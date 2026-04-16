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

# 소스 파일 결정 (local/dev는 같은 파일 사용)
if [ "$ENV" = "prod" ]; then
    SOURCE_FILE="$PROJECT_ROOT/envs/.prod.env"
else
    SOURCE_FILE="$PROJECT_ROOT/envs/.local.env"
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

# 파일 복사 (심볼릭 링크 대신 복사 - ENV 값 수정 필요)
cp "$SOURCE_FILE" "$ENV_FILE"

# ENV 값 수정 (local/dev 구분)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^ENV=.*/ENV=$ENV/" "$ENV_FILE"
    sed -i '' "s/^NEXT_PUBLIC_ENV=.*/NEXT_PUBLIC_ENV=$ENV/" "$ENV_FILE"
else
    # Linux
    sed -i "s/^ENV=.*/ENV=$ENV/" "$ENV_FILE"
    sed -i "s/^NEXT_PUBLIC_ENV=.*/NEXT_PUBLIC_ENV=$ENV/" "$ENV_FILE"
fi

echo "[OK] Switched to '$ENV' environment"
if [ "$ENV" = "prod" ]; then
    echo "     Source: envs/.prod.env"
else
    echo "     Source: envs/.local.env"
fi
echo ""
echo "Current ENV: $ENV"
echo "NEXT_PUBLIC_ENV: $ENV"
