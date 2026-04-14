# 환경 변수 가이드

## 파일 구조

```
envs/
├── .local.env          # 로컬용 실제 값 (gitignore)
├── .prod.env           # prod용 실제 값 (gitignore)
├── example.local.env   # 로컬 템플릿 (git 추적)
└── example.prod.env    # prod 템플릿 (git 추적)
```

---

## 환경 비교

| 항목 | local | dev | prod |
|------|-------|-----|------|
| Backend | 로컬 Docker | 로컬 Docker | EC2 Docker |
| Frontend | localhost:3000 | localhost:3000 | Vercel |
| DB | 로컬 Docker | 로컬 Docker | EC2 Docker |
| Dev 로그인 버튼 | O | X | X |
| Docker Compose | docker-compose.yml | docker-compose.yml | docker-compose.prod.yml |

---

## 로컬 개발 시작

```bash
# 1. 환경변수 복사
cp envs/.local.env .env

# 2. Docker 실행
docker compose up -d

# 3. 프론트엔드 실행
cd medication-frontend && npm run dev

# 4. 접속
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# DB:       localhost:5432
```

---

## local ↔ dev 전환

`.env` 파일에서 두 줄만 변경:

```bash
# local → dev (카카오 로그인 테스트)
ENV=dev
NEXT_PUBLIC_ENV=dev

# dev → local (빠른 개발, dev 버튼 사용)
ENV=local
NEXT_PUBLIC_ENV=local
```

---

## EC2 배포

### 최초 설정

```bash
# EC2 접속
ssh ubuntu@52.78.62.12

# 프로젝트 클론
git clone https://github.com/AI-HealthCare-02/AH_02_06.git
cd AH_02_06

# 환경변수 설정
cp envs/example.prod.env envs/.prod.env
vi envs/.prod.env  # 실제 값 입력

# .env로 복사
cp envs/.prod.env .env

# Docker 실행 (prod용)
docker compose -f docker-compose.prod.yml up -d
```

### 이후 배포

```bash
ssh ubuntu@52.78.62.12
cd AH_02_06
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Vercel 배포

Vercel Dashboard에서 환경변수 설정:

```
Settings > Environment Variables

NEXT_PUBLIC_ENV = prod
API_BASE_URL = http://52.78.62.12
```

---

## CI/CD 파이프라인

### GitHub Secrets 설정

```
Repository > Settings > Secrets and variables > Actions

필수:
- SECRET_KEY
- DB_PASSWORD
- KAKAO_CLIENT_ID
- KAKAO_CLIENT_SECRET

선택 (AI Worker):
- CLOVA_OCR_SECRET_KEY
- CLOVA_OCR_INVOKE_URL
- OPENAI_API_KEY
```

### EC2에 필요한 파일

```
EC2:/home/ubuntu/AH_02_06/
├── .env                      # envs/.prod.env 복사본
├── docker-compose.prod.yml   # prod용 Docker Compose
└── (나머지 소스코드)
```

---

## Docker Compose 비교

| 항목 | docker-compose.yml | docker-compose.prod.yml |
|------|-------------------|------------------------|
| 용도 | 로컬 개발 | EC2 배포 |
| 리소스 | 넉넉함 | t3.micro 최적화 |
| 포트 노출 | 5432, 6379, 8000, 80 | 80만 |
| Nginx 설정 | default.conf | prod_http.conf |
| 재시작 정책 | 없음 | unless-stopped |

---

## 문제 해결

### Docker 컨테이너 상태 확인
```bash
docker compose ps
docker compose logs fastapi --tail=50
```

### DB 연결 테스트
```bash
docker exec -it postgres psql -U downforce_admin -d downforce_db
```

### 환경변수 확인
```bash
docker exec fastapi env | grep ENV
```
