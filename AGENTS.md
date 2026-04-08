# Project Downforce - AI Assistant Guide (Root)

> AI 기반 지능형 복약 관리 시스템

## Project Overview

이 프로젝트는 Docker Compose 기반 마이크로서비스 아키텍처로 구성됩니다.

```
/
├── app/                    # FastAPI Backend (Port 8000)
├── medication-frontend/    # Next.js Frontend (Port 3000)
├── ai_worker/              # AI Processing Worker
├── nginx/                  # Reverse Proxy Config
├── docs/                   # Documentation
└── docker-compose.yml      # Service Orchestration
```

## Architecture Principles

### Service Communication
```
Client -> Nginx:80 -> Frontend:3000 (UI)
                   -> FastAPI:8000 (API)
FastAPI <-> Redis:6379 <-> AI Worker (Async Tasks)
FastAPI <-> PostgreSQL:5432 (Data)
```

### Technology Stack
- **Frontend**: Next.js 16, React 19, Tailwind CSS v4
- **Backend**: FastAPI, Tortoise ORM, PostgreSQL 15
- **AI Worker**: Python, RQ (Redis Queue), CPU-only PyTorch
- **Infra**: Docker, Nginx, Redis, Let's Encrypt

## Security Architecture (RS256 + Zero Trust)

### 핵심 보안 방향성

1. **RS256 비대칭 키 인증**
   - FastAPI: Private Key로 JWT 서명 및 발행
   - Next.js: Public Key로 서명 검증만 수행
   - 키 유출 시에도 토큰 위조 불가능

2. **이중 방어 체계**
   - Next.js: 세션 인증 Gatekeeper (UI 자산 보호)
   - FastAPI: 재인증 + 최종 인가 (데이터 무결성)

3. **Algorithm Pinning**
   - `algorithms=['RS256']` 명시
   - HS256 교체 공격 (Algorithm Confusion Attack) 차단

4. **Cookie 기반 JWT**
   - localStorage 대신 HttpOnly Cookie 사용
   - XSS 공격으로부터 토큰 보호

### 서비스별 보안 책임

| 서비스 | 역할 | 검증 수준 |
|--------|------|-----------|
| Next.js | UI Gatekeeper | 서명 유효성 (Authentication) |
| FastAPI | Data Guardian | 재인증 + 소유권 (Authorization) |

## Docker Deployment

### 컨테이너 구성
- **Next.js**: 독립 Node.js 컨테이너 (Static Export 아님)
  - middleware.ts를 통한 서버단 보안 제어
- **FastAPI**: Uvicorn ASGI 서버
- **AI Worker**: CPU-only 환경 (CUDA 의존성 제거)
- **Nginx**: Reverse Proxy + SSL Termination

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

## Coding Conventions

### Language
- 코드: 영어
- 주석: 한국어 허용
- 커밋 메시지: 한글 (예: `feat: 복약 알림 기능 추가`)

### File Naming
- Python: `snake_case.py`
- TypeScript/JavaScript: `camelCase.ts` 또는 `PascalCase.tsx` (컴포넌트)
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
