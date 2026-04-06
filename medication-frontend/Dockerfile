FROM node:22-alpine

WORKDIR /app

# 패키지 파일만 먼저 복사 (캐시 레이어 활용)
COPY package.json package-lock.json* ./

# 의존성 설치
RUN npm ci

# 소스 코드 복사 (volumes로 마운트되므로 개발 시에는 무시됨)
COPY . .

# 개발 서버 포트
EXPOSE 3000

# 개발 모드 실행
CMD ["npm", "run", "dev"]
