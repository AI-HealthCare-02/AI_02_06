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

# tini 설치 (PID 1 문제 해결)
RUN apk add --no-cache tini wget

# Non-root 사용자 생성
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

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

# 디렉토리 소유권 변경
RUN chown -R nextjs:nodejs /app

# Non-root 사용자로 전환
USER nextjs

EXPOSE 3000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -q --spider http://localhost:3000 || exit 1

# tini를 entrypoint로 사용
ENTRYPOINT ["/sbin/tini", "--"]

# standalone 모드 실행
CMD ["node", ".next/standalone/server.js"]
