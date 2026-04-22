"""Sample medicine data fetcher (UI/RAG validation only).

Separate from sync_medicine_data.py (which pulls the full ~43k production
dataset), this script collects a small sample and populates the RAG stack:

  1. httpx pagination against the same public API
     (DrugPrdtPrmsnInfoService07 / getDrugPrdtPrmsnDtlInq06), capped at
     `--limit` rows (default 50).
  2. Reuses MedicineDataService's raw-item transform + filter helpers
     and MedicineInfoRepository.bulk_upsert so the ingestion contract
     matches the team's production path.
  3. For each upserted medicine, generates section-level chunks from the
     non-null text fields and embeds them locally with
     SentenceTransformer (ko-sroberta-multitask, 768d). Embeddings are
     L2-normalized for cosine similarity in pgvector.

CLI:
    # sample 50 rows, seed chunks + embeddings
    uv run python -m scripts.crawling.fetch_sample

    # different sample size
    uv run python -m scripts.crawling.fetch_sample --limit 10

    # DB structure only (no chunks, no embeddings)
    uv run python -m scripts.crawling.fetch_sample --skip-embed

    # explicit API key (else taken from .env DATA_GO_KR_API_KEY)
    uv run python -m scripts.crawling.fetch_sample --api-key KEY

운영 주의: 이 스크립트는 로컬/CI 전용이며 프로덕션 EC2 에서 실행하지 않는다.
"""

import argparse
import asyncio
from collections.abc import Iterable
import logging
import sys

import httpx
import numpy as np
from tortoise import Tortoise

from app.core.config import config
from app.db.databases import TORTOISE_ORM
from app.models.medicine_chunk import MedicineChunk, MedicineChunkSection
from app.models.medicine_info import MedicineInfo
from app.services.medicine_data_service import MedicineDataService
from app.services.rag.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL_NAME

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_BASE_URL = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService07"
_DETAIL_ENDPOINT = f"{_BASE_URL}/getDrugPrdtPrmsnDtlInq06"
_REQUEST_TIMEOUT = 30.0

# Map MedicineChunkSection -> (medicine_info attribute name, short Korean label)
# Only sections whose source field exists on the current main schema are
# populated here; the rest remain 13-enum-compatible but unused for now.
_SECTION_FIELDS: dict[MedicineChunkSection, tuple[str, str]] = {
    MedicineChunkSection.EFFICACY: ("efficacy", "효능"),
    MedicineChunkSection.USAGE: ("main_item_ingr", "용법"),
    MedicineChunkSection.STORAGE: ("storage_method", "저장"),
    MedicineChunkSection.INGREDIENT: ("material_name", "주성분"),
    MedicineChunkSection.PRECAUTION_GENERAL: ("precautions", "일반주의"),
    MedicineChunkSection.ADVERSE_REACTION: ("side_effects", "이상반응"),
}


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Fetch a small medicine data sample and seed RAG chunks.",
    )
    parser.add_argument("--limit", type=int, default=50, help="Max rows to fetch (default: 50)")
    parser.add_argument("--api-key", type=str, default=None, help="data.go.kr API key (default: .env)")
    parser.add_argument(
        "--skip-embed",
        action="store_true",
        default=False,
        help="Skip chunk creation and embedding (DB structure only)",
    )
    return parser


def build_chunk_text(medicine: MedicineInfo, section: MedicineChunkSection) -> str:
    """Build the embedding-target text for one (medicine, section) pair.

    Applies a header prefix so the embedding captures both the drug
    identity and the section category alongside the body text.
    """
    attr_name, label = _SECTION_FIELDS[section]
    body = getattr(medicine, attr_name, None) or ""
    header = f"[{medicine.medicine_name}] {label}"
    if medicine.category:
        header += f" ({medicine.category})"
    return f"{header}\n{body.strip()}" if body.strip() else header


def iter_section_texts(medicine: MedicineInfo) -> Iterable[tuple[MedicineChunkSection, str]]:
    """Yield (section, chunk_text) pairs for every section that has content."""
    for section, (attr_name, _label) in _SECTION_FIELDS.items():
        body = getattr(medicine, attr_name, None) or ""
        if not body.strip():
            continue
        yield section, build_chunk_text(medicine, section)


def normalize_vector(vector: list[float]) -> list[float]:
    """L2-normalize a vector for cosine similarity."""
    arr = np.asarray(vector, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return vector
    return (arr / norm).tolist()


async def _fetch_sample_items(api_key: str, limit: int) -> list[dict]:
    """Fetch up to `limit` raw items from the public API (paginated)."""
    all_items: list[dict] = []
    params: dict = {"serviceKey": api_key, "type": "json", "pageNo": 1}
    async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT) as client:
        page = 1
        while len(all_items) < limit:
            params["pageNo"] = page
            params["numOfRows"] = min(100, limit - len(all_items))
            response = await client.get(_DETAIL_ENDPOINT, params=params)
            response.raise_for_status()
            body = response.json().get("body", {})
            items = body.get("items", []) or []
            if not items:
                break
            all_items.extend(items)
            total_count = body.get("totalCount", 0)
            logger.info(
                "page %d: +%d items (collected %d / target %d, total api=%d)",
                page,
                len(items),
                len(all_items),
                limit,
                total_count,
            )
            if len(all_items) >= total_count:
                break
            page += 1
    return all_items[:limit]


async def _embed_and_insert_chunks(medicine: MedicineInfo) -> int:
    """Generate chunks for one medicine, embed them, and bulk_create rows.

    Returns the number of chunks inserted.
    """
    from sentence_transformers import SentenceTransformer

    # Lazy singleton across the whole run — the sample sizes are small so
    # reloading per medicine would dominate runtime.
    global _MODEL
    try:
        model = _MODEL  # type: ignore[name-defined]
    except NameError:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        _MODEL = model

    pairs = list(iter_section_texts(medicine))
    if not pairs:
        return 0

    sections, texts = zip(*pairs, strict=True)
    loop = asyncio.get_event_loop()
    matrix = await loop.run_in_executor(None, lambda: model.encode(list(texts), show_progress_bar=False))
    chunks: list[MedicineChunk] = []
    for section, text, raw_vec in zip(sections, texts, matrix, strict=True):
        vector = normalize_vector(raw_vec.tolist())
        if len(vector) != EMBEDDING_DIMENSIONS:
            msg = f"Embedding dim mismatch: got {len(vector)}, expected {EMBEDDING_DIMENSIONS}"
            raise ValueError(msg)
        chunks.append(
            MedicineChunk(
                medicine_info_id=medicine.id,
                section=section.value,
                chunk_index=0,
                content=text,
                token_count=len(text),
                embedding=vector,
                model_version=EMBEDDING_MODEL_NAME,
            ),
        )
    await MedicineChunk.bulk_create(chunks, batch_size=100)
    return len(chunks)


async def fetch_sample_run(
    limit: int = 50,
    skip_embed: bool = False,
    api_key: str | None = None,
) -> dict[str, int]:
    """End-to-end sample ingestion: fetch -> upsert -> chunk + embed.

    Args:
        limit: Max rows to fetch from the API.
        skip_embed: When True, MedicineInfo rows are upserted but no
            chunks or embeddings are produced.
        api_key: data.go.kr API key; defaults to config.DATA_GO_KR_API_KEY.

    Returns:
        Stats dict with fetched / inserted / updated / chunks counts.
    """
    resolved_key = api_key or getattr(config, "DATA_GO_KR_API_KEY", None)
    if not resolved_key:
        raise RuntimeError("DATA_GO_KR_API_KEY is not set; pass --api-key or populate .env")

    await Tortoise.init(config=TORTOISE_ORM)
    try:
        logger.info("Fetching sample (limit=%d)", limit)
        raw_items = await _fetch_sample_items(resolved_key, limit)
        logger.info("Collected %d raw items", len(raw_items))

        # Reuse the team's filter + transform contract verbatim.
        # Accessing these as staticmethods is intentional; keeping behavior
        # identical to sync_medicine_data.py avoids schema drift.
        filtered = [
            item
            for item in raw_items
            if not MedicineDataService._is_hospital_only_injectable(item)  # noqa: SLF001
        ]
        transformed = [MedicineDataService._transform_item(item) for item in filtered]  # noqa: SLF001
        logger.info("After filter: %d items", len(transformed))

        service = MedicineDataService(api_key=resolved_key)
        stats = await service.repository.bulk_upsert(transformed)
        logger.info("Upsert: inserted=%d, updated=%d", stats["inserted"], stats["updated"])

        chunks_total = 0
        if not skip_embed:
            upserted_seqs = [row["item_seq"] for row in transformed if row.get("item_seq")]
            medicines = await MedicineInfo.filter(item_seq__in=upserted_seqs).all()
            logger.info("Embedding chunks for %d medicines...", len(medicines))
            for med in medicines:
                chunks_total += await _embed_and_insert_chunks(med)
            logger.info("Chunks inserted: %d", chunks_total)

        return {
            "fetched": len(raw_items),
            "inserted": stats["inserted"],
            "updated": stats["updated"],
            "chunks": chunks_total,
        }
    finally:
        await Tortoise.close_connections()


def main() -> int:
    """CLI entry point."""
    args = build_parser().parse_args()
    try:
        stats = asyncio.run(
            fetch_sample_run(limit=args.limit, skip_embed=args.skip_embed, api_key=args.api_key),
        )
    except Exception:
        logger.exception("fetch_sample failed")
        return 1
    logger.info("Done: %s", stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
