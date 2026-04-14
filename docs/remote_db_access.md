# Project Downforce - 클라우드 DB 접속 가이드

## 개요

이 문서는 팀원들이 각자의 로컬 개발 환경에서 AWS EC2에 구축된 중앙 PostgreSQL 서버에 접속하는 방법을 설명합니다.

---

## 1. 서버 정보

| 항목 | 값 |
|------|-----|
| 호스트 | 52.78.62.12 |
| 포트 | 5432 |
| 데이터베이스 | downforce_db |
| 사용자 | downforce_admin |
| 비밀번호 | (팀 내부 공유 - 절대 외부 유출 금지) |

---

## 2. 로컬 환경 설정

### 2.1 환경 변수 파일 설정

프로젝트 루트에 `.env` 파일을 생성하고 아래 내용을 입력합니다:

```bash
# 클라우드 DB 연결 (운영 환경)
DATABASE_URL=postgresql+asyncpg://downforce_admin:<비밀번호>@52.78.62.12:5432/downforce_db

# 로컬 DB 연결 (개인 테스트용, 선택 사항)
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/downforce_db
```

**주의**: `.env` 파일은 `.gitignore`에 포함되어 있으므로 Git에 커밋되지 않습니다.

---

## 3. 클라이언트별 접속 방법

### 3.1 FastAPI 애플리케이션

`app/db/database.py`에서 환경 변수를 자동으로 로드합니다. 별도 설정 없이 서버 실행 시 클라우드 DB에 연결됩니다.

```bash
# 가상환경 활성화 후 서버 실행
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

uvicorn app.main:app --reload
```

### 3.2 DBeaver

1. 새 연결 생성: `Database > New Database Connection`
2. PostgreSQL 선택
3. 연결 정보 입력:
   - Host: `52.78.62.12`
   - Port: `5432`
   - Database: `downforce_db`
   - Username: `downforce_admin`
   - Password: (팀 내부 공유 비밀번호)
4. `Test Connection` 클릭하여 연결 확인
5. `Finish` 클릭

### 3.3 pgAdmin 4

1. `Servers` 우클릭 > `Register > Server`
2. General 탭:
   - Name: `Downforce Cloud DB`
3. Connection 탭:
   - Host: `52.78.62.12`
   - Port: `5432`
   - Maintenance database: `downforce_db`
   - Username: `downforce_admin`
   - Password: (팀 내부 공유 비밀번호)
   - Save password 체크 (선택)
4. `Save` 클릭

### 3.4 터미널 (psql)

```bash
psql -h 52.78.62.12 -p 5432 -U downforce_admin -d downforce_db
```

---

## 4. 연결 문제 해결

### 4.1 연결 거부 (Connection refused)

**원인**: AWS Security Group에서 5432 포트가 차단됨

**해결**:
1. AWS Console > EC2 > Security Groups
2. 해당 인스턴스의 보안 그룹 선택
3. Inbound rules에 다음 규칙 추가:
   - Type: PostgreSQL
   - Port: 5432
   - Source: 본인 IP 또는 팀원 IP 대역

### 4.2 인증 실패 (Authentication failed)

**원인**: 비밀번호 오류 또는 사용자명 오타

**해결**:
1. `.env` 파일의 DATABASE_URL 확인
2. 비밀번호에 특수문자가 있는 경우 URL 인코딩 적용
   - `@` -> `%40`
   - `#` -> `%23`
   - `:` -> `%3A`

### 4.3 타임아웃 (Connection timed out)

**원인**: 네트워크 문제 또는 서버 미가동

**해결**:
1. 서버 상태 확인: `docker ps` (EC2 접속 후)
2. 컨테이너 미실행 시: `docker compose up -d`

---

## 5. 보안 주의사항

1. **비밀번호 외부 유출 금지**: Slack, 이메일 등 외부 채널로 비밀번호 공유 금지
2. **IP 제한 권장**: 팀원 IP만 접근 가능하도록 Security Group 설정
3. **SSH 터널링**: 보안 강화 시 SSH 터널을 통한 접속 권장

```bash
# SSH 터널 생성 (로컬 5433 -> 원격 5432)
ssh -L 5433:localhost:5432 ubuntu@52.78.62.12 -i downforce-key.pem

# 이후 localhost:5433으로 접속
DATABASE_URL=postgresql+asyncpg://downforce_admin:<비밀번호>@localhost:5433/downforce_db
```

---

## 6. Alembic 마이그레이션

클라우드 DB에 스키마 변경 적용:

```bash
# 가상환경 활성화 상태에서
alembic upgrade head
```

**주의**: 마이그레이션 실행 전 팀원에게 공지하여 충돌 방지
