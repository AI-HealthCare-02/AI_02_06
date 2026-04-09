FROM python:3.13-slim

WORKDIR /app

# 시스템 의존성 설치 (healthcheck용 procps)
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Non-root 사용자 생성
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# 1. uv 설치 (공식 이미지에서 복사해오는 가장 깔끔한 방법)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# 2. 의존성 패키지 관리 파일을 컨테이너 내부에 복사합니다.
COPY pyproject.toml uv.lock ./

# 3. pyproject.toml에 명시된 의존성 패키지 중에서 'ai' 그룹만 설치합니다.
RUN uv sync --group ai --no-dev --frozen

# 4. 로컬 소스 코드를 컨테이너 내부로 복사합니다.
COPY ai_worker/ ./ai_worker/

# 디렉토리 소유권 변경
RUN chown -R appuser:appgroup /app

# Non-root 사용자로 전환
USER appuser

# Healthcheck (python 프로세스 확인)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD pgrep -f "python" || exit 1

# 5. AI Worker 실행
CMD ["uv", "run", "--no-sync", "python", "-m", "ai_worker.main"]
