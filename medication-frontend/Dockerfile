# =========================================
# Development Stage
# =========================================
FROM node:22-alpine AS dev

# PID 1 문제 해결 및 시그널 처리 -> 시그널 처리 및 프로세스 종료 시 컨테이너 정상 종료
RUN apk add --no-cache tini

WORKDIR /app

# 패키지 파일만 먼저 복사 (캐시 레이어 활용)
COPY package.json package-lock.json* ./

# 전체 의존성 설치 (devDependencies 포함)
RUN npm ci

# 소스 코드는 volume mount로 대체
EXPOSE 3000

ENTRYPOINT ["/sbin/tini", "--"]
CMD ["npm", "run", "dev"]

# =========================================
# Production Stage
# =========================================
FROM node:22-alpine AS prod

WORKDIR /app

# 패키지 파일 복사
COPY package.json package-lock.json* ./

# 프로덕션 의존성만 설치
RUN npm ci --omit=dev

# 소스 코드 복사 및 빌드
COPY . .
RUN npm run build

# standalone 모드용 정적 파일 복사
COPY public ./.next/standalone/public
COPY .next/static ./.next/standalone/.next/static

EXPOSE 3000

# standalone 모드 실행
CMD ["node", ".next/standalone/server.js"]
