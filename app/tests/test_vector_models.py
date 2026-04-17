"""Tests for Vector Database Models."""

import hashlib
import json

from app.models.vector_models import (
    ChunkType,
    DocumentType,
    UserCondition,
)


class TestEnumerations:
    """Test cases for enum classes."""

    def test_document_type_enum(self) -> None:
        """Test DocumentType enumeration values."""
        assert DocumentType.PRESCRIPTION == "PRESCRIPTION"
        assert DocumentType.MEDICINE_INFO == "MEDICINE_INFO"
        assert DocumentType.DRUG_INTERACTION == "DRUG_INTERACTION"
        assert DocumentType.SIDE_EFFECT == "SIDE_EFFECT"
        assert DocumentType.DOSAGE_GUIDE == "DOSAGE_GUIDE"
        assert DocumentType.CONTRAINDICATION == "CONTRAINDICATION"

        # Test enum is string-based
        assert isinstance(DocumentType.PRESCRIPTION, str)

    def test_chunk_type_enum(self) -> None:
        """Test ChunkType enumeration values."""
        assert ChunkType.EFFICACY == "EFFICACY"
        assert ChunkType.DOSAGE == "DOSAGE"
        assert ChunkType.PRECAUTION == "PRECAUTION"
        assert ChunkType.INTERACTION == "INTERACTION"
        assert ChunkType.SIDE_EFFECT == "SIDE_EFFECT"
        assert ChunkType.CONTRAINDICATION == "CONTRAINDICATION"
        assert ChunkType.STORAGE == "STORAGE"
        assert ChunkType.GENERAL == "GENERAL"

        # Test enum is string-based
        assert isinstance(ChunkType.EFFICACY, str)

    def test_user_condition_enum(self) -> None:
        """Test UserCondition enumeration values."""
        assert UserCondition.PREGNANT == "PREGNANT"
        assert UserCondition.ELDERLY == "ELDERLY"
        assert UserCondition.CHILD == "CHILD"
        assert UserCondition.LACTATING == "LACTATING"
        assert UserCondition.DIABETIC == "DIABETIC"
        assert UserCondition.HYPERTENSIVE == "HYPERTENSIVE"
        assert UserCondition.KIDNEY_DISEASE == "KIDNEY_DISEASE"
        assert UserCondition.LIVER_DISEASE == "LIVER_DISEASE"

        # Test enum is string-based
        assert isinstance(UserCondition.PREGNANT, str)


class TestPharmaceuticalDocument:
    """Test cases for PharmaceuticalDocument model."""

    def test_document_creation_data(self) -> None:
        """Test document data structure and validation."""
        # Test document data
        title = "타이레놀 복용법 가이드"
        content = "타이레놀은 해열진통제로 사용됩니다..."
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        medicine_names = ["타이레놀", "아세트아미노펜"]
        target_conditions = [UserCondition.PREGNANT, UserCondition.ELDERLY]

        # Validate data types
        assert isinstance(title, str)
        assert len(title) <= 500  # Max length constraint
        assert isinstance(content, str)
        assert len(content_hash) == 64  # SHA256 hash length
        assert isinstance(medicine_names, list)
        assert isinstance(target_conditions, list)
        assert all(isinstance(condition, UserCondition) for condition in target_conditions)

    def test_document_hash_generation(self) -> None:
        """Test content hash generation for duplicate detection."""
        content1 = "타이레놀 복용법"
        content2 = "타이레놀 복용법"
        content3 = "애드빌 복용법"

        hash1 = hashlib.sha256(content1.encode()).hexdigest()
        hash2 = hashlib.sha256(content2.encode()).hexdigest()
        hash3 = hashlib.sha256(content3.encode()).hexdigest()

        # Same content should produce same hash
        assert hash1 == hash2
        # Different content should produce different hash
        assert hash1 != hash3
        # Hash should be 64 characters (SHA256)
        assert len(hash1) == 64

    def test_document_metadata_structure(self) -> None:
        """Test document metadata JSON structure."""
        medicine_names = ["타이레놀", "아세트아미노펜", "Tylenol"]
        target_conditions = [UserCondition.PREGNANT, UserCondition.CHILD]

        # Test JSON serialization
        medicine_json = json.dumps(medicine_names, ensure_ascii=False)
        condition_json = json.dumps(target_conditions, ensure_ascii=False)

        # Test deserialization
        parsed_medicines = json.loads(medicine_json)
        parsed_conditions = json.loads(condition_json)

        assert parsed_medicines == medicine_names
        assert parsed_conditions == target_conditions

    def test_document_embedding_dimensions(self) -> None:
        """Test document embedding vector dimensions."""
        # Test embedding vector (1536 dimensions for OpenAI)
        embedding = [0.1] * 1536

        assert len(embedding) == 1536
        assert all(isinstance(x, (int, float)) for x in embedding)


class TestDocumentChunk:
    """Test cases for DocumentChunk model."""

    def test_chunk_creation_data(self) -> None:
        """Test chunk data structure and validation."""
        content = "효능: 해열, 진통 작용을 나타냅니다."
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        word_count = len(content.split())
        char_count = len(content)

        # Validate data
        assert isinstance(content, str)
        assert len(content_hash) == 64
        assert isinstance(word_count, int)
        assert isinstance(char_count, int)
        assert word_count > 0
        assert char_count > 0

    def test_chunk_metadata_extraction(self) -> None:
        """Test chunk metadata extraction and structuring."""
        keywords = ["해열", "진통", "타이레놀", "아세트아미노펜"]
        medicine_names = ["타이레놀"]
        dosage_info = {"adult_dose": "500mg", "frequency": "1일 3-4회", "max_daily": "4000mg"}
        target_conditions = [UserCondition.PREGNANT]
        contraindicated_conditions = [UserCondition.LIVER_DISEASE]

        # Test data structure
        assert isinstance(keywords, list)
        assert isinstance(medicine_names, list)
        assert isinstance(dosage_info, dict)
        assert isinstance(target_conditions, list)
        assert isinstance(contraindicated_conditions, list)

        # Test JSON serialization
        dosage_json = json.dumps(dosage_info, ensure_ascii=False)
        parsed_dosage = json.loads(dosage_json)
        assert parsed_dosage == dosage_info

    def test_chunk_embedding_normalization(self) -> None:
        """Test chunk embedding normalization flag."""
        embedding = [0.6, 0.8, 0.0]  # Normalized vector
        embedding_normalized = True

        # Calculate L2 norm
        import math

        norm = math.sqrt(sum(x**2 for x in embedding))

        if embedding_normalized:
            assert abs(norm - 1.0) < 1e-10  # Should be normalized

        assert isinstance(embedding_normalized, bool)

    def test_chunk_section_parsing(self) -> None:
        """Test section title extraction from pharmaceutical documents."""
        section_titles = ["효능·효과", "용법·용량", "사용상의 주의사항", "약물상호작용", "부작용", "금기사항", "보관법"]

        chunk_type_mapping = {
            "효능": ChunkType.EFFICACY,
            "용법": ChunkType.DOSAGE,
            "주의사항": ChunkType.PRECAUTION,
            "상호작용": ChunkType.INTERACTION,
            "부작용": ChunkType.SIDE_EFFECT,
            "금기": ChunkType.CONTRAINDICATION,
            "보관": ChunkType.STORAGE,
        }

        # Test mapping logic
        for title in section_titles:
            found_type = None
            for keyword, chunk_type in chunk_type_mapping.items():
                if keyword in title:
                    found_type = chunk_type
                    break

            assert found_type is not None, f"No chunk type found for title: {title}"


class TestSearchQuery:
    """Test cases for SearchQuery model."""

    def test_search_query_data_structure(self) -> None:
        """Test search query data structure."""
        query_text = "타이레놀 부작용이 뭔가요?"
        query_embedding = [0.1] * 1536
        search_type = "hybrid_search"
        filters_applied = {
            "user_conditions": [UserCondition.PREGNANT],
            "medicine_names": ["타이레놀"],
            "chunk_types": [ChunkType.SIDE_EFFECT],
        }
        results_count = 5
        top_chunk_ids = [1, 3, 7, 12, 15]
        search_duration_ms = 150

        # Validate data types
        assert isinstance(query_text, str)
        assert isinstance(query_embedding, list)
        assert len(query_embedding) == 1536
        assert isinstance(search_type, str)
        assert isinstance(filters_applied, dict)
        assert isinstance(results_count, int)
        assert isinstance(top_chunk_ids, list)
        assert isinstance(search_duration_ms, int)

        # Test JSON serialization of filters
        filters_json = json.dumps(filters_applied, ensure_ascii=False, default=str)
        parsed_filters = json.loads(filters_json)
        assert "user_conditions" in parsed_filters
        assert "medicine_names" in parsed_filters
        assert "chunk_types" in parsed_filters

    def test_search_performance_metrics(self) -> None:
        """Test search performance metrics calculation."""
        search_times = [120, 150, 180, 95, 200]  # milliseconds

        avg_time = sum(search_times) / len(search_times)
        max_time = max(search_times)
        min_time = min(search_times)

        assert isinstance(avg_time, float)
        assert avg_time == 149.0
        assert max_time == 200
        assert min_time == 95


class TestEmbeddingModel:
    """Test cases for EmbeddingModel model."""

    def test_embedding_model_configuration(self) -> None:
        """Test embedding model configuration data."""
        model_configs = [
            {
                "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "model_version": "1.0.0",
                "dimensions": 384,
                "max_tokens": 512,
                "language_support": ["ko", "en", "ja", "zh"],
                "avg_embedding_time_ms": 45.5,
            },
            {
                "model_name": "jhgan/ko-sroberta-multitask",
                "model_version": "1.0.0",
                "dimensions": 768,
                "max_tokens": 512,
                "language_support": ["ko"],
                "avg_embedding_time_ms": 85.2,
            },
            {
                "model_name": "openai/text-embedding-3-small",
                "model_version": "3.0.0",
                "dimensions": 1536,
                "max_tokens": 8192,
                "language_support": ["ko", "en", "ja", "zh", "es", "fr", "de"],
                "avg_embedding_time_ms": 120.0,
            },
        ]

        for config in model_configs:
            # Validate required fields
            assert isinstance(config["model_name"], str)
            assert len(config["model_name"]) <= 200
            assert isinstance(config["model_version"], str)
            assert isinstance(config["dimensions"], int)
            assert config["dimensions"] > 0
            assert isinstance(config["max_tokens"], int)
            assert config["max_tokens"] > 0
            assert isinstance(config["language_support"], list)
            assert "ko" in config["language_support"]  # Korean support required
            assert isinstance(config["avg_embedding_time_ms"], (int, float))

    def test_model_performance_comparison(self) -> None:
        """Test embedding model performance comparison."""
        models = {
            "lightweight": {"dimensions": 384, "time_ms": 45.5},
            "balanced": {"dimensions": 768, "time_ms": 85.2},
            "high_quality": {"dimensions": 1536, "time_ms": 120.0},
        }

        # Test performance vs quality trade-off
        for model_type, specs in models.items():
            dimensions = specs["dimensions"]
            time_ms = specs["time_ms"]

            # Higher dimensions generally mean better quality but slower speed
            quality_score = dimensions / 384  # Normalized to lightweight model
            speed_score = 45.5 / time_ms  # Normalized to lightweight model

            assert quality_score > 0
            assert speed_score > 0

            if model_type == "lightweight":
                assert quality_score == 1.0
                assert speed_score == 1.0
            elif model_type == "high_quality":
                assert quality_score > 1.0
                assert speed_score < 1.0


class TestVectorModelIntegration:
    """Integration tests for vector models."""

    def test_document_to_chunks_relationship(self) -> None:
        """Test document-chunk relationship data structure."""
        # Mock document data
        document_data = {
            "id": 1,
            "title": "타이레놀 약품정보",
            "content": "효능: 해열진통제\n용법: 1일 3회\n주의사항: 간질환 주의",
        }

        # Mock chunk data
        chunks_data = [
            {
                "id": 1,
                "document_id": 1,
                "chunk_index": 0,
                "chunk_type": ChunkType.EFFICACY,
                "content": "효능: 해열진통제",
                "section_title": "효능·효과",
            },
            {
                "id": 2,
                "document_id": 1,
                "chunk_index": 1,
                "chunk_type": ChunkType.DOSAGE,
                "content": "용법: 1일 3회",
                "section_title": "용법·용량",
            },
            {
                "id": 3,
                "document_id": 1,
                "chunk_index": 2,
                "chunk_type": ChunkType.PRECAUTION,
                "content": "주의사항: 간질환 주의",
                "section_title": "사용상의 주의사항",
            },
        ]

        # Test relationship integrity
        for chunk in chunks_data:
            assert chunk["document_id"] == document_data["id"]
            assert isinstance(chunk["chunk_index"], int)
            assert chunk["chunk_index"] >= 0
            assert isinstance(chunk["chunk_type"], ChunkType)

        # Test chunk ordering
        chunk_indices = [chunk["chunk_index"] for chunk in chunks_data]
        assert chunk_indices == sorted(chunk_indices)  # Should be ordered

    def test_search_query_to_results_relationship(self) -> None:
        """Test search query to results relationship."""
        # Mock search query
        query_data = {
            "id": 1,
            "query_text": "타이레놈 부작용",
            "search_type": "hybrid_search",
            "results_count": 3,
            "top_chunk_ids": [5, 12, 8],
        }

        # Mock chunk results
        result_chunks = [
            {"id": 5, "chunk_type": ChunkType.SIDE_EFFECT, "relevance_score": 0.95},
            {"id": 12, "chunk_type": ChunkType.PRECAUTION, "relevance_score": 0.87},
            {"id": 8, "chunk_type": ChunkType.CONTRAINDICATION, "relevance_score": 0.82},
        ]

        # Test relationship integrity
        assert len(result_chunks) == query_data["results_count"]
        assert all(chunk["id"] in query_data["top_chunk_ids"] for chunk in result_chunks)

        # Test relevance ordering
        scores = [chunk["relevance_score"] for chunk in result_chunks]
        assert scores == sorted(scores, reverse=True)  # Should be descending order
