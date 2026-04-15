#!/bin/bash
# ============================================================
# 환경 전환 스크립트 (Linux/Mac)
# 사용법: ./scripts/switch-env.sh local|dev|prod
# ============================================================

set -e

ENV=$1
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# 사용법 체크
if [[ ! "$ENV" =~ ^(local|dev|prod)$ ]]; then
    echo "Usage: $0 <local|dev|prod>"
    echo ""
    echo "Environments:"
    echo "  local  - Local Docker with dev login button"
    echo "  dev    - Local Docker without dev login button (Kakao test)"
    echo "  prod   - Production mode (EC2 API test)"
    exit 1
fi

# 소스 파일 결정
if [ "$ENV" = "dev" ]; then
    SOURCE_FILE="$PROJECT_ROOT/envs/.local.env"
else
    SOURCE_FILE="$PROJECT_ROOT/envs/.$ENV.env"
fi

# 소스 파일 확인
if [ ! -f "$SOURCE_FILE" ]; then
    echo "[ERROR] Source file not found: $SOURCE_FILE"
    exit 1
fi

# 기존 .env 삭제
if [ -e "$ENV_FILE" ] || [ -L "$ENV_FILE" ]; then
    rm -f "$ENV_FILE"
fi

# 심볼릭 링크 생성
ln -s "$SOURCE_FILE" "$ENV_FILE"

echo "[OK] Switched to '$ENV' environment"
echo "     .env -> envs/.$ENV.env"
echo ""
echo "Current ENV: $(grep '^ENV=' "$ENV_FILE" | cut -d'=' -f2)"
