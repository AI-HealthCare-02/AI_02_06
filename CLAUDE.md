# Project Downforce: AI 기반 지능형 복약 관리 시스템

이 문서는 AI 협업 도구(Claude Code 등)가 프로젝트의 복합적인 비즈니스 로직과 기술 요구사항을 즉각 파악하기 위한 마스터 가이드북입니다.

## 1. 프로젝트 정체성 및 목적
- **서비스 명칭**: Downforce
- **핵심 가치**: 복잡한 복약 데이터를 체계적으로 관리하여 환자의 안전한 약물 복용을 돕는 전용 백엔드 시스템
- **서비스 목적성**: 
    - 처방전 데이터의 디지털 전환 및 복약 일정 자동화
    - 약물 간 상호작용(DUR 등) 분석을 통한 안전성 확보
    - 보호자가 피보호자의 건강 상태를 실시간으로 모니터링할 수 있는 환경 제공
- **기술적 지향점**: 한국어 의료 데이터 처리 및 약물 명칭 인식 성능의 극대화

## 2. 참조 문서 및 데이터 소스 (Primary Sources)
Claude Code는 프로젝트 수행 시 아래 경로의 문서를 최우선적으로 참조하여 비즈니스 로직을 설계해야 함.
- **상세 요구사항**: `csv/요구사항 정의서 2차 - 시트1.csv` (약 144개 태스크 및 상세 설명 포함)
- **API 설계 가이드**: `csv/[최종본] API 명세서 - 시트1.csv` (약 30개 엔드포인트 및 통신 규격 포함)

## 3. 개발 환경 및 설정
- **가상환경**: 루트 폴더의 `.venv`를 사용하며, 모든 Python 명령어 및 패키지 실행은 반드시 이 환경 내에서 수행함
- **환경 변수**: 보안을 위해 모든 민감 정보(비밀번호 등)는 루트의 `.env` 파일에서 관리함
    - `DATABASE_URL`: `postgresql+asyncpg://<user>:<password>@localhost:5432/downforce_db`
- **보안 규칙**: `.env` 파일은 절대 Git에 커밋하지 않으며, `migrations/env.py`를 통해 로드함
- **인프라**: AWS EC2 (Ubuntu 24.04.4 LTS) - 중앙 DB 서버 가동 완료 (Container: downforce_postgres, Status: Healthy)
- **접속 정보**: 52.78.62.12:5432 (PostgreSQL 15-alpine)

## 4. 기술 스택 (Updated)
- **Backend**: FastAPI (Async)
- **Database**: PostgreSQL 15 (asyncpg 드라이버), Tortoise ORM (Async)
  - JSONB 등 PostgreSQL 특화 기능 적극 활용
- **Validation**: Pydantic v2
- **Package Manager**: uv
- **AI/ML Worker**: 별도 마이크로서비스로 분리 (`ai_worker/`)
- **Container/Proxy**: Docker, Nginx
- **Security**: JWT (RS256 비대칭 키), Cookie 기반 토큰 관리

## 5. 데이터베이스 구조 (10개 테이블)
ERD 마스터 문서: `docs/db_schema.dbml` 참조
1. `accounts`: 로그인 계정 (소셜 OAuth)
2. `profiles`: 건강 프로필 (본인 + 피보호자, health_survey JSONB 포함)
3. `medications`: 복용 약품 정보
4. `intake_logs`: 복용 기록
5. `challenges`: 건강 챌린지
6. `chat_sessions`: AI 상담 세션
7. `messages`: 채팅 메시지
8. `refresh_tokens`: 인증 토큰 관리
9. `drug_interaction_cache`: DUR 병용금기 캐시
10. `llm_response_cache`: LLM 응답 캐시

## 6. 비즈니스 및 엔지니어링 마인드셋 (Efficiency & Cost)
- **비용 최적화**: LLM 및 OCR API 호출 시 토큰 사용량을 최소화하는 프롬프트 설계를 준수함. 불필요한 외부 API 호출을 줄이기 위해 로컬 캐싱(InteractionCache, SemanticCache)을 적극 활용함.
- **개발 효율성**: 코드 재사용성을 높이기 위해 공통 로직(Base Model, Mixins)을 활용하며, 유지보수가 용이한 모듈화된 아키텍처를 지향함.
- **구축 비용 고려**: 초기 인프라 오버헤드를 줄이기 위해 경량화된 라이브러리를 우선하며, 확장 가능한 구조로 설계하여 추후 스케일 아웃 시 발생하는 비용을 최소화함.

## 7. 개발 규칙 및 제약 사항
- **이모지 사용 절대 금지**: 모든 코드, 커밋 메시지, 문서 작성 시 이모지를 절대 사용하지 않음
- **비동기 프로그래밍**: 모든 DB 통신 및 외부 API 호출 시 `async`/`await` 패턴을 필수적으로 사용함
- **절대 경로 임포트**: `app/` 내부 모듈 참조 시 `from app.models.users import User`와 같이 루트 기준 절대 경로를 사용함
- **에러 핸들링**: 401(미인증), 403(권한 부족/PIN 미인증 포함) 등 표준 HTTP 상태 코드를 준수함
- **Aerich 운영**: 모델 수정 후 반드시 `aerich migrate`를 통해 마이그레이션 파일을 생성하고 DB를 동기화함

## 8. 시각화 및 설계 문서 (Visualization)
- **도구**: [dbdiagram.io](https://dbdiagram.io)를 사용하여 ERD를 관리함.
- **스키마 정의 파일**: `docs/db_schema.dbml` 파일을 DB 설계 마스터 문서로 활용함.
- **업데이트 규칙**: 
    - `app/models/` 내의 Tortoise ORM 모델이 수정될 때마다 `docs/db_schema.dbml` 파일의 DBML 코드를 반드시 최신 상태로 갱신해야 함.
    - 테이블 간의 관계(FK), 인덱스(Index), 제약 조건(Check/Unique)을 DBML 규격에 맞춰 정확히 반영함.

## 9. 디렉토리 구조 및 계층 (Updated)
- `app/apis/v1/`: **Presentation Layer** (HTTP 엔드포인트, 라우터)
- `app/dtos/`: **Data Transfer Objects** (Pydantic 요청/응답 스키마)
- `app/services/`: **Application Layer** (핵심 비즈니스 로직 캡슐화)
- `app/validators/`: **Domain Rules** (재사용 가능한 도메인 검증 로직)
- `app/models/`: **Domain Layer** (Tortoise ORM 엔티티)
- `app/repositories/`: **Infrastructure Layer** (DB 데이터 접근 추상화, CRUD)
- `app/dependencies/`: FastAPI 의존성 주입 (인증 등)
- `ai_worker/`: 비동기 AI 처리 전용 마이크로서비스
- `scripts/`, `nginx/`, `.github/`: CI/CD 및 배포 인프라

## 10. 버전 관리 규칙 (Git Policy)
- **커밋 주체**: 개발자가 VS Code 소스 제어를 통해 직접 커밋함.
- **AI의 역할**: 각 작업 완료 후, 개발자가 커밋을 진행할 수 있도록 아래 정보를 **추천(Recommend)** 형식으로 제공해야 함.
    - **Git Add**: 변경된 파일 목록
    - **Commit Subject**: 명확하고 간결한 한글 제목
    - **Commit Body**: 변경 사유 및 요구사항 ID(예: REQ-USR-001)를 포함한 상세 내용
- **주의**: AI가 직접 `git commit` 명령을 실행하지 않도록 주의함.

## 11. 아키텍처 설계 원칙 (Layered Architecture)
- **관심사 분리 (Separation of Concerns)**: 라우터(`apis/`)는 HTTP 요청/응답만 처리하며, 모든 비즈니스 규칙은 `services/`에 격리되어야 함.
- **데이터 추상화**: 서비스 계층은 Tortoise ORM 모델에 직접 쿼리하지 않고, 반드시 `repositories/`를 통해서만 데이터에 접근해야 함.
- **무결성 검증**: 데이터 검증은 라우터 도달 전 `dtos/`와 `validators/`에서 1차적으로 완료되어야 함.