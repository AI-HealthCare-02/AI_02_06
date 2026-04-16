#!/bin/bash
# Modern Python Type Checking Script (2025-2026)
# Uses MyPy with strict type checking standards

set -eo pipefail

COLOR_GREEN=$(tput setaf 2)
COLOR_BLUE=$(tput setaf 4)
COLOR_RED=$(tput setaf 1)
COLOR_YELLOW=$(tput setaf 3)
COLOR_NC=$(tput sgr0)

cd "$(dirname "$0")/../.."

echo "${COLOR_BLUE}🔍 Starting MyPy Type Checking (2025-2026 Standards)${COLOR_NC}"
echo "${COLOR_BLUE}📋 Running strict type analysis...${COLOR_NC}"
echo ""

# Check if mypy cache exists and is valid
if [ -d ".mypy_cache" ]; then
    echo "${COLOR_BLUE}💾 Using MyPy cache for faster analysis${COLOR_NC}"
fi

# Run MyPy with comprehensive reporting
if uv run mypy . --show-error-codes --show-error-context --color-output; then
    echo ""
    echo "${COLOR_GREEN}✅ MyPy type checking passed successfully!${COLOR_NC}"
    echo "${COLOR_GREEN}📊 Your code follows strict type safety standards${COLOR_NC}"
else
    echo ""
    echo "${COLOR_RED}❌ MyPy found type issues.${COLOR_NC}"
    echo "${COLOR_RED}→ Please fix the type issues above and re-run the command.${COLOR_NC}"
    echo ""
    echo "${COLOR_YELLOW}💡 Common fixes:${COLOR_NC}"
    echo "${COLOR_YELLOW}  • Add type annotations to function parameters and return values${COLOR_NC}"
    echo "${COLOR_YELLOW}  • Use built-in types: list[T], dict[K,V], T | None${COLOR_NC}"
    echo "${COLOR_YELLOW}  • Import types from typing only when necessary${COLOR_NC}"
    echo "${COLOR_YELLOW}  • Use # type: ignore[error-code] for unavoidable issues${COLOR_NC}"
    exit 1
fi

echo "${COLOR_GREEN}🎉 Type checking completed successfully!${COLOR_NC}"
