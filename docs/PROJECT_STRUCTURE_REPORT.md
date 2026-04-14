# Project Downforce - 프로젝트 구조 분석 보고서

작성일: 2026-04-13

## 1. 프로젝트 개요

**Downforce**는 AI 기반 복약 관리 시스템으로, 처방전 OCR 인식, 복약 일정 자동화, 약물 상호작용 분석 등의 기능을 제공합니다.

### 기술 스택
| 영역 | 기술 |
|------|------|
| Backend | FastAPI (Python 3.13+, Async) |
| Frontend | Next.js 15 (App Router, JavaScript Only) |
| Database | PostgreSQL 15 (Tortoise ORM, asyncpg) |
| AI Worker | 별도 마이크로서비스 |
| 인프라 | Docker, Nginx, AWS EC2 |
| 인증 | JWT (RS256), Cookie 기반 |

---

## 2. 루트 디렉토리 구조

```
AH_02_06/
├── app/                    # FastAPI 백엔드 메인 애플리케이션
├── ai_worker/              # AI 처리 전용 마이크로서비스
├── medication-frontend/    # Next.js 프론트엔드
├── docs/                   # 문서 (ERD, 스키마 등)
├── scripts/                # 배포 및 유틸리티 스크립트
├── nginx/                  # Nginx 설정
├── envs/                   # 환경변수 파일
├── .github/                # GitHub Actions CI/CD
├── pyproject.toml          # Python 패키지 및 도구 설정
├── docker-compose.yml      # 개발용 Docker 구성
├── docker-compose.prod.yml # 운영용 Docker 구성
├── CLAUDE.md               # AI 협업 가이드
└── .env                    # 환경변수 (심볼릭 링크)
```

---

## 3. Backend (app/)

### 3.1 계층 구조 (Layered Architecture)

```
app/
├── apis/v1/          # Presentation Layer (HTTP 엔드포인트)
├── dtos/             # Data Transfer Objects (요청/응답 스키마)
├── services/         # Application Layer (비즈니스 로직)
├── repositories/     # Infrastructure Layer (DB 접근 추상화)
├── models/           # Domain Layer (ORM 엔티티)
├── validators/       # 도메인 검증 로직
├── dependencies/     # FastAPI 의존성 주입
├── middlewares/      # 미들웨어 (CORS, Rate Limit, Security)
├── utils/            # 유틸리티 (JWT, 보안 등)
├── core/             # 설정 및 로깅
├── db/               # 데이터베이스 설정 및 마이그레이션
├── tests/            # 테스트 코드
└── main.py           # FastAPI 애플리케이션 진입점
```

### 3.2 주요 모듈별 역할

#### apis/v1/ (라우터)
| 파일 | 역할 |
|------|------|
| `oauth_routers.py` | 소셜 로그인 (Kakao, Naver) 인증 |
| `profile_routers.py` | 프로필 CRUD (본인 + 피보호자) |
| `medication_routers.py` | 복용 약품 관리 |
| `intake_log_routers.py` | 복용 기록 관리 |
| `ocr_routers.py` | 처방전 OCR 추출 및 저장 |
| `chat_session_routers.py` | AI 상담 세션 관리 |
| `message_routers.py` | 채팅 메시지 관리 |
| `challenge_routers.py` | 건강 챌린지 기능 |
| `health_routers.py` | 헬스체크 엔드포인트 |

#### dtos/ (데이터 전송 객체)
- Pydantic v2 기반 요청/응답 스키마 정의
- 입력값 검증 및 직렬화 담당
- 각 도메인별 DTO 파일 분리 (oauth.py, profile.py, medication.py 등)

#### services/ (비즈니스 로직)
| 파일 | 역할 |
|------|------|
| `oauth.py` | OAuth 토큰 검증 및 계정 생성 로직 |
| `profile_service.py` | 프로필 관련 비즈니스 규칙 |
| `medication_service.py` | 복약 관리 로직 |
| `ocr_service.py` | Clova OCR + OpenAI LLM 연동 |
| `chat_session_service.py` | AI 상담 세션 로직 |
| `intake_log_service.py` | 복용 기록 처리 |
| `challenge_service.py` | 챌린지 진행 상태 관리 |
| `rate_limiter.py` | IP 기반 요청 제한 |

#### repositories/ (데이터 접근)
- Tortoise ORM을 통한 DB CRUD 추상화
- 서비스 계층이 직접 ORM 쿼리하지 않고 Repository를 통해 접근
- 소유권 검증 메서드 포함 (`_with_owner_check`)

#### models/ (ORM 엔티티)
| 파일 | 테이블 |
|------|--------|
| `accounts.py` | accounts (로그인 계정) |
| `profiles.py` | profiles (건강 프로필) |
| `medication.py` | medications (복용 약품) |
| `intake_log.py` | intake_logs (복용 기록) |
| `challenge.py` | challenges (건강 챌린지) |
| `chat_sessions.py` | chat_sessions (AI 상담 세션) |
| `messages.py` | messages (채팅 메시지) |
| `refresh_tokens.py` | refresh_tokens (인증 토큰) |
| `drug_interaction_cache.py` | drug_interaction_cache (DUR 캐시) |
| `llm_response_cache.py` | llm_response_cache (LLM 응답 캐시) |

#### utils/jwt/ (JWT 처리)
- RS256 비대칭 키 기반 토큰 발급/검증
- Access Token + Refresh Token 이중 인증
- Refresh Token Rotation (RTR) 보안 패턴

#### middlewares/
| 파일 | 역할 |
|------|------|
| `security.py` | 입력값 검증, 보안 헤더 추가 |
| `rate_limit.py` | IP 기반 요청 제한 |

---

## 4. AI Worker (ai_worker/)

별도 마이크로서비스로 분리된 AI 처리 모듈입니다.

```
ai_worker/
├── main.py           # Worker 진입점
├── service.py        # AI 처리 서비스
├── core/             # 설정 및 로깅
│   ├── config.py
│   └── logger.py
├── utils/            # AI 유틸리티
│   ├── ocr.py        # OCR 처리
│   ├── rag.py        # RAG(검색 증강 생성) 처리
│   └── chunker.py    # 텍스트 청킹
├── schemas/          # 데이터 스키마
├── tasks/            # 비동기 태스크
├── data/             # 학습/참조 데이터
├── Dockerfile        # 개발용 Docker
└── Dockerfile.prod   # 운영용 Docker
```

---

## 5. Frontend (medication-frontend/)

### 5.1 디렉토리 구조

```
medication-frontend/
├── src/
│   ├── app/                    # Next.js App Router 페이지
│   │   ├── layout.js           # 루트 레이아웃
│   │   ├── page.js             # 메인 페이지 (/)
│   │   ├── login/page.jsx      # 로그인
│   │   ├── main/page.jsx       # 메인 대시보드
│   │   ├── medication/page.jsx # 복약 관리
│   │   ├── ocr/                # OCR 기능
│   │   │   ├── page.jsx        # 이미지 업로드
│   │   │   ├── loading/page.jsx# 처리 중 화면
│   │   │   └── result/page.jsx # 결과 확인/수정
│   │   ├── chat/page.jsx       # AI 상담
│   │   ├── challenge/page.jsx  # 챌린지
│   │   ├── mypage/page.jsx     # 마이페이지
│   │   ├── survey/page.jsx     # 건강 설문
│   │   └── auth/kakao/callback/page.jsx  # OAuth 콜백
│   ├── components/             # 재사용 컴포넌트
│   │   ├── Header.jsx
│   │   ├── BottomNav.jsx
│   │   ├── Navigation.jsx
│   │   ├── EmptyState.jsx
│   │   └── LogoutModal.jsx
│   └── lib/                    # 유틸리티
│       ├── api.js              # Axios API 클라이언트
│       ├── errors.js           # 에러 처리
│       └── tokenManager.js     # 토큰 관리
├── public/                     # 정적 파일
├── package.json
└── next.config.mjs
```

### 5.2 주요 특징
- **JavaScript Only**: TypeScript 사용 금지 (.jsx 확장자)
- **Static Export**: SSR 불가, CSR 기반
- **Tailwind CSS v4**: 스타일링

---

## 6. 데이터베이스 구조

10개 테이블로 구성되며, DBML 스키마는 `docs/db_schema.dbml`에서 관리합니다.

### 테이블 관계도
```
accounts (1) ─────┬──── (N) profiles
                  │
                  └──── (N) chat_sessions ──── (N) messages
                  │
                  └──── (N) refresh_tokens

profiles (1) ────┬──── (N) medications ──── (N) intake_logs
                 │
                 ├──── (N) challenges
                 │
                 └──── (N) chat_sessions

[캐시 테이블 - 독립]
drug_interaction_cache
llm_response_cache
```

### PK 전략
- **비즈니스 엔티티**: UUID (보안, 외부 노출 시 예측 불가)
- **내부/캐시 테이블**: BigInt (성능 최적화)

### Soft Delete
- 비즈니스 엔티티: `deleted_at` 필드 적용
- 캐시/로그: 미적용 (TTL 기반 정리)

---

## 7. 인프라 및 배포

### scripts/
| 파일 | 역할 |
|------|------|
| `certbot.sh` | SSL 인증서 발급/갱신 |
| `deployment.sh` | 배포 자동화 스크립트 |
| `create_fake_user.py` | 테스트용 가짜 사용자 생성 |

### Docker 구성
- `docker-compose.yml`: 로컬 개발 환경
- `docker-compose.prod.yml`: 운영 환경 (Nginx, SSL 포함)

### 환경변수
- `envs/.local.env`: 로컬 개발용
- `.env`: 심볼릭 링크로 연결

---

## 8. 개발 도구 및 품질 관리

### pyproject.toml 설정
- **Ruff**: Python 린터/포매터
- **Mypy**: 정적 타입 검사
- **Bandit**: 보안 취약점 검사
- **Pytest**: 테스트 프레임워크
- **Aerich**: Tortoise ORM 마이그레이션

### Pre-commit Hooks
`.pre-commit-config.yaml`을 통해 커밋 전 자동 검사

---

## 9. 요약

| 구성요소 | 설명 |
|----------|------|
| `app/` | FastAPI 백엔드 (Layered Architecture) |
| `ai_worker/` | AI 처리 마이크로서비스 |
| `medication-frontend/` | Next.js 프론트엔드 (JS Only) |
| `docs/` | 스키마, ERD 문서 |
| `scripts/` | 배포/유틸리티 스크립트 |
| `nginx/` | 웹서버 설정 |

이 프로젝트는 **관심사 분리**와 **계층화된 아키텍처**를 통해 유지보수성과 확장성을 확보하고 있으며, **비용 최적화**를 위해 LLM/OCR 응답 캐싱을 적극 활용합니다.
