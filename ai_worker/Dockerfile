# AI Worker — 로컬 개발 이미지. prod 는 Dockerfile.prod 참조.
FROM python:3.13-slim

WORKDIR /app

# procps: healthcheck 의 pgrep 용
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
# app 그룹 포함 — ai_worker.utils.rag → app.dtos.rag → Tortoise 모델 의존 체인
RUN uv sync --group ai --group app --group dev --frozen

COPY ai_worker/ ./ai_worker/
COPY app/ ./app/

RUN chown -R appuser:appgroup /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD pgrep -f "python" || exit 1

CMD ["uv", "run", "--no-sync", "python", "-m", "ai_worker.main"]
