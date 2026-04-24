# FastAPI — 로컬 개발 이미지. prod 는 Dockerfile.prod 참조.
FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --group app --group dev --frozen

COPY app/ ./app/
COPY ai_worker/ ./ai_worker/

RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 로컬 compose 는 --reload 로 override. 이미지 단독 실행 시 기본 명령.
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]
