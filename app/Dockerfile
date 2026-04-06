FROM python:3.13-slim

WORKDIR /app

# 시스템 의존성 설치 (캐시 레이어)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# uv 설치 (공식 이미지에서 복사)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 의존성 파일만 먼저 복사 (캐시 레이어 활용)
COPY pyproject.toml uv.lock ./

# 의존성 설치 (app 그룹만)
RUN uv sync --group app --no-dev --frozen

# 소스 코드 복사 (volumes로 마운트되므로 개발 시에는 무시됨)
COPY ./app ./app

# 포트 노출
EXPOSE 8000

# 프로덕션 실행 명령 (개발 시 docker-compose에서 override)
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "3"]
