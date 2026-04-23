FROM python:3.13-slim

WORKDIR /app

# 시스템 의존성 설치 (캐시 레이어)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root 사용자 생성
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# uv 설치 (공식 이미지에서 복사)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 의존성 파일만 먼저 복사 (캐시 레이어 활용)
COPY pyproject.toml uv.lock ./

# 의존성 설치 (app + dev 그룹 — 로컬/개발 이미지. prod는 Dockerfile.prod 사용)
RUN uv sync --group app --group dev --frozen

# 소스 코드 복사
COPY app/ ./app/
COPY ai_worker/ ./ai_worker/

# 디렉토리 소유권 변경
RUN chown -R appuser:appgroup /app

# Non-root 사용자로 전환
USER appuser

# 포트 노출
EXPOSE 8000

# Healthcheck (compose의 healthcheck와 동일)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# 프로덕션 실행 명령 (개발 시 docker-compose에서 override)
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]
