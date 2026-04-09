# Project Downforce - AI Assistant Guide (Root)

> AI 기반 지능형 복약 관리 시스템

## Project Overview

이 프로젝트는 Docker Compose 기반 마이크로서비스 아키텍처로 구성됩니다.

```
/
├── app/                    # FastAPI Backend (Port 8000)
├── medication-frontend/    # Next.js Frontend (Static Export)
├── ai_worker/              # AI Processing Worker
├── nginx/                  # Reverse Proxy + Static File Server
├── docs/                   # Documentation
└── docker-compose.yml      # Service Orchestration
```

## Architecture Principles

### Service Communication
```
Client -> Nginx:80 -> Static Files (UI)
                   -> FastAPI:8000 (API)
FastAPI <-> Redis:6379 <-> AI Worker (Async Tasks)
FastAPI <-> PostgreSQL:5432 (Data)
```

### Technology Stack
- **Frontend**: Next.js 16 (Static Export), React 19, Tailwind CSS v4 (**JavaScript Only**)
- **Backend**: FastAPI, Tortoise ORM, PostgreSQL 15
- **AI Worker**: Python, RQ (Redis Queue), CPU-only PyTorch
- **Infra**: Docker, Nginx, Redis, Let's Encrypt

## Environment Configuration (local / dev / prod)

### 환경별 동작 차이

| 환경 | `ENV` | OAuth | Dev 로그인 | 용도 |
|------|-------|-------|-----------|------|
| **local** | `local` | Mock 서버 | 표시 | 로컬 개발 (Docker 없이) |
| **dev** | `dev` | 실제 Kakao | 표시 | Docker 개발 환경 |
| **prod** | `prod` | 실제 Kakao | 숨김 | 프로덕션 배포 |

### 핵심 환경변수

```bash
# 공통
ENV=local|dev|prod           # 환경 구분

# Backend (FastAPI)
API_BASE_URL=http://fastapi:8000   # Docker 내부 통신용
FRONTEND_URL=http://localhost:3000      # 브라우저 리다이렉트용

# Frontend (Next.js)
NEXT_PUBLIC_ENV=local|dev|prod     # 클라이언트 환경 구분
NEXT_PUBLIC_API_BASE_URL=          # 비워두면 Nginx 프록시 사용 (프로덕션)
                                   # http://localhost:8000 (로컬 개발)
```

### OAuth 흐름 분기

```python
# FastAPI: oauth_routers.py
if config.ENV == Env.LOCAL:
    # Mock 서버로 리다이렉트 (카카오 앱 없이 테스트)
    authorize_url = f"{config.FRONTEND_URL}/api/v1/mock/kakao/authorize"
else:
    # 실제 카카오 OAuth
    authorize_url = "https://kauth.kakao.com/oauth/authorize"
```

### Dev 로그인 버튼 (Frontend)

```javascript
// login/page.jsx
const IS_DEV_MODE = process.env.NEXT_PUBLIC_ENV !== 'prod'
// prod 환경에서만 Dev 로그인 버튼 숨김
```

## Security Architecture (RS256)

### 인증 방식

1. **RS256 비대칭 키 인증**
   - FastAPI: Private Key로 JWT 서명 및 발행
   - 클라이언트: 토큰을 HttpOnly Cookie로 저장

2. **Algorithm Pinning**
   - `algorithms=['RS256']` 명시
   - HS256 교체 공격 (Algorithm Confusion Attack) 차단

3. **Cookie 기반 JWT**
   - localStorage 대신 HttpOnly Cookie 사용
   - XSS 공격으로부터 토큰 보호

### 보안 검증 흐름

```
Client Request
    -> Nginx (Static Files / API Proxy)
    -> FastAPI (토큰 검증 + 소유권 확인)
    -> Response
```

FastAPI가 모든 인증/인가를 담당합니다:
- **토큰 검증**: RS256 서명 확인, 만료 시간 확인
- **소유권 확인**: 요청 리소스에 대한 접근 권한 검증

## Docker Deployment

### 컨테이너 구성 (3개)
- **Nginx**: Static File Server + Reverse Proxy
- **FastAPI**: Uvicorn ASGI 서버
- **AI Worker**: CPU-only 환경 (CUDA 의존성 제거)

### Frontend 배포 (Static Export)
```bash
# 1. 빌드 (로컬에서 실행)
cd medication-frontend
npm run build
# -> out/ 폴더에 정적 파일 생성

# 2. Docker 실행 (Nginx가 out/ 폴더 서빙)
docker compose up nginx fastapi
```

### AI Worker 최적화
```toml
# pyproject.toml - CPU 전용 PyTorch
[[tool.uv.index]]
name = "pytorch-cpu"
url = "https://download.pytorch.org/whl/cpu"
explicit = true

[tool.uv.sources]
torch = { index = "pytorch-cpu" }
torchvision = { index = "pytorch-cpu" }
```

## Development Workflow

### 로컬 개발 (권장)
```bash
# 1. 루트 .env 설정 (환경변수 통합 관리)
cp .env.example .env
# 필수 값 입력: SECRET_KEY, DB_PASSWORD, KAKAO_CLIENT_ID 등

# 2. 백엔드 서비스 실행
docker compose up fastapi redis

# 3. 프론트엔드 개발 서버 실행 (별도 터미널)
cd medication-frontend
npm run dev
# -> http://localhost:3000 (루트 .env 자동 로드)
```

### Docker 통합 테스트
```bash
# 1. 프론트엔드 빌드
cd medication-frontend && npm run build

# 2. 전체 스택 실행
docker compose up
# -> http://localhost (Nginx)
```

## Coding Conventions

### Language
- 코드: 영어
- 주석: 한국어 허용
- 커밋 메시지: 한글 (예: `feat: 복약 알림 기능 추가`)

### File Naming
- Python: `snake_case.py`
- Frontend: `camelCase.js` 또는 `PascalCase.jsx` (컴포넌트) - **JavaScript Only**
- Config: `kebab-case.yml`

### Import Order
1. Standard library
2. Third-party packages
3. Local imports (absolute path)

### FastAPI 의존성 주입 (Annotated 패턴)
```python
# Ruff UP 규칙 준수 - Depends() 직접 사용 금지
from typing import Annotated
from fastapi import Depends

CurrentAccount = Annotated[Account, Depends(get_current_account)]

@router.get("/")
async def get_items(account: CurrentAccount):
    ...
```

## Do NOTs

- 이모지 사용 금지 (코드, 커밋 메시지, 문서 모두)
- `.env` 파일 수정 또는 커밋 금지
- `docker-compose.prod.yml`에 포트 노출 금지 (Nginx 제외)
- `git push --force` 금지
- 하드코딩된 시크릿 금지
- `= Depends()` 직접 사용 금지 -> `Annotated[T, Depends()]` 사용
- Frontend에 `.ts`, `.tsx` 파일 생성 금지 (JavaScript Only)

## Key Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | 개발 환경 서비스 정의 |
| `docker-compose.prod.yml` | 프로덕션 환경 정의 |
| `pyproject.toml` | Python 의존성 관리 (uv) |
| `.env.example` | 환경변수 템플릿 |

## Reference Documents

- `docs/project_structure_analysis.md` - 전체 구조 분석
- `docs/improvement_roadmap.md` - 개선 로드맵
- `docs/db_schema.dbml` - ERD 스키마
- `csv/요구사항 정의서 2차 - 시트1.csv` - 요구사항
- `csv/[최종본] API 명세서 - 시트1.csv` - API 명세
