"""RAG Data Seeding Script for medicine_info.

Loads `ai_worker/data/medicines.json` into the `medicine_info` pgvector
table. Generates L2-normalized SentenceTransformer embeddings for the
full formatted chunk text of each entry.

Usage:
    uv run python scripts/seed_rag_data.py           # Seed new rows only
    uv run python scripts/seed_rag_data.py --dry-run # Preview without DB writes
    uv run python scripts/seed_rag_data.py --force   # Delete existing rows then re-seed
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

# Add project root so app.* imports resolve when run as a script.
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.databases import TORTOISE_ORM
from app.models.medicine_info import MedicineInfo
from app.services.rag.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL_NAME

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Lazily load and cache the SentenceTransformer model."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("Embedding model loaded successfully")
    return _embedding_model


def normalize_vector(vector: list[float]) -> list[float]:
    """L2-normalize a vector for cosine similarity."""
    np_vec = np.array(vector)
    norm = np.linalg.norm(np_vec)
    if norm == 0:
        return vector
    return (np_vec / norm).tolist()


def load_medicines_json(json_path: Path | None = None) -> list[dict]:
    """Load medicines data from JSON, returning [] if the file is missing.

    Args:
        json_path: Explicit JSON path. If None, tries Docker then local path.
    """
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


def compute_content_hash(content: str) -> str:
    """SHA-256 hex digest for dedupe / change detection."""
    return hashlib.sha256(content.encode()).hexdigest()


async def generate_embedding(text: str) -> list[float]:
    """Encode text to an L2-normalized embedding vector."""
    model = get_embedding_model()
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(None, model.encode, text)
    return normalize_vector(embedding.tolist())


async def seed_medicine_to_db(medicine: dict, dry_run: bool = False) -> None:
    """Insert a single medicine into medicine_info (skip if name exists).

    Args:
        medicine: Medicine dict from medicines.json.
        dry_run: When True, log intent only and skip DB interaction.
    """
    chunk_text = build_chunk_text(medicine)

    if dry_run:
        logger.info("[DRY-RUN] Would seed: %s", medicine["name"])
        logger.info("  Chunk text: %s...", chunk_text[:100])
        return

    existing = await MedicineInfo.filter(name=medicine["name"]).first()
    if existing:
        logger.info("[SKIP] Already exists: %s", medicine["name"])
        return

    embedding = await generate_embedding(chunk_text)
    if len(embedding) != EMBEDDING_DIMENSIONS:
        raise ValueError(f"Embedding dimension mismatch: got {len(embedding)}, expected {EMBEDDING_DIMENSIONS}")

    await MedicineInfo.create(
        name=medicine["name"],
        ingredient=medicine["ingredient"],
        usage=medicine["usage"],
        disclaimer=medicine["disclaimer"],
        contraindicated_drugs=medicine.get("contraindicated_drugs", []),
        contraindicated_foods=medicine.get("contraindicated_foods", []),
        embedding=embedding,
        embedding_normalized=True,
    )
    logger.info("[CREATED] %s", medicine["name"])


async def seed_all(dry_run: bool = False, force: bool = False) -> None:
    """Seed every medicine in medicines.json into medicine_info.

    Args:
        dry_run: Skip DB writes entirely.
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

        for medicine in medicines:
            await seed_medicine_to_db(medicine, dry_run=dry_run)

        logger.info("Seeding complete")
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
