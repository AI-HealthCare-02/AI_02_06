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
                        │                             MySQL            │
                        └─────────────────────────────────────────────┘
```

## 서비스 레이어

| 서비스 | 역할 | 기술 |
|---|---|---|
| Nginx | 리버스 프록시, `/api/*` 요청 라우팅 | nginx:latest |
| FastAPI | REST API 서버, 인증/비즈니스 로직 처리 | FastAPI + Uvicorn |
| AI Worker | 모델 추론/학습 비동기 처리 | Python Worker |
| MySQL | 영구 데이터 저장 | MySQL 8.0 |
| Redis | 메시지 브로커 / 캐싱 | Redis Alpine |

## FastAPI 내부 구조

```
app/
├── apis/v1/          # 라우터 (auth, user)
├── services/         # 비즈니스 로직
├── repositories/     # DB 접근 계층
├── models/           # Tortoise ORM 테이블 정의
├── dtos/             # 요청/응답 Pydantic 스키마
├── dependencies/     # FastAPI 의존성 (JWT 인증)
├── utils/jwt/        # JWT 토큰 발급·검증
├── validators/       # 입력값 검증
├── core/             # 설정(pydantic-settings), 로거
└── db/               # DB 초기화, Aerich 마이그레이션
```

요청 흐름: `Router → Service → Repository → DB`

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
