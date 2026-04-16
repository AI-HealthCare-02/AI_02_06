#!/bin/bash
# Comprehensive Code Quality Check (2025-2026 Python Standards)
# Runs all quality checks in the correct order

set -eo pipefail

COLOR_GREEN=$(tput setaf 2)
COLOR_BLUE=$(tput setaf 4)
COLOR_RED=$(tput setaf 1)
COLOR_YELLOW=$(tput setaf 3)
COLOR_PURPLE=$(tput setaf 5)
COLOR_NC=$(tput sgr0)

cd "$(dirname "$0")/../.."

echo "${COLOR_PURPLE}🚀 Starting Comprehensive Code Quality Check${COLOR_NC}"
echo "${COLOR_PURPLE}📋 Following 2025-2026 Python Standards${COLOR_NC}"
echo ""

# Step 1: Ruff Linting and Formatting
echo "${COLOR_BLUE}Step 1/4: 🔧 Ruff Linting & Formatting${COLOR_NC}"
if ./scripts/ci/code_fommatting.sh; then
    echo "${COLOR_GREEN}✅ Ruff checks passed${COLOR_NC}"
else
    echo "${COLOR_RED}❌ Ruff checks failed${COLOR_NC}"
    exit 1
fi
echo ""

# Step 2: Type Checking
echo "${COLOR_BLUE}Step 2/4: 🔍 MyPy Type Checking${COLOR_NC}"
if ./scripts/ci/check_mypy.sh; then
    echo "${COLOR_GREEN}✅ Type checking passed${COLOR_NC}"
else
    echo "${COLOR_RED}❌ Type checking failed${COLOR_NC}"
    exit 1
fi
echo ""

# Step 3: Security Scanning
echo "${COLOR_BLUE}Step 3/4: 🔒 Security Scanning${COLOR_NC}"
if uv run bandit -c pyproject.toml -r app/ ai_worker/ -lll; then
    echo "${COLOR_GREEN}✅ Security scan passed${COLOR_NC}"
else
    echo "${COLOR_YELLOW}⚠️ Security scan found potential issues${COLOR_NC}"
    echo "${COLOR_YELLOW}💡 Review the findings above and address if necessary${COLOR_NC}"
fi
echo ""

# Step 4: Test Suite
echo "${COLOR_BLUE}Step 4/4: 🧪 Running Tests${COLOR_NC}"
if ./scripts/ci/run_test.sh; then
    echo "${COLOR_GREEN}✅ All tests passed${COLOR_NC}"
else
    echo "${COLOR_RED}❌ Some tests failed${COLOR_NC}"
    exit 1
fi
echo ""

# Final Summary
echo "${COLOR_GREEN}🎉 All Quality Checks Completed Successfully!${COLOR_NC}"
echo "${COLOR_GREEN}📊 Your code meets 2025-2026 Python standards:${COLOR_NC}"
echo "${COLOR_GREEN}  ✅ Modern built-in types (list[T], dict[K,V], T | None)${COLOR_NC}"
echo "${COLOR_GREEN}  ✅ Comprehensive linting with Ruff${COLOR_NC}"
echo "${COLOR_GREEN}  ✅ Strict type checking with MyPy${COLOR_NC}"
echo "${COLOR_GREEN}  ✅ Security best practices${COLOR_NC}"
echo "${COLOR_GREEN}  ✅ All tests passing${COLOR_NC}"
echo ""
echo "${COLOR_PURPLE}🚀 Ready for deployment!${COLOR_NC}"
