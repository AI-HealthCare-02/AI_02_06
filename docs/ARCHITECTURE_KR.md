# AI Healthcare System Architecture

## 전체 시스템 구성도

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                AI Healthcare System                                 │
└─────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────────────────┐
│   사용자 브라우저   │────│  Vercel (CDN)   │────│        ai-02-06.duckdns.org        │
│                 │    │   Next.js 15    │    │         + Let's Encrypt SSL         │
└─────────────────┘    │   React 19      │    └─────────────────────────────────────┘
                       │   TypeScript    │                        │
                       └─────────────────┘                        │
                                                                  │
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            AWS EC2 (t3.medium)                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                          Docker Network                                    │   │
│  │                                                                             │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │   │
│  │  │    Nginx    │────│   FastAPI   │────│ PostgreSQL  │                    │   │
│  │  │ :80, :443   │    │    :8000    │    │    :5432    │                    │   │
│  │  │ Reverse     │    │ Python 3.13 │    │ Primary DB  │                    │   │
│  │  │ Proxy       │    │ Uvicorn     │    │ Tortoise    │                    │   │
│  │  │ HTTPS       │    │ ASGI        │    │ ORM         │                    │   │
│  │  └─────────────┘    └─────────────┘    └─────────────┘                    │   │
│  │                              │                                             │   │
│  │                              │         ┌─────────────┐                    │   │
│  │                              └─────────│    Redis    │                    │   │
│  │                                        │    :6379    │                    │   │
│  │                                        │ Message     │                    │   │
│  │                                        │ Broker      │                    │   │
│  │                                        │ Cache       │                    │   │
│  │                                        └─────────────┘                    │   │
│  │                                                │                           │   │
│  │                                        ┌─────────────┐                    │   │
│  │                                        │ AI Worker   │                    │   │
│  │                                        │ OCR + RAG   │                    │   │
│  │                                        │ Pipeline    │                    │   │
│  │                                        │ Background  │                    │   │
│  │                                        │ Jobs        │                    │   │
│  │                                        └─────────────┘                    │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
          ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
          │ NAVER CLOVA OCR │  │  OpenAI GPT-4o  │  │ Kakao OAuth 2.0 │
          │ 처방전 텍스트 추출  │  │ 복약 가이드 생성   │  │   소셜 로그인     │
          └─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## 배포 환경 구성

### Frontend (Vercel)
- **플랫폼**: Vercel (Next.js 최적화)
- **프레임워크**: Next.js 15 + React 19 + TypeScript
- **배포**: Git push 시 자동 배포
- **도메인**: Vercel 제공 도메인 + 커스텀 도메인 연결

### Backend (AWS EC2)
- **인스턴스**: t3.medium (2 vCPU, 4GB RAM, 30GB EBS)
- **OS**: Ubuntu 22.04 LTS
- **도메인**: `ai-02-06.duckdns.org` (DuckDNS 무료 도메인)
- **SSL**: Let's Encrypt 자동 갱신
- **배포**: GitHub Actions CI/CD

---

## Docker 컨테이너 구성

### Production Stack (`docker-compose.prod.yml`)

| 서비스 | 이미지 | 포트 | 역할 | 리소스 제한 |
|--------|--------|------|------|-------------|
| **nginx** | nginx:alpine | 80, 443 | 리버스 프록시, HTTPS 종료 | 64MB |
| **fastapi** | custom | 8000 | REST API 서버 | 300MB |
| **ai-worker** | custom | - | AI 추론 백그라운드 작업 | 300MB |
| **postgres** | postgres:15-alpine | 5432 | 주 데이터베이스 | 256MB |
| **redis** | redis:alpine | 6379 | 메시지 브로커, 캐시 | 128MB |

### 네트워크 구성
- **frontend**: nginx ↔ fastapi, ai-worker (외부 API 접근)
- **backend**: fastapi ↔ postgres, redis ↔ ai-worker (내부 통신)

---

## FastAPI 백엔드 아키텍처

### 디렉토리 구조
```
app/
├── apis/v1/              # API 라우터 (RESTful 엔드포인트)
│   ├── health_routers.py     # 헬스체크
│   ├── oauth_routers.py      # 카카오 OAuth 인증
│   ├── profile_routers.py    # 사용자 프로필 관리
│   ├── medication_routers.py # 복용약 관리
│   ├── intake_log_routers.py # 복용 기록
│   ├── ocr_routers.py        # 처방전 OCR
│   ├── chat_session_routers.py # 채팅 세션
│   ├── message_routers.py    # 메시지 관리
│   └── challenge_routers.py  # 복약 챌린지
├── core/                 # 핵심 설정
│   ├── config.py            # Pydantic Settings
│   └── logger.py            # 구조화된 로깅
├── middlewares/          # 미들웨어
│   ├── security.py          # 보안 (XSS, Path Traversal 방어)
│   └── rate_limit.py        # IP 기반 요청 제한
├── models/               # Tortoise ORM 모델
├── dtos/                 # Pydantic 스키마 (요청/응답)
├── services/             # 비즈니스 로직
├── repositories/         # 데이터 접근 계층
├── dependencies/         # FastAPI 의존성 주입
├── utils/                # 유틸리티 (JWT, 보안)
├── validators/           # 입력값 검증
└── db/                   # DB 초기화, 마이그레이션
    └── migrations/          # Aerich 마이그레이션 파일
```

### 요청 처리 흐름
```
Client Request
    ↓
Nginx (HTTPS, Rate Limiting)
    ↓
FastAPI Middlewares
    ├── SecurityMiddleware (공격 패턴 탐지)
    ├── RateLimitMiddleware (IP별 요청 제한)
    └── CORSMiddleware (CORS 정책)
    ↓
API Router (v1)
    ↓
Service Layer (비즈니스 로직)
    ↓
Repository Layer (DB 추상화)
    ↓
Tortoise ORM
    ↓
PostgreSQL Database
```

---

## AI Worker 아키텍처

### 구조
```
ai_worker/
├── core/                 # 설정 및 로깅
├── tasks/                # 백그라운드 작업 정의
│   ├── ocr_tasks.py         # OCR 처리 작업
│   └── embedding_tasks.py   # 임베딩 생성 작업
├── utils/                # AI 유틸리티
│   ├── ocr.py              # CLOVA OCR 호출
│   ├── chunker.py          # 데이터 청킹
│   └── rag.py              # RAG 파이프라인
├── data/                 # 정적 데이터
│   └── medicines.json      # 약품 정보 DB
└── main.py               # Worker 진입점
```

### RAG 파이프라인
```
RAG 파이프라인 처리 흐름:

User        FastAPI      Redis       AI Worker    CLOVA OCR    OpenAI GPT-4o
 │             │           │             │             │             │
 │─────────────│──────────▶│             │             │             │
 │ 처방전 이미지  │           │             │             │             │
 │ 업로드       │           │             │             │             │
 │             │───────────│────────────▶│             │             │
 │             │ OCR 작업   │             │             │             │
 │             │ 큐에 추가   │             │             │             │
 │             │           │─────────────│────────────▶│             │
 │             │           │ 작업 수신    │             │             │
 │             │           │             │─────────────│────────────▶│
 │             │           │             │ 이미지 →     │             │
 │             │           │             │ 텍스트 변환   │             │
 │             │           │             │◀────────────│─────────────│
 │             │           │             │ 추출된 약품명  │             │
 │             │           │             │─────────────│────────────▶│
 │             │           │             │ medicines.   │             │
 │             │           │             │ json 매칭    │             │
 │             │           │             │─────────────│────────────▶│
 │             │           │             │ 텍스트 청킹   │             │
 │             │           │             │─────────────│────────────▶│
 │             │           │             │ 복약 가이드   │             │
 │             │           │             │ 생성 요청     │             │
 │             │           │             │◀────────────│─────────────│
 │             │           │             │ 개인화된      │             │
 │             │           │             │ 복약 가이드   │             │
 │◀────────────│───────────│◀────────────│─────────────│─────────────│
 │ 복약 가이드   │           │ 결과 반환    │             │             │
 │ 응답         │           │             │             │             │
```

---

## 보안 아키텍처

### 인증 & 인가
```
카카오 OAuth 2.0 인증 흐름:

Client          FastAPI         Kakao OAuth      PostgreSQL
 │                 │                 │               │
 │─────────────────│────────────────▶│               │
 │ 카카오 로그인     │                 │               │
 │ 요청            │                 │               │
 │                 │─────────────────│──────────────▶│
 │                 │ OAuth 인증 코드   │               │
 │                 │ 교환            │               │
 │                 │◀────────────────│───────────────│
 │                 │ 사용자 정보 반환   │               │
 │                 │─────────────────│──────────────▶│
 │                 │ 사용자 정보       │ 저장/업데이트   │
 │                 │ 저장/업데이트     │               │
 │◀────────────────│─────────────────│───────────────│
 │ JWT Access      │                 │               │
 │ Token (60분) +   │                 │               │
 │ Refresh Token   │                 │               │
 │ (14일)          │                 │               │
 │                 │                 │               │
 │ ─ ─ ─ ─ ─ ─ ─ ─ 이후 API 요청 ─ ─ ─ ─ ─ ─ ─ ─ │
 │                 │                 │               │
 │─────────────────│────────────────▶│               │
 │ Authorization:  │                 │               │
 │ Bearer <token>  │                 │               │
 │                 │─────────────────│──────────────▶│
 │                 │ JWT 검증 및      │               │
 │                 │ 사용자 식별       │               │
 │◀────────────────│─────────────────│───────────────│
 │ API 응답        │                 │               │
```

### 보안 계층
1. **Nginx**: HTTPS 강제, 요청 크기 제한 (10MB)
2. **SecurityMiddleware**:
   - Path Traversal 공격 차단
   - XSS 패턴 탐지 및 로깅
   - 보안 헤더 추가
3. **RateLimitMiddleware**:
   - GET: 200 req/60s per IP
   - POST/PATCH/DELETE: 30 req/60s per IP
   - Auth endpoints: 10 req/60s per IP
4. **JWT**: 짧은 수명 Access Token + HttpOnly Refresh Token

---

## CI/CD 파이프라인

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
1. Test Phase:
   - Python 3.13 + PostgreSQL 15 환경
   - uv로 의존성 설치
   - pytest 테스트 실행

2. Deploy Phase:
   - EC2 SSH 접속
   - Git pull (latest main)
   - Docker Compose 재빌드
   - 자동 마이그레이션 실행
   - 헬스체크 확인

3. Health Check Phase:
   - API 엔드포인트 상태 확인
   - Nginx 프록시 상태 확인
```

### 배포 자동화 스크립트
- `scripts/deployment.sh`: Docker 이미지 빌드 & 푸시 & EC2 배포
- `scripts/certbot.sh`: Let's Encrypt SSL 인증서 자동 갱신

---

## 개발 환경 설정

### 로컬 개발
```bash
# 의존성 설치
uv sync

# 로컬 스택 실행
docker-compose up -d

# 개발 서버 실행
uv run uvicorn app.main:app --reload
```

### 환경 변수 관리
- `envs/.local.env`: 로컬 개발용
- `envs/.prod.env`: 프로덕션용 (EC2)
- GitHub Secrets: 민감한 정보 (API 키, DB 비밀번호)

---

## 모니터링 & 로깅

### 로깅 전략
- **구조화된 로깅**: JSON 형태로 출력
- **레벨별 분류**: DEBUG → INFO → WARNING → ERROR → CRITICAL
- **보안 고려**: 개인정보 마스킹, 토큰 제외
- **Docker 로그**: 크기 제한 (50MB, 5개 파일)

### 헬스체크
- **API**: `/api/v1/health` (DB 연결 상태 포함)
- **Nginx**: `/health` (프록시 상태)
- **Docker**: 각 컨테이너별 헬스체크 설정

---

## 확장성 고려사항

### 현재 제약사항 (t3.medium)
- **CPU**: 2 vCPU (버스트 가능)
- **메모리**: 4GB (컨테이너별 제한 설정)
- **스토리지**: 30GB EBS

### 확장 방안
1. **수직 확장**: 더 큰 EC2 인스턴스 타입
2. **수평 확장**:
   - Application Load Balancer + 다중 EC2
   - RDS PostgreSQL (관리형 DB)
   - ElastiCache Redis (관리형 캐시)
3. **마이크로서비스**: AI Worker를 별도 서비스로 분리

---

## 기술 스택 요약

| 계층 | 기술 | 버전 | 역할 |
|------|------|------|------|
| **Frontend** | Next.js | 15 | React 기반 SPA |
| **Backend** | FastAPI | 0.128+ | Python 비동기 API 서버 |
| **Database** | PostgreSQL | 15 | 관계형 데이터베이스 |
| **Cache/Queue** | Redis | Alpine | 메시지 브로커, 캐시 |
| **ORM** | Tortoise ORM | 0.25+ | 비동기 Python ORM |
| **Web Server** | Nginx | Alpine | 리버스 프록시, HTTPS |
| **Container** | Docker | - | 컨테이너화 |
| **Orchestration** | Docker Compose | - | 멀티 컨테이너 관리 |
| **CI/CD** | GitHub Actions | - | 자동 배포 |
| **Monitoring** | Docker Logs | - | 로그 수집 |
| **SSL** | Let's Encrypt | - | 무료 SSL 인증서 |
| **DNS** | DuckDNS | - | 무료 동적 DNS |

---

## 추가 문서

- [README.md](../README.md): 프로젝트 개요 및 실행 방법
- [SYSTEM_DESIGN.md](SYSTEM_DESIGN_KR.md): 기술적 설계 세부사항
- [docs/01_DB_MIGRATION_GUIDE.md](01_DB_MIGRATION_GUIDE.md): DB 마이그레이션 가이드
- [docs/02_ENV_AND_CICD_GUIDE.md](02_ENV_AND_CICD_GUIDE.md): 환경 설정 및 CI/CD
- [docs/OCR_FLOW.md](OCR_FLOW.md): OCR 처리 흐름
- [PLAN.md](../PLAN.md): 개발 계획 및 아키텍처 설계
