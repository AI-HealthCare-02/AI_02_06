"""Dtl06 DOC XML parser.

Food and Drug Safety Dtl06 endpoint returns three XML document blobs
(EE_DOC_DATA / UD_DOC_DATA / NB_DOC_DATA) whose structure is
``<DOC><SECTION><ARTICLE><PARAGRAPH>...``. This module translates
that structure into ARTICLE-level records suitable for RAG chunk
creation, plus two helpers:

- parse_doc_articles: ARTICLE 단위 (title, body) 리스트
- flatten_doc_plaintext: DOC 전체 → 단일 평문
- classify_article_section: ARTICLE title 키워드 → MedicineChunkSection

The parser is tolerant of ``None``, empty strings, and malformed XML:
bad input returns an empty result instead of raising.
"""

from dataclasses import dataclass
import logging
from xml.etree import ElementTree as ET

from app.models.medicine_chunk import MedicineChunkSection

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Article:
    """ARTICLE-level extracted record.

    Attributes:
        title: ARTICLE tag title attribute (may be empty when only PARAGRAPHs).
        body: Joined PARAGRAPH text content, newline-separated (may be empty).
    """

    title: str
    body: str


# ── 섹션 키워드 매핑 (순서 중요: 더 구체적인 것 먼저) ─────────────────
# Each entry is (keyword, section). The first matching keyword wins.
# v2 6섹션 enum 으로 재매핑됨 — 사용자 질문 패턴 기준 묶음.
_SECTION_KEYWORDS: tuple[tuple[str, MedicineChunkSection], ...] = (
    # 생활 상호작용 (술/카페인/운전 — 사용자 일상 질문)
    ("음주", MedicineChunkSection.LIFESTYLE_INTERACTION),
    ("술", MedicineChunkSection.LIFESTYLE_INTERACTION),
    ("카페인", MedicineChunkSection.LIFESTYLE_INTERACTION),
    ("커피", MedicineChunkSection.LIFESTYLE_INTERACTION),
    ("운전", MedicineChunkSection.LIFESTYLE_INTERACTION),
    ("기계조작", MedicineChunkSection.LIFESTYLE_INTERACTION),
    # 약물 상호작용 — 금기·병용·신중투여 일괄
    ("투여하지 말", MedicineChunkSection.DRUG_INTERACTION),
    ("복용하지 말", MedicineChunkSection.DRUG_INTERACTION),
    ("사용하지 말", MedicineChunkSection.DRUG_INTERACTION),
    ("금기", MedicineChunkSection.DRUG_INTERACTION),
    ("신중히 투여", MedicineChunkSection.DRUG_INTERACTION),
    ("신중 투여", MedicineChunkSection.DRUG_INTERACTION),
    ("신중히 복용", MedicineChunkSection.DRUG_INTERACTION),
    ("상호작용", MedicineChunkSection.DRUG_INTERACTION),
    ("병용", MedicineChunkSection.DRUG_INTERACTION),
    ("상의", MedicineChunkSection.DRUG_INTERACTION),
    # 이상반응·과량 — 부작용 영역
    ("이상반응", MedicineChunkSection.ADVERSE_REACTION),
    ("부작용", MedicineChunkSection.ADVERSE_REACTION),
    ("과량", MedicineChunkSection.ADVERSE_REACTION),
    ("과용", MedicineChunkSection.ADVERSE_REACTION),
    # 특수 상황 — 경고·임부·소아·고령·시술
    ("경고", MedicineChunkSection.SPECIAL_EVENT),
    ("임부", MedicineChunkSection.SPECIAL_EVENT),
    ("임산부", MedicineChunkSection.SPECIAL_EVENT),
    ("수유", MedicineChunkSection.SPECIAL_EVENT),
    ("가임", MedicineChunkSection.SPECIAL_EVENT),
    ("소아", MedicineChunkSection.SPECIAL_EVENT),
    ("어린이", MedicineChunkSection.SPECIAL_EVENT),
    ("영아", MedicineChunkSection.SPECIAL_EVENT),
    ("유아", MedicineChunkSection.SPECIAL_EVENT),
    ("신생아", MedicineChunkSection.SPECIAL_EVENT),
    ("고령자", MedicineChunkSection.SPECIAL_EVENT),
    ("노인", MedicineChunkSection.SPECIAL_EVENT),
    ("수술", MedicineChunkSection.SPECIAL_EVENT),
    ("시술", MedicineChunkSection.SPECIAL_EVENT),
)


def parse_doc_articles(xml: str | None) -> list[Article]:
    """Parse a Dtl06 DOC XML blob into ARTICLE records.

    Args:
        xml: Raw XML string from EE_DOC_DATA / UD_DOC_DATA / NB_DOC_DATA.
            ``None``, empty, or whitespace-only input returns ``[]``.

    Returns:
        List of Article(title, body) in document order. Malformed XML
        yields an empty list and logs a warning.
    """
    if not xml or not xml.strip():
        return []

    try:
        root = ET.fromstring(xml)  # noqa: S314 — 공공데이터포털 신뢰 소스
    except ET.ParseError as exc:
        logger.warning("DOC XML parse failed: %s", exc)
        return []

    articles: list[Article] = []
    for article_el in root.iter("ARTICLE"):
        title = (article_el.get("title") or "").strip()
        paragraphs = [(p.text or "").strip() for p in article_el.iter("PARAGRAPH") if p.text]
        body = "\n".join(p for p in paragraphs if p)
        articles.append(Article(title=title, body=body))

    return articles


def flatten_doc_plaintext(xml: str | None) -> str:
    r"""Flatten a DOC XML blob to a single newline-joined plaintext string.

    Used for UI display fields (e.g. MedicineInfo.efficacy). Produces
    ``title\nbody`` per ARTICLE, joined by blank lines.

    Args:
        xml: Raw XML string. ``None``/empty/malformed input returns ``""``.

    Returns:
        Plaintext without any XML tags or CDATA wrappers.
    """
    articles = parse_doc_articles(xml)
    if not articles:
        return ""

    blocks: list[str] = []
    for article in articles:
        parts = [article.title, article.body]
        block = "\n".join(p for p in parts if p)
        if block:
            blocks.append(block)

    return "\n\n".join(blocks)


def classify_article_section(title: str) -> MedicineChunkSection:
    """Classify an ARTICLE title into a MedicineChunkSection.

    Uses ordered keyword matching over ``_SECTION_KEYWORDS``. Titles
    with no matching keyword fall back to ``INTAKE_GUIDE`` (일반 복용
    가이드).

    Args:
        title: ARTICLE title string (Korean).

    Returns:
        Corresponding MedicineChunkSection. Unknown/empty titles
        return INTAKE_GUIDE.
    """
    if not title:
        return MedicineChunkSection.INTAKE_GUIDE

    for keyword, section in _SECTION_KEYWORDS:
        if keyword in title:
            return section

    return MedicineChunkSection.INTAKE_GUIDE
