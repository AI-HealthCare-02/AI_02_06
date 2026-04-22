# Architecture

## 전체 시스템 구성

```
                        ┌─────────────────────────────────────────────┐
                        │               Docker Network (ws)            │
                        │                                              │
  Client ──── :80 ───▶  │  Nginx  ──── /api/* ────▶  FastAPI (:8000)  │
                        │                                │             │
                        │                           Tortoise ORM       │
                        │                                │             │
                        │  AI Worker ◀── Redis ──────────┤             │
                        │                                │             │
                        │                             PostgreSQL       │
                        └─────────────────────────────────────────────┘
```

## 서비스 레이어

| 서비스 | 역할 | 기술 |
|---|---|---|
| Nginx | 리버스 프록시, `/api/*` 요청 라우팅 | nginx:latest |
| FastAPI | REST API 서버, 인증/비즈니스 로직 처리 | FastAPI + Uvicorn |
| AI Worker | 모델 추론/학습 비동기 처리 | Python Worker |
| PostgreSQL | 영구 데이터 저장 | PostgreSQL 15 |
| Redis | 메시지 브로커 / 캐싱 | Redis Alpine |

## FastAPI 내부 구조

```
app/
├── apis/v1/          # 라우터 (auth, user)
├── services/         # 비즈니스 로직
│   └── rag/          # RAG 파이프라인 (의도 분류 → 검색 → 응답)
├── repositories/     # DB 접근 계층
├── models/           # Tortoise ORM 테이블 정의 (medicine_info 포함)
├── dtos/             # 요청/응답 Pydantic 스키마
├── dependencies/     # FastAPI 의존성 (JWT 인증)
├── utils/jwt/        # JWT 토큰 발급·검증
├── validators/       # 입력값 검증
├── core/             # 설정(pydantic-settings), 로거
└── db/               # DB 초기화, Aerich 마이그레이션, VectorField
```

요청 흐름: `Router → Service → Repository → DB`

## RAG 레이어 (app/services/rag/)

```
ChatModal
   │ POST /api/v1/messages/ask
   ▼
MessageService.ask_and_reply_with_owner_check
   │
   ▼
RAGPipeline.ask  ───────────────────────────────┐
   │                                             │
   ├─(1) IntentClassifier       키워드·규칙 기반 │
   │                                             │
   ├─(2) EmbeddingProvider      SentenceTransformer (768d)
   │                                             │
   ├─(3) HybridRetriever        pgvector cosine 0.7 + 키워드 0.3
   │        │                                   │
   │        ▼                                   │
   │    medicine_info           HNSW + GIN      │
   │                                             │
   └─(4) RAGGenerator           OpenAI GPT-4o-mini ──► 응답
```

### 구성 요소

| 파일 | 역할 |
|---|---|
| `pipeline.py` | 4단계 오케스트레이션 (의도 → 임베딩 → 검색 → 응답) |
| `config.py` | `EMBEDDING_MODEL_NAME`, `EMBEDDING_DIMENSIONS` 단일 소스 상수 |
| `intent/classifier.py` | 키워드 기반 IntentType 분류 (LLM 미사용) |
| `providers/sentence_transformer.py` | 로컬 한국어 임베딩 (L2 정규화) |
| `retrievers/hybrid.py` | pgvector + 키워드 하이브리드 검색 (medicine_info 대상) |
| `tools/` | 의도별 도구 라우팅 (DB 조회 / 외부 API) |

### 모델 교체 절차

1. `app/services/rag/config.py`의 두 상수 수정
2. `medicine_info.embedding`의 `vector(N)` 차원을 바꾸는 Aerich 마이그레이션 추가
3. `scripts/seed_rag_data.py`로 재시딩

### medicine_info 테이블

한 행 = 한 약품. `ai_worker/data/medicines.json` 필드 구조 그대로.

- `name` UNIQUE, `ingredient/usage/disclaimer` 텍스트
- `contraindicated_drugs`, `contraindicated_foods` JSONB (GIN 인덱스)
- `embedding` `vector(768)` (HNSW cosine 인덱스, L2 정규화)

## 인증 흐름

```
POST /api/v1/auth/login
  → JWT Access Token (60분) + Refresh Token (14일) 발급
  → Access Token은 Authorization 헤더, Refresh Token은 HttpOnly 쿠키

POST /api/v1/auth/token/refresh
  → Refresh Token 검증 후 새 Access Token 발급
```

## AI Worker 구조

```
ai_worker/
├── tasks/    # 처리 작업 정의
├── schemas/  # 입출력 스키마
└── core/     # 설정, 로거
```

FastAPI와 분리된 독립 프로세스로 실행되며, Redis를 통해 작업 메시지를 수신합니다.

## 배포 구성

- 로컬/개발: `docker-compose.yml` (hot-reload 활성화)
- 프로덕션: `docker-compose.prod.yml` + `scripts/deployment.sh` (EC2 자동 배포)
- HTTPS: `scripts/certbot.sh`로 Let's Encrypt 인증서 발급 및 Nginx 설정 갱신
