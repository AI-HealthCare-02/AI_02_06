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

# 3. pyproject.toml에 명시된 의존성 중 'ai' + 'app' + 'dev' 그룹 설치.
#    'app' 그룹이 필요한 이유: ai_worker.utils.rag 가 app.dtos.rag 를 import 하고
#    그 안에서 Tortoise 모델 (MedicineChunk, MedicineInfo) 클래스 평가가 일어난다.
#    Tortoise 자체는 ai-worker 에서 DB 접속하지 않지만, 모델 클래스 import 만으로도
#    tortoise-orm 라이브러리가 sys.path 에 있어야 한다.
RUN uv sync --group ai --group app --group dev --frozen

# 4. 로컬 소스 코드를 컨테이너 내부로 복사합니다.
#    ai_worker.providers.llm -> ai_worker.utils.rag -> app.core.config 의존 체인 때문에
#    런타임에 app/ 모듈도 import 가능해야 하므로 함께 COPY 한다.
COPY ai_worker/ ./ai_worker/
COPY app/ ./app/

# 5. 임베딩 모델 pre-download (HF 허브 → 이미지 내부 캐시).
#    이렇게 해두면 런타임 컨테이너는 네트워크 없이도 모델을 로드할 수 있고
#    첫 기동 시간을 30~40초 단축할 수 있다. 메모리 warm-up 은 별개이며
#    컨테이너 부팅 시 ai_worker.main 에서 추가로 수행한다.
ENV HF_HOME=/app/.cache/huggingface
RUN uv run --no-sync python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jhgan/ko-sroberta-multitask')"

# 디렉토리 소유권 변경
RUN chown -R appuser:appgroup /app

# Non-root 사용자로 전환
USER appuser

# Healthcheck (python 프로세스 확인)
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD pgrep -f "python" || exit 1

# 6. AI Worker 실행
CMD ["uv", "run", "--no-sync", "python", "-m", "ai_worker.main"]
