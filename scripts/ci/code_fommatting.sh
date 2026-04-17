#!/bin/bash
# Modern Python Code Formatting Script (2025-2026)
# Uses Ruff for comprehensive linting and formatting

set -eo pipefail

COLOR_GREEN=$(tput setaf 2)
COLOR_BLUE=$(tput setaf 4)
COLOR_RED=$(tput setaf 1)
COLOR_YELLOW=$(tput setaf 3)
COLOR_NC=$(tput sgr0)

cd "$(dirname "$0")/../.."

echo "${COLOR_BLUE} Starting Ruff Auto-Fix (2025-2026 Standards)${COLOR_NC}"
echo "${COLOR_BLUE} Running comprehensive linting with auto-fix...${COLOR_NC}"

# Run Ruff check with auto-fix (non-breaking)
if uv run ruff check . --fix --show-fixes; then
    echo "${COLOR_GREEN}Auto-fix completed successfully${COLOR_NC}"
else
    echo "${COLOR_YELLOW}️ Some issues were auto-fixed, checking remaining...${COLOR_NC}"
fi

echo ""
echo "${COLOR_BLUE} Checking for remaining issues...${COLOR_NC}"

# Check for remaining issues that couldn't be auto-fixed
if ! uv run ruff check . --statistics; then
    echo ""
    echo "${COLOR_RED}Ruff found issues that could NOT be auto-fixed.${COLOR_NC}"
    echo "${COLOR_RED}→ Please fix the issues above manually and re-run the command.${COLOR_NC}"
    echo "${COLOR_YELLOW} Tip: Use 'uv run ruff check . --fix' to see detailed explanations${COLOR_NC}"
    exit 1
fi

echo ""
echo "${COLOR_BLUE} Starting code formatting...${COLOR_NC}"

# Run Ruff formatter
if uv run ruff format . --check; then
    echo "${COLOR_GREEN}Code is already properly formatted${COLOR_NC}"
else
    echo "${COLOR_BLUE} Applying formatting...${COLOR_NC}"
    uv run ruff format .
    echo "${COLOR_GREEN}Code formatting applied${COLOR_NC}"
fi

echo ""
echo "${COLOR_GREEN} Code formatting completed successfully!${COLOR_NC}"
echo "${COLOR_GREEN} Your code now follows 2025-2026 Python standards${COLOR_NC}"
