r"""medicine_info → medicine_chunk 청킹 + 임베딩 1회성 batch.

PLAN.md (feature/RAG) §4 Step 4-B — 32K medicine_info 의 raw XML 을
ARTICLE 단위로 청킹하고, OpenAI text-embedding-3-large (3072d) 으로
임베딩한 뒤 medicine_chunk 에 INSERT 한다.

흐름:
1. Tortoise.init
2. medicine_info 모두 순회 (--batch 단위, default 50)
3. 각 row 의 ee_doc_data / ud_doc_data / nb_doc_data XML 파싱
4. ARTICLE → classify_article_section → MedicineChunkSection
5. content 조립 ([약: name] [section_kr]\\n{title}\\n{body})
6. 토큰 길이 추정 (한국어 1.5자=1tok 단순) — 8000 초과 시 chunk_index 분할
7. 한 medicine 의 모든 chunk 를 OpenAI Embedding API batch 호출
8. medicine_chunk INSERT (ON CONFLICT (medicine_info_id, section, chunk_index) DO NOTHING)
9. progress 로그 (매 50 medicine 마다)

멱등성:
- unique constraint 위반 시 SKIP — 재실행 시 이미 INSERT 된 row 영향 X
- 중간 실패 시 그 medicine 부터 재시작 가능 (--resume-from)

Usage (EC2 fastapi 컨테이너 안에서):
    docker compose -f ~/AI_02_06/docker-compose.prod.yml exec -d fastapi \\
      python -m scripts.embed_medicine_chunks --batch 50 --concurrency 5

Cost (estimate):
    32K medicines x ~6 sections = ~192K chunks x ~500 tok = 96M tok
    text-embedding-3-large @ $0.13/1M = ~$12.5
"""

import argparse
import asyncio
import logging
import time

from openai import AsyncOpenAI
from tortoise import Tortoise
from tortoise.transactions import in_transaction

from app.core.config import config
from app.db.databases import TORTOISE_ORM
from app.models.medicine_chunk import MedicineChunkSection
from app.models.medicine_info import MedicineInfo
from app.services.medicine_doc_parser import (
    Article,
    classify_article_section,
    parse_doc_articles,
)

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("embed_medicine_chunks")
logging.getLogger("httpx").setLevel(logging.WARNING)

# ── 상수 ───────────────────────────────────────────────────────────
EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMENSIONS = 3072
EMBEDDING_PRICE_PER_1M = 0.13  # USD

# OpenAI text-embedding-3-large input 한도 = 8192 tok. 분할 한도는 더 보수적
# 으로 4000 tok (한국어 토큰화는 char/tok 비율이 변동 커서 안전 마진 필요).
MAX_TOKENS_PER_CHUNK = 4000

# 한국어 평균 0.5~1자 = 1 token (cl100k_base 기준). tiktoken 미설치 환경에선
# 0.5 로 보수적 추정 (실제 토큰 수보다 *많이* 잡혀 분할이 적극적으로 일어남).
CHARS_PER_TOKEN = 0.5

# OpenAI Embedding batch input 한도는 매우 크지만 (지금은 메모리/네트워크
# 제약 위주) 안전하게 100 chunks per call.
EMBED_BATCH_SIZE = 100

# Retry: rate limit / connection error 시 exponential backoff
MAX_RETRIES = 4
INITIAL_BACKOFF = 1.0  # sec

# section 한국어 표시 (content prefix 용)
_SECTION_KR: dict[MedicineChunkSection, str] = {
    MedicineChunkSection.OVERVIEW: "개요",
    MedicineChunkSection.INTAKE_GUIDE: "복용법",
    MedicineChunkSection.DRUG_INTERACTION: "약물 상호작용",
    MedicineChunkSection.LIFESTYLE_INTERACTION: "생활 상호작용",
    MedicineChunkSection.ADVERSE_REACTION: "이상반응",
    MedicineChunkSection.SPECIAL_EVENT: "특수 상황",
}


# ── 파싱 + 청킹 ────────────────────────────────────────────────────
def _articles_for_medicine(med: MedicineInfo) -> list[tuple[Article, MedicineChunkSection]]:
    """medicine_info 의 3 raw XML 을 ARTICLE 리스트로 합쳐 section 분류한다.

    EE_DOC_DATA — 효능/효과 (대부분 OVERVIEW)
    UD_DOC_DATA — 용법/용량 (대부분 INTAKE_GUIDE)
    NB_DOC_DATA — 사용상의 주의 (DRUG_INTERACTION / ADVERSE_REACTION /
                  LIFESTYLE_INTERACTION / SPECIAL_EVENT 분기)
    """
    classified: list[tuple[Article, MedicineChunkSection]] = []

    for source_xml, default_section in (
        (med.ee_doc_data, MedicineChunkSection.OVERVIEW),
        (med.ud_doc_data, MedicineChunkSection.INTAKE_GUIDE),
        (med.nb_doc_data, None),
    ):
        for article in parse_doc_articles(source_xml):
            if not article.body and not article.title:
                continue
            section = classify_article_section(article.title) if default_section is None else default_section
            classified.append((article, section))

    return classified


def _estimate_tokens(text: str) -> int:
    """한국어 단순 추정 — 1.5자 = 1 토큰."""
    return int(len(text) / CHARS_PER_TOKEN) + 1


def _format_chunk_content(medicine_name: str, section: MedicineChunkSection, article: Article) -> str:
    """청크 임베딩 입력 텍스트 — 헤더 prefix + ARTICLE 본문."""
    section_kr = _SECTION_KR.get(section, section.value)
    parts = [f"[약: {medicine_name}] [{section_kr}]"]
    if article.title:
        parts.append(article.title)
    if article.body:
        parts.append(article.body)
    return "\n".join(parts)


def _truncate_to_char_limit(text: str, max_chars: int) -> str:
    """OpenAI 한도 (8192 tok) 안전 보장 — char 단위 hard cap.

    한 줄이 max_tokens 초과하는 케이스 (긴 PARAGRAPH 단일 줄) 도 최후 잘라낸다.
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _split_long_content(content: str, max_tokens: int = MAX_TOKENS_PER_CHUNK) -> list[str]:
    """토큰 한도 초과 시 줄바꿈 단위로 분할해 chunk_index 0,1,2... 로 사용."""
    if _estimate_tokens(content) <= max_tokens:
        return [content]

    # 한도를 보장하는 char 상한 (CHARS_PER_TOKEN=0.5 면 max_tokens=4000 → 2000 chars)
    max_chars = int(max_tokens * CHARS_PER_TOKEN)

    lines = content.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for line in lines:
        # 한 줄 자체가 한도 초과 시 hard truncate
        if _estimate_tokens(line) > max_tokens:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_tokens = 0
            chunks.append(_truncate_to_char_limit(line, max_chars))
            continue

        line_tokens = _estimate_tokens(line)
        if current_tokens + line_tokens > max_tokens and current:
            chunks.append("\n".join(current))
            current = [line]
            current_tokens = line_tokens
        else:
            current.append(line)
            current_tokens += line_tokens

    if current:
        chunks.append("\n".join(current))

    # 최종 안전망: 어느 chunk 도 hard char limit 초과 안 하도록
    return [_truncate_to_char_limit(c, max_chars * 2) for c in chunks]


def _build_chunks_for_medicine(med: MedicineInfo) -> list[tuple[MedicineChunkSection, int, str, int]]:
    """한 medicine 의 모든 (section, chunk_index, content, token_count) 리스트.

    같은 section 의 ARTICLE 이 여러 개면 chunk_index 가 0, 1, 2... 로 순차.
    한 ARTICLE 이 토큰 한도 초과면 _split_long_content 로 다시 분할 (이때도
    chunk_index 가 그 section 내에서 계속 증가).
    """
    section_counter: dict[MedicineChunkSection, int] = {}
    out: list[tuple[MedicineChunkSection, int, str, int]] = []

    for article, section in _articles_for_medicine(med):
        full_content = _format_chunk_content(med.medicine_name, section, article)
        for sub in _split_long_content(full_content):
            idx = section_counter.get(section, 0)
            section_counter[section] = idx + 1
            out.append((section, idx, sub, _estimate_tokens(sub)))

    return out


# ── OpenAI Embedding 호출 (retry) ──────────────────────────────────
async def _embed_with_retry(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    """Batch input 을 한 번에 임베딩, rate limit / connection 오류 시 retry."""
    backoff = INITIAL_BACKOFF
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=texts,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            return [d.embedding for d in response.data]
        except Exception as exc:
            if attempt >= MAX_RETRIES:
                logger.exception("Embedding failed after %d attempts", MAX_RETRIES)
                raise
            logger.warning(
                "Embedding attempt %d/%d failed (%s: %s) — retry in %.1fs",
                attempt,
                MAX_RETRIES,
                type(exc).__name__,
                str(exc)[:100],
                backoff,
            )
            await asyncio.sleep(backoff)
            backoff *= 2

    raise RuntimeError("unreachable")


# ── INSERT (raw SQL, vector pgvector 형식) ──────────────────────────
def _vector_literal(embedding: list[float]) -> str:
    """Pgvector 의 vector(N) 입력 형식 — '[v1,v2,...]' 문자열."""
    return "[" + ",".join(f"{v:.6f}" for v in embedding) + "]"


async def _insert_chunks_batch(
    rows: list[tuple[int, MedicineChunkSection, int, str, int, list[float]]],
) -> int:
    """rows: (medicine_info_id, section, chunk_index, content, token_count, embedding)
    멱등성을 위해 ON CONFLICT DO NOTHING.
    """
    if not rows:
        return 0

    placeholders: list[str] = []
    params: list = []
    for i, (mid, section, idx, content, tok, emb) in enumerate(rows):
        base = i * 7
        placeholders.append(
            f"(${base + 1}, ${base + 2}, ${base + 3}, ${base + 4}, ${base + 5}, ${base + 6}::vector, ${base + 7})"
        )
        params.extend([mid, section.value, idx, content, tok, _vector_literal(emb), EMBEDDING_MODEL])

    sql = f"""
        INSERT INTO medicine_chunk
            (medicine_info_id, section, chunk_index, content, token_count, embedding, model_version)
        VALUES {",".join(placeholders)}
        ON CONFLICT (medicine_info_id, section, chunk_index) DO NOTHING
    """  # noqa: S608

    from tortoise import connections

    await connections.get("default").execute_query(sql, params)
    # asyncpg 의 INSERT ... ON CONFLICT 결과 파싱 일관 X.
    # rows 길이로 카운트 (재실행 시 ON CONFLICT 가 silent skip 이라 정확).
    return len(rows)


# ── 메인 처리 루프 ───────────────────────────────────────────────────
async def process_medicines(
    *,
    batch_size: int,
    concurrency: int,
    resume_from: int,
    medicine_ids: list[int] | None = None,
) -> None:
    """모든 medicine_info 를 순회하며 청킹 + 임베딩 + INSERT.

    Args:
        batch_size: medicine_info 페이지 크기.
        concurrency: 동시 medicine 처리 병렬도 (OpenAI 호출 병렬 = 이 값).
        resume_from: 시작 medicine_info.id (재시작용). medicine_ids 지정 시 무시.
        medicine_ids: 특정 ID 만 처리 (None 이면 resume_from 이후 모두).
    """
    api_key = config.OPENAI_API_KEY
    if not api_key:
        msg = "OPENAI_API_KEY 미설정 — 본 batch 는 OpenAI 호출 필수"
        raise SystemExit(msg)
    client = AsyncOpenAI(api_key=api_key)

    if medicine_ids is not None:
        total = len(medicine_ids)
        scope_desc = f"ids={len(medicine_ids)}"
    else:
        total = await MedicineInfo.filter(id__gte=resume_from).count()
        scope_desc = f"resume_from={resume_from}"
    logger.info(
        "Embedding %d medicines (batch=%d, concurrency=%d, %s, model=%s, dim=%d)",
        total,
        batch_size,
        concurrency,
        scope_desc,
        EMBEDDING_MODEL,
        EMBEDDING_DIMENSIONS,
    )

    semaphore = asyncio.Semaphore(concurrency)
    processed = 0
    inserted_total = 0
    tokens_total = 0
    start = time.time()

    async def _process_one(med: MedicineInfo) -> tuple[int, int]:
        async with semaphore:
            chunks = _build_chunks_for_medicine(med)
            if not chunks:
                return 0, 0

            contents = [c[2] for c in chunks]
            embeddings: list[list[float]] = []
            # OpenAI batch 한도 안에서 분할 호출
            for offset in range(0, len(contents), EMBED_BATCH_SIZE):
                sub = contents[offset : offset + EMBED_BATCH_SIZE]
                vecs = await _embed_with_retry(client, sub)
                embeddings.extend(vecs)

            rows = [
                (med.id, sec, idx, content, tok, emb)
                for (sec, idx, content, tok), emb in zip(chunks, embeddings, strict=True)
            ]
            async with in_transaction("default"):
                affected = await _insert_chunks_batch(rows)
            return affected, sum(tok for (_, _, _, tok) in chunks)

    offset = 0
    while True:
        if medicine_ids is not None:
            ids_page = medicine_ids[offset : offset + batch_size]
            if not ids_page:
                break
            page = await MedicineInfo.filter(id__in=ids_page).order_by("id").all()
        else:
            page = await MedicineInfo.filter(id__gte=resume_from).order_by("id").offset(offset).limit(batch_size).all()
        if not page:
            break

        results = await asyncio.gather(
            *[_process_one(m) for m in page],
            return_exceptions=True,
        )

        for med, result in zip(page, results, strict=True):
            if isinstance(result, BaseException):
                logger.error("medicine_info id=%d 처리 실패: %s: %s", med.id, type(result).__name__, result)
                continue
            inserted, tokens = result
            inserted_total += inserted
            tokens_total += tokens

        processed += len(page)
        elapsed = time.time() - start
        rate = processed / max(elapsed, 1)
        eta_min = (total - processed) / max(rate, 0.001) / 60
        cost_est = tokens_total / 1_000_000 * EMBEDDING_PRICE_PER_1M
        logger.info(
            "Progress: %d/%d (%.1f%%) chunks=%d tokens=%dK cost=$%.2f rate=%.1f/s eta=%.1fmin",
            processed,
            total,
            processed / max(total, 1) * 100,
            inserted_total,
            tokens_total // 1000,
            cost_est,
            rate,
            eta_min,
        )

        offset += batch_size

    logger.info(
        "Done — medicines processed=%d chunks_inserted=%d tokens=%dK cost=$%.2f elapsed=%.1fmin",
        processed,
        inserted_total,
        tokens_total // 1000,
        tokens_total / 1_000_000 * EMBEDDING_PRICE_PER_1M,
        (time.time() - start) / 60,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="medicine_info → medicine_chunk 청킹 + 임베딩 batch (1회성)",
    )
    parser.add_argument("--batch", type=int, default=50, help="medicine_info 페이지 크기 (default: 50)")
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="동시 medicine 처리 병렬도 (default: 5). OpenAI rate limit 따라 조정",
    )
    parser.add_argument("--resume-from", type=int, default=0, help="시작 medicine_info.id (재시작용)")
    parser.add_argument(
        "--medicine-ids",
        type=str,
        default=None,
        help="콤마 구분 medicine_info.id 목록 — 이 인자가 있으면 resume-from 무시하고 해당 ID 만 처리 (예: 1,5,12,42)",
    )
    parser.add_argument(
        "--name-like",
        type=str,
        default=None,
        help="콤마 구분 ILIKE 패턴 (medicine_name + item_eng_name 매칭)",
    )
    return parser.parse_args()


async def main_async(args: argparse.Namespace) -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        ids: list[int] | None = None
        if args.medicine_ids:
            ids = [int(x.strip()) for x in args.medicine_ids.split(",") if x.strip()]
            logger.info("ID 목록 모드 — %d medicines", len(ids))
        elif args.name_like:
            patterns = [p.strip() for p in args.name_like.split(",") if p.strip()]
            from tortoise.expressions import Q

            cond = Q()
            for p in patterns:
                cond |= Q(medicine_name__ilike=p) | Q(item_eng_name__ilike=p)
            matched = await MedicineInfo.filter(cond).values_list("id", flat=True)
            ids = list(matched)
            logger.info("name-like 매칭 — %d medicines (patterns=%s)", len(ids), patterns)

        await process_medicines(
            batch_size=args.batch,
            concurrency=args.concurrency,
            resume_from=args.resume_from,
            medicine_ids=ids,
        )
    finally:
        await Tortoise.close_connections()


def main() -> None:
    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
