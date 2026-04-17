"""Document chunking service for pharmaceutical documents."""

from dataclasses import dataclass
import logging
import re

from app.models.vector_models import ChunkType

logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Represents a chunk of a pharmaceutical document."""

    content: str
    chunk_type: ChunkType
    section_title: str | None = None
    chunk_index: int = 0
    word_count: int = 0
    char_count: int = 0
    keywords: list[str] = None

    def __post_init__(self):
        """Calculate metrics after initialization."""
        if self.keywords is None:
            self.keywords = []

        self.word_count = len(self.content.split())
        self.char_count = len(self.content)


class DocumentChunker:
    """Service for chunking pharmaceutical documents into meaningful sections."""

    # Section patterns for Korean pharmaceutical documents
    SECTION_PATTERNS = {
        ChunkType.EFFICACY: [r"효능[·\s]*효과", r"적응증", r"치료효과"],
        ChunkType.DOSAGE: [r"용법[·\s]*용량", r"투여[·\s]*용량", r"복용법", r"사용법"],
        ChunkType.PRECAUTION: [r"사용상[의\s]*주의사항", r"주의사항", r"경고", r"주의"],
        ChunkType.INTERACTION: [r"약물[·\s]*상호작용", r"상호작용", r"병용금기", r"약물간[·\s]*상호작용"],
        ChunkType.SIDE_EFFECT: [r"부작용", r"이상반응", r"부작용[·\s]*이상반응", r"이상사례"],
        ChunkType.CONTRAINDICATION: [r"금기사항", r"금기", r"투여금기", r"사용금기"],
        ChunkType.STORAGE: [r"보관[·\s]*저장", r"저장방법", r"보관법", r"보관조건"],
    }

    def __init__(self, max_chunk_size: int = 500, overlap_size: int = 50):
        """Initialize document chunker.

        Args:
            max_chunk_size: Maximum characters per chunk
            overlap_size: Number of characters to overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size

        # Compile regex patterns for efficiency
        self.compiled_patterns = {}
        for chunk_type, patterns in self.SECTION_PATTERNS.items():
            self.compiled_patterns[chunk_type] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

    def chunk_document(self, content: str, title: str = "") -> list[DocumentChunk]:  # noqa: ARG002
        """Chunk a pharmaceutical document into meaningful sections.

        Args:
            content: Full document content
            title: Document title for context

        Returns:
            List of document chunks
        """
        if not content.strip():
            return []

        # First try structured chunking by sections
        structured_chunks = self._chunk_by_sections(content)

        if structured_chunks:
            logger.info(f"Created {len(structured_chunks)} structured chunks")
            return structured_chunks

        # Fallback to semantic chunking
        logger.info("Falling back to semantic chunking")
        return self._chunk_semantically(content)

    def _chunk_by_sections(self, content: str) -> list[DocumentChunk]:
        """Chunk document by pharmaceutical sections.

        Args:
            content: Document content

        Returns:
            List of chunks organized by sections
        """
        chunks = []
        sections = self._identify_sections(content)

        if not sections:
            return []

        for _i, (section_title, section_content, chunk_type) in enumerate(sections):
            # Split large sections into smaller chunks
            section_chunks = self._split_large_section(section_content, chunk_type, section_title)

            for _j, chunk in enumerate(section_chunks):
                chunk.chunk_index = len(chunks)
                chunks.append(chunk)

        return chunks

    def _identify_sections(self, content: str) -> list[tuple[str, str, ChunkType]]:
        """Identify sections in pharmaceutical document.

        Args:
            content: Document content

        Returns:
            List of (section_title, section_content, chunk_type) tuples
        """
        sections = []
        lines = content.split("\n")
        current_section = None
        current_content = []
        current_type = ChunkType.GENERAL

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line is a section header
            detected_type = self._detect_section_type(line)

            if detected_type != ChunkType.GENERAL:
                # Save previous section
                if current_section and current_content:
                    sections.append((current_section, "\n".join(current_content), current_type))

                # Start new section
                current_section = line
                current_content = []
                current_type = detected_type
            else:
                # Add to current section
                current_content.append(line)

        # Add final section
        if current_section and current_content:
            sections.append((current_section, "\n".join(current_content), current_type))

        return sections

    def _detect_section_type(self, text: str) -> ChunkType:
        """Detect the type of a section based on its title.

        Args:
            text: Section title or text

        Returns:
            Detected chunk type
        """
        for chunk_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    return chunk_type

        return ChunkType.GENERAL

    def _split_large_section(self, content: str, chunk_type: ChunkType, section_title: str) -> list[DocumentChunk]:
        """Split large sections into smaller chunks.

        Args:
            content: Section content
            chunk_type: Type of the section
            section_title: Title of the section

        Returns:
            List of chunks from the section
        """
        if len(content) <= self.max_chunk_size:
            # Section fits in one chunk
            keywords = self._extract_keywords(content, chunk_type)
            return [
                DocumentChunk(content=content, chunk_type=chunk_type, section_title=section_title, keywords=keywords)
            ]

        # Split into multiple chunks with overlap
        chunks = []
        start = 0

        while start < len(content):
            end = start + self.max_chunk_size

            if end >= len(content):
                # Last chunk
                chunk_content = content[start:]
            else:
                # Find good break point (sentence boundary)
                break_point = self._find_break_point(content, start, end)
                chunk_content = content[start:break_point]

            keywords = self._extract_keywords(chunk_content, chunk_type)
            chunks.append(
                DocumentChunk(
                    content=chunk_content, chunk_type=chunk_type, section_title=section_title, keywords=keywords
                )
            )

            # Move start position with overlap
            start = max(start + len(chunk_content) - self.overlap_size, start + 1)

        return chunks

    def _find_break_point(self, content: str, start: int, end: int) -> int:
        """Find a good break point for chunking (sentence boundary).

        Args:
            content: Full content
            start: Start position
            end: Desired end position

        Returns:
            Actual break point
        """
        # Look for sentence endings near the desired end point
        search_start = max(start, end - 100)  # Look back up to 100 chars

        # Korean sentence endings
        sentence_endings = ["다.", "요.", "니다.", "습니다.", "다!", "요!", "다?", "요?"]

        best_break = end
        for ending in sentence_endings:
            pos = content.rfind(ending, search_start, end)
            if pos != -1:
                potential_break = pos + len(ending)
                if potential_break > start + 100:  # Ensure minimum chunk size
                    best_break = min(best_break, potential_break)

        return best_break

    def _chunk_semantically(self, content: str) -> list[DocumentChunk]:
        """Fallback semantic chunking when structured chunking fails.

        Args:
            content: Document content

        Returns:
            List of semantically chunked documents
        """
        chunks = []
        sentences = self._split_into_sentences(content)

        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # Check if adding this sentence would exceed max size
            if current_length + sentence_length > self.max_chunk_size and current_chunk:
                # Create chunk from current sentences
                chunk_content = " ".join(current_chunk)
                chunk_type = self._infer_chunk_type(chunk_content)
                keywords = self._extract_keywords(chunk_content, chunk_type)

                chunks.append(
                    DocumentChunk(
                        content=chunk_content, chunk_type=chunk_type, chunk_index=len(chunks), keywords=keywords
                    )
                )

                # Start new chunk with overlap
                if self.overlap_size > 0 and len(current_chunk) > 1:
                    # Keep last sentence for overlap
                    current_chunk = [current_chunk[-1], sentence]
                    current_length = len(current_chunk[-2]) + sentence_length
                else:
                    current_chunk = [sentence]
                    current_length = sentence_length
            else:
                current_chunk.append(sentence)
                current_length += sentence_length

        # Add final chunk
        if current_chunk:
            chunk_content = " ".join(current_chunk)
            chunk_type = self._infer_chunk_type(chunk_content)
            keywords = self._extract_keywords(chunk_content, chunk_type)

            chunks.append(
                DocumentChunk(content=chunk_content, chunk_type=chunk_type, chunk_index=len(chunks), keywords=keywords)
            )

        return chunks

    def _split_into_sentences(self, content: str) -> list[str]:
        """Split content into sentences for Korean text.

        Args:
            content: Text content

        Returns:
            List of sentences
        """
        # Korean sentence splitting pattern
        sentence_pattern = r"[.!?]+\s*"
        sentences = re.split(sentence_pattern, content)

        # Clean and filter sentences
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def _infer_chunk_type(self, content: str) -> ChunkType:
        """Infer chunk type from content when section headers are not available.

        Args:
            content: Chunk content

        Returns:
            Inferred chunk type
        """
        # Check content against patterns
        for chunk_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(content):
                    return chunk_type

        # Check for specific keywords
        content_lower = content.lower()

        if any(word in content_lower for word in ["복용", "투여", "용량", "mg", "ml"]):
            return ChunkType.DOSAGE
        if any(word in content_lower for word in ["부작용", "이상반응", "위험"]):
            return ChunkType.SIDE_EFFECT
        if any(word in content_lower for word in ["주의", "경고", "금지"]):
            return ChunkType.PRECAUTION
        if any(word in content_lower for word in ["효과", "치료", "적응"]):
            return ChunkType.EFFICACY

        return ChunkType.GENERAL

    def _extract_keywords(self, content: str, chunk_type: ChunkType) -> list[str]:
        """Extract keywords from chunk content.

        Args:
            content: Chunk content
            chunk_type: Type of chunk

        Returns:
            List of extracted keywords
        """
        keywords = []

        # Medicine name patterns
        medicine_patterns = [
            r"[가-힣]+놀",  # 타이레놀, 부루펜 등
            r"[가-힣]+린",  # 아스피린 등
            r"[가-힣]+펜",  # 이부프로펜 등
            r"[가-힣]+신",  # 페니실린 등
        ]

        for pattern in medicine_patterns:
            matches = re.findall(pattern, content)
            keywords.extend(matches)

        # Dosage patterns
        if chunk_type == ChunkType.DOSAGE:
            dosage_patterns = [r"\d+\s*mg", r"\d+\s*ml", r"\d+회", r"하루\s*\d+번", r"식[전후]"]

            for pattern in dosage_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                keywords.extend(matches)

        # Remove duplicates and return
        return list(set(keywords))


# Global chunker instance
_document_chunker: DocumentChunker | None = None


def get_document_chunker() -> DocumentChunker:
    """Get or create global document chunker instance.

    Returns:
        Document chunker instance
    """
    global _document_chunker

    if _document_chunker is None:
        _document_chunker = DocumentChunker()

    return _document_chunker
