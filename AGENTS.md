# AGENTS.md
This document defines the mandatory **logical guidelines and coding rules** for all AI agents (e.g., Claude Code) operating in this project. Agents MUST verify these rules before executing any user commands. **All final text outputs to the user MUST be in Korean.**

---

## 1. Agentic Workflow

### 1.1. Design First (PLAN.md)
* **NEVER write code immediately.**
* Always create/update `PLAN.md` at the project root first to document architecture, data flow, and edge cases.
* Use **Mermaid Flow Charts** to visualize Backend (BE) data flow and business logic.
* Once `PLAN.md` is drafted, PAUSE, ask the user for feedback, and wait.
* Execute code implementation ONLY when the user explicitly commands `go`.

### 1.2. TDD (Test-Driven Development)
* Prioritize tests. When implementing core business logic, write tests first or design a Dependency Injection (DI) structure tailored for testing (Pytest).

---

## 2. Tech Stack
See `CLAUDE.md` for full architecture details. Summary:
* **Backend:** FastAPI, Tortoise ORM, PostgreSQL 15, JWT (RS256) + RTR
* **Frontend:** Next.js 15 (JS Only), Tailwind CSS v4, CSR Static Export
* **Infra:** Docker, AWS EC2, Nginx
* **QA:** Pytest, Bandit, Ruff, pre-commit

---

## 3. Tidy Data & Coding

### 3.1. Tidy Data Principles
Strictly follow these to prevent Messy Data:
* Every variable forms a column.
* Every observation forms a row.
* Every type of observational unit forms a table.

### 3.2. Tidy Coding
* **Consistent Naming:** Keep it intuitive and uniform.
* **SRP (Single Responsibility Principle):** One purpose per function/class.
* **Scannability:** Code must be easily readable top-to-bottom.
* **Standard Libs First:** Minimize 3rd-party packages.
* **Enums:** Mandatory for state values, flags, and fixed strings.

### 3.3. Quality Standards
* Strictly follow **PEP8** and **Google Python Style Guide**.
* All code MUST pass `Ruff` formatting and linting.

---

## 4. Strict Import Rules

### 4.1. General Rules
* All imports at the top of the file.
* **Absolute paths ONLY.** No relative imports (`.`, `..`).
* One module per line (multiple items from the same module on one line are allowed).
* Use parentheses `()` for multi-line imports, NOT backslashes `\`.
* **NO wildcard imports** (`import *`).
* Maintain layered architecture to prevent circular dependencies; minimize internal imports.

### 4.2. Ban on `typing` Module (Python 3.12+)
**STRICTLY FORBIDDEN:** Do NOT use `typing.TYPE_CHECKING` to bypass circular imports (fix the architecture instead). Do NOT import the following from `typing`:

| Forbidden | Use Instead |
|---|---|
| `List`, `Dict`, `Set` | `list[str]`, `dict[str, int]`, `set[int]` |
| `Tuple`, `FrozenSet` | `tuple[int, str]`, `frozenset[str]` |
| `Type`, `Optional` | `type[MyClass]`, `str \| None` |
| `Union`, `Any` | `str \| int`, Omit hint or use `object` |
| `Callable` | Omit hint or use `Protocol` |
| `Sequence`, `Mapping`, `Iterable` | `collections.abc.*` equivalents |

### 4.3. Exception: `typing.Annotated`
* `from typing import Annotated` is HIGHLY RECOMMENDED for modern FastAPI DI patterns.

---

## 5. Refactoring Rules

1. **Tidy First (Strict Separation):** NEVER mix refactoring and new feature additions in a single commit/prompt. Refactor structure/readability first while maintaining 100% test pass rate, THEN add features.
2. **Architectural Fix for Circular Refs:** Do not use `typing.TYPE_CHECKING` as a workaround. Redesign dependencies unidirectionally by extracting interfaces or elevating logic to higher layers.
3. **Edge Validation & Domain Isolation:** Keep `Pydantic` validations at the outermost edge (Routers/Controllers). Isolate Service/Domain layers from framework dependencies (FastAPI) to ensure pure Python testability.
4. **Modern DI over Hardcoding:** Eliminate hardcoded external client/DB instantiations inside Services/Repos. Use modern **`typing.Annotated`** for FastAPI dependencies.
   * GOOD: `service: Annotated[OCRService, Depends(get_ocr_service)]`
   * BAD: `service: OCRService = Depends(get_ocr_service)`
5. **Minimize Depth (Early Return):** Avoid deep nested `if-else` blocks (Arrow Code). Validate exceptions at the top of the function and return early.

---

## 6. Commit Rules
* Use consistent semantic prefixes: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
* ALWAYS verify backward compatibility before committing.

---

## 7. Development Flow (Tidy First -> TDD)

This project follows a development flow combining **Tidy First** principles with **TDD**.

### 7.1. Core Principle

```
"Tidy the structure first, write tests first, then implement."

Tidy (Refactor) -> Test (Red) -> Implement (Green)
```

### 7.2. Three-Step Development Cycle

**Step 1: Tidy First**
- Before implementing, clean up the related code structure.
- NO behavioral changes - only improve readability and structure.
- All existing tests MUST pass after tidying.

**Step 2: Test First**
- Write test code for the feature BEFORE implementation.
- Tests should be in a failing state (Red).
- Tests serve as the specification.

**Step 3: Implement**
- Write minimal code to pass the tests.
- After passing (Green), perform additional tidying if needed.

### 7.3. Commit Separation

Each step MUST be a **separate commit**.

| Step | Prefix | Example |
|------|--------|---------|
| Tidy First | `refactor:` | `refactor: restructure DUR service` |
| Test First | `test:` | `test: add drug interaction tests` |
| Implement | `feat:`/`fix:` | `feat: implement drug interaction check` |

**FORBIDDEN:**
- Mixing `refactor` and `feat` in a single commit.
- Implementing features without tests.

### 7.4. Agent Behavior Guidelines

When user requests a feature implementation:

1. **Ask first:**
   - "Should I tidy the related code first? (Tidy First)"
   - "Should I write tests first? (TDD)"

2. **Document in PLAN.md:**
   ```markdown
   ## Implementation Plan

   ### Phase 1: Tidy First
   - [ ] Analyze existing code structure
   - [ ] Clean up imports
   - [ ] Extract functions if needed

   ### Phase 2: Test First
   - [ ] Design test cases
   - [ ] Write test code
   - [ ] Verify Red state

   ### Phase 3: Implement
   - [ ] Minimal implementation
   - [ ] Verify Green state
   - [ ] Additional tidying if needed
   ```

3. **Get user confirmation at each step:**
   - After Tidy: "Structure cleanup complete. Proceed to write tests?"
   - After Test: "Tests written. Proceed to implementation?"

### 7.5. Tidy First Checklist

- [ ] Remove unnecessary imports
- [ ] Sort imports (stdlib -> third-party -> local)
- [ ] Single responsibility per function/class?
- [ ] Any functions too long? (>20 lines)
- [ ] Any duplicate code?
- [ ] Clear naming?
- [ ] Modern type hints? (See Section 4.2)
- [ ] Early return pattern applicable?

---

## 8. Mandatory Ruff Validation

**CRITICAL: All code changes MUST pass Ruff checks before committing.**

### 8.1. Required Checks Before Every Commit

Run the following commands and ensure all pass with zero errors:

```bash
# 1. Ruff lint check (must pass)
uv run ruff check app/ ai_worker/

# 2. Ruff format check (must pass)
uv run ruff format --check app/ ai_worker/
```

Or run the integrated script:

```bash
./scripts/ci/code_fommatting.sh
```

### 8.2. Auto-fix Before Checking

Before running checks, apply auto-fixes:

```bash
uv run ruff check --fix app/ ai_worker/
uv run ruff format app/ ai_worker/
```

### 8.3. Agent Behavior Rule

* After writing or modifying ANY Python file, the agent MUST run Ruff checks.
* If Ruff reports errors, fix them BEFORE proceeding to the next step.
* NEVER commit code that fails Ruff lint or format checks.
* Include Ruff check results in the commit recommendation output.

### 8.4. Commit Recommendation Format

When recommending a commit, always include Ruff validation status:

```
[Ruff 검사 결과]
- ruff check: PASS
- ruff format: PASS

[Git Add 대상 파일]
- app/services/example_service.py

[커밋 제목]
feat: 예시 서비스 구현
```
