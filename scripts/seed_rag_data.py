"""RAG Data Seeding Script.

This script loads medicines.json data into pgvector database
for RAG (Retrieval-Augmented Generation) functionality.

Usage:
    uv run python scripts/seed_rag_data.py           # Normal execution
    uv run python scripts/seed_rag_data.py --dry-run # Preview without DB insert
    uv run python scripts/seed_rag_data.py --force   # Delete existing and re-seed
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

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.databases import TORTOISE_ORM
from app.models.vector_models import (
    ChunkType,
    DocumentChunk,
    DocumentType,
    PharmaceuticalDocument,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Embedding model configuration (same as RAG pipeline)
EMBEDDING_MODEL = "jhgan/ko-sroberta-multitask"
EMBEDDING_DIMENSIONS = 768

# Global embedding model (initialized lazily)
_embedding_model: SentenceTransformer | None = None


def get_embedding_model() -> SentenceTransformer:
    """Get or initialize embedding model.

    Returns:
        SentenceTransformer: Embedding model instance.
    """
    global _embedding_model
    if _embedding_model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info("Embedding model loaded successfully")
    return _embedding_model


def normalize_vector(vector: list[float]) -> list[float]:
    """L2-normalize a vector for cosine similarity.

    Args:
        vector: Input vector.

    Returns:
        Unit-length vector.
    """
    np_vec = np.array(vector)
    norm = np.linalg.norm(np_vec)
    if norm == 0:
        return vector
    return (np_vec / norm).tolist()


def load_medicines_json(json_path: Path | None = None) -> list[dict]:
    """Load medicines data from JSON file.

    Args:
        json_path: Path to JSON file. If None, uses default path.

    Returns:
        List of medicine dictionaries, or empty list if file not found.
    """
    if json_path is None:
        # Default paths
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
        logger.warning(f"JSON file not found: {json_path}")
        return []

    with json_path.open(encoding="utf-8") as f:
        return json.load(f)


def build_chunk_text(medicine: dict) -> str:
    """Build chunk text from medicine data.

    Creates a formatted text chunk containing all medicine information
    in a natural language format suitable for RAG retrieval.

    Args:
        medicine: Medicine dictionary from JSON.

    Returns:
        Formatted chunk text string.
    """
    name = medicine["name"]
    ingredient = medicine["ingredient"]
    usage = medicine["usage"]
    disclaimer = medicine["disclaimer"]

    # Format contraindicated drugs
    drugs = medicine.get("contraindicated_drugs", [])
    drugs_text = ", ".join(drugs) if drugs else "해당 없음"

    # Format contraindicated foods
    foods = medicine.get("contraindicated_foods", [])
    foods_text = ", ".join(foods) if foods else "해당 없음"

    return (
        f"[{name}]의 주성분은 {ingredient}이며, 주된 용도는 {usage}입니다. "
        f"복용 시 주의사항: {disclaimer}. "
        f"함께 복용하면 안 되는 병용 금기 약물: {drugs_text}. "
        f"피해야 할 금기 음식: {foods_text}."
    )


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of content.

    Args:
        content: Text content to hash.

    Returns:
        Hexadecimal hash string.
    """
    return hashlib.sha256(content.encode()).hexdigest()


def extract_keywords(medicine: dict) -> list[str]:
    """Extract keywords from medicine data.

    Args:
        medicine: Medicine dictionary from JSON.

    Returns:
        List of keywords for search.
    """
    keywords = []

    # Add medicine name and ingredient as keywords
    keywords.append(medicine["name"])
    keywords.extend(medicine["ingredient"].split(", "))

    # Add contraindicated drugs (excluding "해당 없음")
    keywords.extend(drug for drug in medicine.get("contraindicated_drugs", []) if drug != "해당 없음")

    # Add contraindicated foods (excluding "해당 없음")
    keywords.extend(food for food in medicine.get("contraindicated_foods", []) if food != "해당 없음")

    # Add usage
    keywords.append(medicine["usage"])

    return keywords


async def generate_embedding(text: str) -> list[float]:
    """Generate embedding for text using SentenceTransformer.

    Args:
        text: Text to generate embedding for.

    Returns:
        List of float values representing the normalized embedding.
    """
    model = get_embedding_model()
    loop = asyncio.get_event_loop()
    embedding = await loop.run_in_executor(None, model.encode, text)
    return normalize_vector(embedding.tolist())


async def seed_medicine_to_db(medicine: dict, dry_run: bool = False) -> None:
    """Seed a single medicine to database.

    Creates PharmaceuticalDocument and DocumentChunk for the medicine.

    Args:
        medicine: Medicine dictionary from JSON.
        dry_run: If True, skip actual DB insertion.
    """
    chunk_text = build_chunk_text(medicine)
    content_hash = compute_content_hash(chunk_text)
    keywords = extract_keywords(medicine)

    if dry_run:
        logger.info(f"[DRY-RUN] Would create: {medicine['name']}")
        logger.info(f"  Chunk text: {chunk_text[:100]}...")
        logger.info(f"  Keywords: {keywords[:5]}...")
        return

    # Check if already exists
    existing_chunk = await DocumentChunk.filter(content_hash=content_hash).first()
    if existing_chunk:
        logger.info(f"[SKIP] Already exists: {medicine['name']}")
        return

    # Generate embedding
    embedding = await generate_embedding(chunk_text)

    # Create PharmaceuticalDocument
    doc = await PharmaceuticalDocument.create(
        title=medicine["name"],
        document_type=DocumentType.MEDICINE_INFO,
        content=chunk_text,
        content_hash=compute_content_hash(medicine["name"]),
        medicine_names=[medicine["name"]],
        target_conditions=[],
        language="ko",
    )

    # Create DocumentChunk
    await DocumentChunk.create(
        document=doc,
        chunk_index=0,
        chunk_type=ChunkType.GENERAL,
        content=chunk_text,
        content_hash=content_hash,
        section_title=medicine["name"],
        word_count=len(chunk_text.split()),
        char_count=len(chunk_text),
        keywords=keywords,
        medicine_names=[medicine["name"]],
        dosage_info={},
        target_conditions=[],
        contraindicated_conditions=[],
        embedding=embedding,
        embedding_normalized=False,
    )

    logger.info(f"[CREATED] {medicine['name']}")


async def clear_existing_data() -> None:
    """Clear existing RAG data from database."""
    # Delete chunks first (foreign key constraint)
    chunk_count = await DocumentChunk.all().delete()
    doc_count = await PharmaceuticalDocument.all().delete()
    logger.info(f"Deleted {chunk_count} chunks and {doc_count} documents")


async def run(dry_run: bool = False, force: bool = False) -> None:
    """Main execution function.

    Args:
        dry_run: If True, preview without DB insertion.
        force: If True, delete existing data before seeding.
    """
    # Initialize database connection
    await Tortoise.init(config=TORTOISE_ORM)

    try:
        # Load medicines data
        medicines = load_medicines_json()
        if not medicines:
            logger.error("No medicines data found. Exiting.")
            return

        logger.info(f"Loaded {len(medicines)} medicines from JSON")

        if force and not dry_run:
            logger.info("Force mode: clearing existing data...")
            await clear_existing_data()

        # Seed each medicine
        for i, medicine in enumerate(medicines, 1):
            logger.info(f"Processing [{i}/{len(medicines)}]: {medicine['name']}")
            await seed_medicine_to_db(medicine, dry_run=dry_run)

        logger.info("Seeding completed successfully!")

    finally:
        await Tortoise.close_connections()


async def main() -> None:
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="Seed medicines.json data into pgvector database for RAG")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without actual DB insertion",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing data before seeding",
    )

    args = parser.parse_args()

    try:
        await run(dry_run=args.dry_run, force=args.force)
    except Exception:
        logger.exception("Error occurred during seeding")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
