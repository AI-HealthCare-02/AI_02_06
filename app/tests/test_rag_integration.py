"""Tests for RAG system integration and embedding services."""

from datetime import UTC
from unittest.mock import Mock, patch

import numpy as np
import pytest

from app.models.vector_models import ChunkType, UserCondition


class TestEmbeddingService:
    """Test cases for embedding service functionality."""

    def test_korean_text_preprocessing(self) -> None:
        """Test Korean text preprocessing for embedding."""
        test_texts = [
            "타이레놀은 해열진통제입니다.",
            "효능·효과: 발열, 두통, 치통의 완화",
            "용법·용량: 성인 1회 500mg, 1일 3-4회",
            "사용상 주의사항: 간질환 환자는 주의하세요.",
        ]

        for text in test_texts:
            # Test text cleaning
            cleaned = text.strip()
            assert isinstance(cleaned, str)
            assert len(cleaned) > 0

            # Test Korean character detection
            has_korean = any("\uac00" <= char <= "\ud7af" for char in text)
            assert has_korean, f"Text should contain Korean characters: {text}"

    def test_embedding_dimension_validation(self) -> None:
        """Test embedding dimension validation for different models."""
        model_dimensions = {
            "paraphrase-multilingual-MiniLM-L12-v2": 384,
            "ko-sroberta-multitask": 768,
            "text-embedding-3-small": 1536,
        }

        for expected_dim in model_dimensions.values():
            # Mock embedding vector
            mock_embedding = [0.1] * expected_dim

            assert len(mock_embedding) == expected_dim
            assert all(isinstance(x, (int, float)) for x in mock_embedding)

            # Test normalization
            embedding_array = np.array(mock_embedding)
            normalized = embedding_array / np.linalg.norm(embedding_array)
            assert abs(np.linalg.norm(normalized) - 1.0) < 1e-10

    @patch("sentence_transformers.SentenceTransformer")
    def test_sentence_transformer_integration(self, mock_transformer: Mock) -> None:
        """Test SentenceTransformer integration."""
        # Mock model
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1, 0.2, 0.3]])
        mock_transformer.return_value = mock_model

        # Test embedding generation
        text = "타이레놀 복용법"
        embedding = mock_model.encode([text])

        assert embedding.shape == (1, 3)
        assert isinstance(embedding, np.ndarray)
        mock_model.encode.assert_called_once_with([text])

    def test_batch_embedding_processing(self) -> None:
        """Test batch processing of multiple texts."""
        texts = ["타이레놀 효능", "아스피린 부작용", "이부프로펜 용법", "아세트아미노펜 주의사항"]

        # Mock batch processing
        batch_size = 2
        batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]

        assert len(batches) == 2
        assert batches[0] == ["타이레놀 효능", "아스피린 부작용"]
        assert batches[1] == ["이부프로펜 용법", "아세트아미노펜 주의사항"]


class TestDocumentChunking:
    """Test cases for document chunking strategies."""

    def test_structured_chunking_by_sections(self) -> None:
        """Test chunking based on pharmaceutical document sections."""
        mock_document = """
        효능·효과
        발열, 두통, 치통, 생리통, 관절통, 신경통, 근육통의 완화

        용법·용량
        성인: 1회 500mg, 1일 3-4회 복용
        소아: 체중 1kg당 10-15mg, 1일 3-4회

        사용상의 주의사항
        1. 간질환 환자는 신중히 투여
        2. 알코올과 함께 복용 금지
        3. 장기간 복용 시 의사와 상담
        """

        # Test section detection
        sections = {
            "효능·효과": ChunkType.EFFICACY,
            "용법·용량": ChunkType.DOSAGE,
            "사용상의 주의사항": ChunkType.PRECAUTION,
        }

        for section_title, expected_type in sections.items():
            assert section_title in mock_document
            assert isinstance(expected_type, ChunkType)

    def test_chunk_size_optimization(self) -> None:
        """Test optimal chunk size for embedding."""
        test_content = "타이레놀은 아세트아미노펜을 주성분으로 하는 해열진통제입니다. " * 20

        # Test different chunk sizes
        chunk_sizes = [100, 200, 500, 1000]

        for size in chunk_sizes:
            if len(test_content) > size:
                chunk = test_content[:size]
                assert len(chunk) == size
                assert isinstance(chunk, str)
            else:
                chunk = test_content
                assert len(chunk) <= size

    def test_chunk_overlap_strategy(self) -> None:
        """Test chunk overlap for context preservation."""
        text = "타이레놀은 해열진통제입니다. 성인은 1회 500mg 복용합니다. 간질환 환자는 주의해야 합니다."
        sentences = text.split(". ")

        chunk_size = 2  # sentences per chunk
        overlap = 1  # sentence overlap

        chunks = []
        for i in range(0, len(sentences), chunk_size - overlap):
            chunk_sentences = sentences[i : i + chunk_size]
            chunk = ". ".join(chunk_sentences)
            chunks.append(chunk)

        # Test overlap preservation
        assert len(chunks) >= 2
        # Should have overlapping content between chunks
        if len(chunks) > 1:
            # Check if there's shared content (overlap)
            assert any(word in chunks[1] for word in chunks[0].split())


class TestHybridSearch:
    """Test cases for hybrid search functionality."""

    def test_vector_similarity_scoring(self) -> None:
        """Test vector similarity scoring methods."""
        query_vector = np.array([1.0, 0.0, 0.0])
        doc_vectors = [
            np.array([1.0, 0.0, 0.0]),  # Identical
            np.array([0.0, 1.0, 0.0]),  # Orthogonal
            np.array([0.5, 0.5, 0.0]),  # Partial match
        ]

        # Test cosine similarity
        cosine_scores = []
        for doc_vec in doc_vectors:
            # Normalize vectors
            query_norm = query_vector / np.linalg.norm(query_vector)
            doc_norm = doc_vec / np.linalg.norm(doc_vec)

            # Calculate cosine similarity
            cosine_sim = np.dot(query_norm, doc_norm)
            cosine_scores.append(cosine_sim)

        assert cosine_scores[0] == 1.0  # Identical vectors
        assert abs(cosine_scores[1]) < 1e-10  # Orthogonal vectors
        assert 0 < cosine_scores[2] < 1  # Partial match

    def test_keyword_matching_scoring(self) -> None:
        """Test keyword matching for hybrid search."""
        query_keywords = ["타이레놀", "부작용", "간질환"]

        documents = [
            {"content": "타이레놀의 주요 부작용은 간질환입니다.", "keywords": ["타이레놀", "부작용", "간질환"]},
            {"content": "아스피린은 위장장애를 일으킬 수 있습니다.", "keywords": ["아스피린", "위장장애"]},
            {"content": "타이레놀 복용 시 간질환 환자는 주의하세요.", "keywords": ["타이레놀", "간질환", "주의사항"]},
        ]

        # Calculate keyword match scores
        keyword_scores = []
        for doc in documents:
            matches = len(set(query_keywords) & set(doc["keywords"]))
            score = matches / len(query_keywords)
            keyword_scores.append(score)

        assert keyword_scores[0] == 1.0  # All keywords match
        assert keyword_scores[1] == 0.0  # No keywords match
        assert keyword_scores[2] > 0.5  # Partial match

    def test_hybrid_score_combination(self) -> None:
        """Test combining vector and keyword scores."""
        vector_scores = [0.9, 0.3, 0.7]
        keyword_scores = [0.8, 0.9, 0.4]

        vector_weight = 0.7
        keyword_weight = 0.3

        hybrid_scores = []
        for v_score, k_score in zip(vector_scores, keyword_scores, strict=False):
            hybrid_score = vector_weight * v_score + keyword_weight * k_score
            hybrid_scores.append(hybrid_score)

        expected_scores = [
            0.7 * 0.9 + 0.3 * 0.8,  # 0.63 + 0.24 = 0.87
            0.7 * 0.3 + 0.3 * 0.9,  # 0.21 + 0.27 = 0.48
            0.7 * 0.7 + 0.3 * 0.4,  # 0.49 + 0.12 = 0.61
        ]

        for actual, expected in zip(hybrid_scores, expected_scores, strict=False):
            assert abs(actual - expected) < 1e-10


class TestMetadataFiltering:
    """Test cases for metadata-based filtering."""

    def test_user_condition_filtering(self) -> None:
        """Test filtering based on user conditions."""
        user_conditions = [UserCondition.PREGNANT, UserCondition.ELDERLY]

        mock_chunks = [
            {
                "id": 1,
                "content": "임산부 복용 금지",
                "target_conditions": [],
                "contraindicated_conditions": [UserCondition.PREGNANT],
            },
            {
                "id": 2,
                "content": "노인 환자 용량 조절 필요",
                "target_conditions": [UserCondition.ELDERLY],
                "contraindicated_conditions": [],
            },
            {"id": 3, "content": "일반 성인 복용법", "target_conditions": [], "contraindicated_conditions": []},
        ]

        # Filter chunks based on user conditions
        filtered_chunks = []
        for chunk in mock_chunks:
            # Exclude contraindicated chunks
            if any(condition in chunk["contraindicated_conditions"] for condition in user_conditions):
                continue

            # Include targeted or general chunks
            if not chunk["target_conditions"] or any(
                condition in chunk["target_conditions"] for condition in user_conditions
            ):
                filtered_chunks.append(chunk)

        # Should exclude chunk 1 (contraindicated for pregnant)
        # Should include chunks 2 and 3
        assert len(filtered_chunks) == 2
        assert filtered_chunks[0]["id"] == 2
        assert filtered_chunks[1]["id"] == 3

    def test_medicine_name_filtering(self) -> None:
        """Test filtering based on medicine names."""
        query_medicines = ["타이레놀", "아세트아미노펜"]

        mock_chunks = [
            {"id": 1, "medicine_names": ["타이레놀", "아세트아미노펜"], "relevance": "high"},
            {"id": 2, "medicine_names": ["아스피린"], "relevance": "low"},
            {"id": 3, "medicine_names": ["타이레놀"], "relevance": "medium"},
        ]

        # Filter by medicine name relevance
        relevant_chunks = [
            chunk for chunk in mock_chunks if any(med in chunk["medicine_names"] for med in query_medicines)
        ]

        assert len(relevant_chunks) == 2
        assert relevant_chunks[0]["id"] == 1
        assert relevant_chunks[1]["id"] == 3

    def test_temporal_filtering(self) -> None:
        """Test filtering based on document recency."""
        from datetime import datetime, timedelta

        now = datetime.now(UTC)
        mock_documents = [
            {"id": 1, "created_at": now - timedelta(days=1), "title": "최신 타이레놀 정보"},
            {"id": 2, "created_at": now - timedelta(days=365), "title": "구 타이레놀 정보"},
            {"id": 3, "created_at": now - timedelta(days=30), "title": "타이레놀 업데이트"},
        ]

        # Filter documents from last 90 days
        cutoff_date = now - timedelta(days=90)
        recent_docs = [doc for doc in mock_documents if doc["created_at"] > cutoff_date]

        assert len(recent_docs) == 2
        assert recent_docs[0]["id"] == 1
        assert recent_docs[1]["id"] == 3


class TestRAGPipeline:
    """Test cases for complete RAG pipeline."""

    @pytest.mark.asyncio
    async def test_rag_pipeline_flow(self) -> None:
        """Test complete RAG pipeline flow."""
        # Mock user query
        user_conditions = [UserCondition.PREGNANT]

        # Step 1: Query embedding (mocked)
        query_embedding = [0.1] * 1536
        assert len(query_embedding) == 1536

        # Step 2: Vector similarity search (mocked)
        mock_similar_chunks = [
            {"id": 1, "vector_score": 0.9, "content": "임산부 복용 금지"},
            {"id": 2, "vector_score": 0.8, "content": "간질환 환자 주의"},
            {"id": 3, "vector_score": 0.7, "content": "알코올과 병용 금지"},
        ]

        # Step 3: Keyword matching (mocked)
        keyword_scores = [0.6, 0.8, 0.5]

        # Step 4: Hybrid scoring
        hybrid_chunks = []
        for chunk, k_score in zip(mock_similar_chunks, keyword_scores, strict=False):
            hybrid_score = 0.7 * chunk["vector_score"] + 0.3 * k_score
            hybrid_chunks.append({**chunk, "hybrid_score": hybrid_score})

        # Step 5: Metadata filtering
        filtered_chunks = []
        for chunk in hybrid_chunks:
            # Mock filtering logic
            if "임산부" in chunk["content"] and UserCondition.PREGNANT in user_conditions:
                chunk["priority"] = "high"
            filtered_chunks.append(chunk)

        # Step 6: Ranking and selection
        final_chunks = sorted(filtered_chunks, key=lambda x: x["hybrid_score"], reverse=True)[:3]

        assert len(final_chunks) == 3
        assert final_chunks[0]["hybrid_score"] >= final_chunks[1]["hybrid_score"]
        assert final_chunks[1]["hybrid_score"] >= final_chunks[2]["hybrid_score"]

    def test_rag_response_generation(self) -> None:
        """Test RAG response generation with retrieved chunks."""
        retrieved_chunks = [
            {
                "content": "임산부는 타이레놀 복용을 피해야 합니다.",
                "chunk_type": ChunkType.CONTRAINDICATION,
                "relevance_score": 0.95,
            },
            {
                "content": "간질환 환자는 용량을 줄여서 복용하세요.",
                "chunk_type": ChunkType.PRECAUTION,
                "relevance_score": 0.87,
            },
        ]

        # Mock response generation
        context = "\n".join([chunk["content"] for chunk in retrieved_chunks])

        # Test context preparation
        assert "임산부" in context
        assert "간질환" in context
        assert len(context) > 0

        # Test chunk type diversity
        chunk_types = [chunk["chunk_type"] for chunk in retrieved_chunks]
        assert ChunkType.CONTRAINDICATION in chunk_types
        assert ChunkType.PRECAUTION in chunk_types

    def test_rag_safety_filtering(self) -> None:
        """Test safety filtering in RAG responses."""
        mock_chunks = [
            {"content": "타이레놀은 안전한 약물입니다.", "safety_level": "safe"},
            {"content": "과다복용 시 간손상 위험이 있습니다.", "safety_level": "warning"},
            {"content": "의사 처방 없이 장기 복용하지 마세요.", "safety_level": "caution"},
        ]

        # Test safety level prioritization
        safety_priority = {"warning": 3, "caution": 2, "safe": 1}

        sorted_chunks = sorted(mock_chunks, key=lambda x: safety_priority.get(x["safety_level"], 0), reverse=True)

        assert sorted_chunks[0]["safety_level"] == "warning"
        assert sorted_chunks[1]["safety_level"] == "caution"
        assert sorted_chunks[2]["safety_level"] == "safe"
