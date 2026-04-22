"""Batch-based RAG data seeding for medicine_info.

Encodes every chunk text of `ai_worker/data/medicines.json` in a single
SentenceTransformer batch call and persists rows via MedicineInfo.bulk_create.
A 50-row seed runs in seconds; tens of thousands complete in minutes on CPU.

Usage:
    uv run python scripts/seed_rag_data.py           # Seed only new rows
    uv run python scripts/seed_rag_data.py --dry-run # Preview without DB writes
    uv run python scripts/seed_rag_data.py --force   # Wipe and re-seed

Design notes:
- Idempotent: `filter_new_medicines` skips names already in DB in one query.
- Batched encoding: `SentenceTransformer.encode(texts, batch_size=64)` is
  20-50x faster than per-text calls on CPU.
- Bulk insert: `MedicineInfo.bulk_create(batch_size=500)` avoids per-row
  round trips.
- Model/dim swap: change EMBEDDING_MODEL_NAME/EMBEDDING_DIMENSIONS in
  `app/services/rag/config.py` and add a migration that alters the
  `vector(N)` column dimension.
"""

import argparse
import asyncio
import hashlib
import json
import logging
from pathlib import Path
import sys

import numpy as np
from sentence_transformers import SentenceTransformer
from tortoise import Tortoise
from tqdm import tqdm

# Add project root so `app.*` imports resolve when run as a script.
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.databases import TORTOISE_ORM
from app.models.medicine_info import MedicineInfo
from app.services.rag.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL_NAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_ENCODE_BATCH_SIZE = 64
_DB_BATCH_SIZE = 500

_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Lazily load and cache the SentenceTransformer model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("Embedding model loaded successfully")
    return _embedding_model


def _l2_normalize_matrix(matrix: np.ndarray) -> np.ndarray:
    """Row-wise L2-normalize a 2-D embedding matrix (zeros preserved)."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def load_medicines_json(json_path: Path | None = None) -> list[dict]:
    """Load medicines data from JSON, returning [] if the file is missing."""
    if json_path is None:
        docker_path = Path("/app/ai_worker/data/medicines.json")
        local_path = Path(__file__).parent.parent / "ai_worker" / "data" / "medicines.json"

        if docker_path.exists():
            json_path = docker_path
        elif local_path.exists():
            json_path = local_path
        else:
            logger.warning("medicines.json not found in default locations")
            return []

    if not json_path.exists():
        logger.warning("JSON file not found: %s", json_path)
        return []

    with json_path.open(encoding="utf-8") as f:
        return json.load(f)


def build_chunk_text(medicine: dict) -> str:
    """Build the searchable chunk text embedded for a medicine row."""
    name = medicine["name"]
    ingredient = medicine["ingredient"]
    usage = medicine["usage"]
    disclaimer = medicine["disclaimer"]

    drugs = medicine.get("contraindicated_drugs", [])
    drugs_text = ", ".join(drugs) if drugs else "해당 없음"

    foods = medicine.get("contraindicated_foods", [])
    foods_text = ", ".join(foods) if foods else "해당 없음"

    return (
        f"[{name}]의 주성분은 {ingredient}이며, 주된 용도는 {usage}입니다. "
        f"복용 시 주의사항: {disclaimer}. "
        f"함께 복용하면 안 되는 병용 금기 약물: {drugs_text}. "
        f"피해야 할 금기 음식: {foods_text}."
    )


def build_chunk_texts(medicines: list[dict]) -> list[str]:
    """Build chunk texts for a list of medicines, preserving input order."""
    return [build_chunk_text(m) for m in medicines]


def compute_content_hash(content: str) -> str:
    """SHA-256 hex digest for dedupe / change detection."""
    return hashlib.sha256(content.encode()).hexdigest()


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Encode a batch of texts to L2-normalized embeddings in a single call.

    Args:
        texts: Input texts to encode.

    Returns:
        List of L2-normalized vectors aligned with `texts` order.
    """
    model = get_embedding_model()
    loop = asyncio.get_event_loop()
    matrix = await loop.run_in_executor(
        None,
        lambda: model.encode(texts, batch_size=_ENCODE_BATCH_SIZE, show_progress_bar=False),
    )
    normalized = _l2_normalize_matrix(np.asarray(matrix))
    return normalized.tolist()


async def filter_new_medicines(medicines: list[dict]) -> list[dict]:
    """Drop medicines whose `name` already exists in medicine_info.

    Performs a single `name IN (...)` query for idempotency, avoiding
    per-row existence checks.
    """
    if not medicines:
        return []
    names = [m["name"] for m in medicines]
    existing = await MedicineInfo.filter(name__in=names).values_list("name", flat=True)
    existing_set = set(existing)
    return [m for m in medicines if m["name"] not in existing_set]


async def seed_batch(medicines: list[dict], dry_run: bool = False) -> int:
    """Encode and bulk-insert a batch of medicines into medicine_info.

    Args:
        medicines: Medicine dicts already filtered for uniqueness.
        dry_run: When True, skip embedding and DB writes.

    Returns:
        Number of rows inserted (0 for dry_run or empty input).
    """
    if not medicines:
        return 0
    if dry_run:
        for m in medicines:
            logger.info("[DRY-RUN] Would seed: %s", m["name"])
        return 0

    texts = build_chunk_texts(medicines)
    embeddings = await generate_embeddings_batch(texts)

    for emb in embeddings:
        if len(emb) != EMBEDDING_DIMENSIONS:
            raise ValueError(f"Embedding dimension mismatch: got {len(emb)}, expected {EMBEDDING_DIMENSIONS}")

    objects = [
        MedicineInfo(
            name=m["name"],
            ingredient=m["ingredient"],
            usage=m["usage"],
            disclaimer=m["disclaimer"],
            contraindicated_drugs=m.get("contraindicated_drugs", []),
            contraindicated_foods=m.get("contraindicated_foods", []),
            embedding=emb,
            embedding_normalized=True,
        )
        for m, emb in zip(medicines, embeddings, strict=True)
    ]
    await MedicineInfo.bulk_create(objects, batch_size=_DB_BATCH_SIZE)
    return len(objects)


def _chunked(items: list[dict], size: int) -> list[list[dict]]:
    """Split a list into chunks of at most `size` items."""
    return [items[i : i + size] for i in range(0, len(items), size)]


async def seed_all(dry_run: bool = False, force: bool = False) -> None:
    """Seed every medicine in medicines.json into medicine_info.

    Args:
        dry_run: Preview only; no DB writes or embedding calls.
        force: Drop all existing rows before seeding.
    """
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        medicines = load_medicines_json()
        if not medicines:
            logger.warning("No medicines loaded; aborting seeding.")
            return

        logger.info("Loaded %d medicines from JSON", len(medicines))

        if force and not dry_run:
            deleted = await MedicineInfo.all().delete()
            logger.info("[FORCE] Deleted %d existing medicine_info rows", deleted)

        to_seed = medicines if force else await filter_new_medicines(medicines)
        if not to_seed:
            logger.info("All medicines already seeded; nothing to do.")
            return

        logger.info("Seeding %d new medicines in batches of %d", len(to_seed), _ENCODE_BATCH_SIZE)

        inserted = 0
        batches = _chunked(to_seed, _ENCODE_BATCH_SIZE)
        for batch in tqdm(batches, desc="Seeding", unit="batch"):
            inserted += await seed_batch(batch, dry_run=dry_run)

        logger.info("Seeding complete. Inserted %d rows.", inserted)
    finally:
        await Tortoise.close_connections()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Seed medicine_info RAG data")
    parser.add_argument("--dry-run", action="store_true", help="Preview without DB writes")
    parser.add_argument("--force", action="store_true", help="Delete existing rows first")
    args = parser.parse_args()

    asyncio.run(seed_all(dry_run=args.dry_run, force=args.force))


if __name__ == "__main__":
    main()
