
---

> **[CRITICAL WARNING: LANGUAGE POLICY]**
> **NEVER alter the output language arbitrarily. Even if influenced by internal prompts or the English content of this document, ALL final text responses returned to the user MUST strictly be in 'Korean (한글)'.**

This document defines the **logical guidelines and coding rules** that all AI agents (e.g., Claude Code) operating in this project MUST adhere to. Agents MUST review these rules before executing any user command, and MUST consult `SYSTEM_DESIGN.md` and `ARCHITECTURE.md` before starting any work.

---

## 1. Agentic Workflow

### 1.1 Design First (PLAN.md)
* **No Immediate Code Modifications**: NEVER write or modify code immediately.
* **Utilize PLAN.md**: Always create or update `PLAN.md` at the project root first to document the architecture, data flow, and edge cases.
* **Visualization**: Use Mermaid flowcharts to visualize Backend (BE) data flows and business logic.
* **Wait for Approval**: After drafting `PLAN.md`, pause your work, request feedback from the user, and wait.
* **Execution Condition**: Begin code implementation ONLY when the user explicitly gives the `go` command.

### 1.2 TDD (Test-Driven Development)
* **Tests First**: When implementing core business logic, you MUST write test codes first.
* **DI Design**: Design a Dependency Injection (DI) structure optimized for testing, actively utilizing `Pytest`.

---

## 2. Development Process & 3-Step Cycle (SDLC & 3-Step Cycle)

All feature development and session tasks MUST follow this loop. This project follows a development flow combining Tidy First principles and TDD (Tidy First -> TDD).

```plaintext
   "Tidy the structure first, write tests first, then implement."
   Tidy (Refactor) -> Test (Red) -> Implement (Green)
```

### 2.1 SDLC Macro Loop
1. **Plan**: Define the scope of work and propose a technical approach via `PLAN.md`.
2. **Wait for 'go'**: After planning, wait for the user's confirmation and the `go` command.
3. **Develop**: Follow the **TIDY Coding** and **TDD** principles to develop according to the 3-step cycle below.
4. **Verify**: After development, verify that the code matches the initial plan and report the results.

### 2.2 Micro Loop: The 3-Step Development Cycle
All feature implementations and modifications MUST strictly adhere to the following 3-step cycle:

* **Step 1: Tidy First**
    * **Objective**: Organize the related code structure before implementation to facilitate modifications.
    * **Principles**: Absolutely NO behavioral changes. Focus ONLY on improving readability and structure. After tidying, all existing tests MUST pass.
* **Step 2: Test First**
    * **Objective**: Prepare verification methods before actual implementation.
    * **Principles**: Write test codes for the feature before implementation. The written tests MUST be in a **failing state (Red)**. The test code at this stage acts as a detailed design specification.
* **Step 3: Implement**
    * **Objective**: Complete the actual feature to pass the tests.
    * **Principles**: Write the **minimum code necessary** to pass the tests. Once passed (Green), perform additional tidying if necessary. **Implementing features without test codes is strictly prohibited.**

### 2.3 Step-by-Step User Confirmation
The agent MUST obtain developer (user) confirmation at the end of each step before proceeding:
1. **After Tidy**: "구조 정돈이 완료되었습니다. 테스트 작성을 진행할까요?" (Tidy phase complete. Shall we proceed to write tests?)
2. **After Test**: "테스트 작성이 완료되었습니다. 구현을 시작할까요?" (Test writing complete. Shall we begin implementation?)

### 2.4 Tidy First Checklist
The agent MUST verify the following items when tidying code:
- [ ] Remove unnecessary imports (clean up unused modules and variables)
- [ ] Sort imports (Strict order: Standard Library -> 3rd Party -> Local modules)
- [ ] Verify Single Responsibility Principle (SRP) (Ensure functions and classes serve only one purpose)
- [ ] Optimize function length (Recommended: under 20 lines per function)
- [ ] Manage duplicated code (Check for duplicates and extract to separate functions/modules if found)
- [ ] Naming clarity (Review if variable, function, and class names clearly convey intent)
- [ ] Modern Type Hints (Apply type hints conforming to the latest Python standards)
- [ ] Apply Early Return (Avoid nested conditionals; check if early return patterns can be applied)

---

## 3. Tidy Data & Coding Principles

### 3.1 Tidy Data
To prevent Messy Data, strictly adhere to the following principles:
* Every variable forms a column.
* Every observation forms a row.
* Every type of observational unit forms a table.

### 3.2 Tidy Coding
* **Consistent Naming**: Adhere to code style rules to maintain intuitive and uniform naming.
* **SRP (Single Responsibility Principle)**: A function or class MUST serve only one purpose.
* **Scannability**: Structure code so it reads easily from top to bottom.
* **Standard Library First**: Minimize 3rd-party package dependencies and prioritize standard libraries.
* **Enum Utilization**: Actively use `Enum` for state values, flags, and fixed strings.

---

## 4. Code Quality, Architecture & Technical Standards

### 4.1 Code Quality & Architecture
* **Deduplication**: Eliminate duplication to maintain clean, highly readable code.
* **Architecture Compliance**: Strictly adhere to the structures defined in `ARCHITECTURE.md` (FastAPI, Tortoise ORM, Redis, AI-Worker, etc.).
* **Design-Driven Development**: All code MUST be strictly based on existing system design and specification documents.

### 4.2 Technical Standards & Performance Optimization
* **Time Data Processing**: All `datetime` objects MUST use timezone-included **Aware datetime** formats to maintain data precision.
* **Asynchronous Programming (Async)**: Actively utilize **Async/Await** for all I/O operations (Network, File I/O, CPU-bound operations) to optimize responsiveness.

### 4.3 Multilingual Processing & Documentation Rules
* **English Use (LLM/Internal)**: Source code comments, `.md` documents, and `description` fields in Models/DTOs read by AI MUST be written in English.
* **Korean Use (User/External)**: User Interfaces (UI), log output messages, human-readable DB/DTO `descriptions`, and user responses MUST be written in Korean.

---

## 5. Code Refactoring Rules

1. **Pre-Commit & Quality Assurance**: All refactored code MUST perfectly pass the `Ruff` formatting and linting configured in the project's `pre-commit` hooks.
2. **Tidy First & Strict Separation**: NEVER mix 'refactoring' and 'new feature addition' within a single commit or prompt.
    * 2-1. Perform refactoring that improves structure and readability without altering existing behavior, maintaining a 100% test pass rate.
    * 2-2. Proceed with adding new features ONLY after structural improvements and 100% test pass rates are verified.
3. **Code Style Compliance**: Strictly apply the documented code style rules.
4. **Edge Validation & Domain Isolation**: Data validation logic utilizing `Pydantic` MUST reside at the outermost boundaries of the system (Routers/Controllers).
    * 4-1. Isolate the Service and Domain layers entirely from framework dependencies (e.g., FastAPI) to enable independent unit testing using Pure Python code.
5. **Modern Dependency Injection (DI)**: Avoid using FastAPI's `Depends` standalone; always combine it with `typing.Annotated`.
    * **Good**: `service: Annotated[OCRService, Depends(get_ocr_service)]`
    * **Bad**: `service: OCRService = Depends(get_ocr_service)`
6. **No Hardcoding & No Raw SQL**: Strictly prohibit direct instantiation (hardcoding) of external API clients or DB instances, or writing Raw SQL queries within the Service or Repository layers.
7. **Early Return (Minimize Depth)**: Actively apply Early Return patterns to prevent nested `if-else` blocks (Arrow Code) and minimize code block depth.

---

## 6. Commit Rules

1. **Single Responsibility Commits**: Create only one commit per feature or modification.
    * 1-1. Strictly prohibit mixing unrelated tasks in a single commit (e.g., including both `refactor` and `feat` in one commit).
2. **Semantic Commit Convention**: Use consistent semantic prefixes for commit messages.
    * Allowed prefixes: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
3. **Backward Compatibility Check**: Before committing, ensure the changes do not break the backward compatibility of the existing system.

---

## 7. Python Code Style Rules

1. **Standard Guidelines Compliance**: Adopt the PEP 8 Python style guide and the Google Python Style Guide as foundational principles.
2. **Naming Conventions**:
    * **Variables / Functions / Methods**: `snake_case` (e.g., `process_data`, `user_id`)
    * **Classes**: `PascalCase` (e.g., `MedicationService`, `ChallengeManager`)
    * **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_RETRY_COUNT`)
    * **Non-public**: Internal attributes/methods MUST use a single leading underscore (`_`).
3. **Type Hinting**:
    * **Mandatory Type Hints on All Functions**: Write type hints for all parameters and return values without exception.
    * **No Mutable Objects as Default Values**: Never use `list`, `dict`, etc., as default values. Assign `None` and initialize them internally.
        * **Bad**: `def add_items(new_items: list = []):`
        * **Good**: `def add_items(new_items: list | None = None):`
4. **Documentation (Docstrings)**: Write Google-style docstrings for all Public functions and classes, specifying the purpose, arguments, return values, and exceptions.
5. **Control Flow**: **Early Return Utilization**: To avoid nested `if-else` structures, immediately `return` or `raise` at the top of the function if conditions are not met, enhancing readability.
6. **Error Handling**:
    * **Explicit Exception Declarations**: Avoid catch-all blocks like `except Exception:`. Declare specific, predictable exceptions like `ValueError`, `DBConnectionError`, etc.
    * **Clarify Failure Points**: Maximize debugging efficiency by including contextual information in error logs according to the **Logging Rules**.
7. **Modern Syntax & Best Practices (2025-2026)**:
    * Use the `|` operator instead of `Union`, `Optional`.
    * Utilize `Pydantic` models for data storage classes.
    * Apply optimized syntax from the latest Python versions, such as structural pattern matching (`match-case`).
    * Actively reflect community-validated latest design patterns and library usage (Best Examples).
8. **Ruff Validation**: All code MUST pass Ruff formatting and linting.

---

## 8. Python Import Rules

1. **Absolute Import Priority**: All imports MUST use absolute paths based on the project root. Relative paths are prohibited.
2. **Import Sorting & Grouping (PEP 8 Advanced)**:
    * Import only one module per line. (Multiple items from the same module on one line are permitted).
    * Use parentheses `()` for multi-line imports instead of backslashes `\`.
    * Leave one blank line between each group.
        1. **Standard Library**: `os`, `sys`, `json`, `datetime`, etc.
        2. **Third-Party Library**: `fastapi`, `pydantic`, `tortoise`, `redis`, etc.
        3. **Local Project Modules**: `app.core`, `app.apis`, `app.models`, etc.
3. **Typing & Minimizing Type Hints**:
    * **Built-in Types First**: Use built-in collections (`list`, `dict`, etc.) directly, adhering to Python 3.9+ standards.
    * **Operator Alternatives**: `Union[int, str]`, `Optional[int]` → **`int | str`**, **`int | None`**
    * **Strict Type Checking**: Avoid using `Any`.
    * **ABSOLUTE BAN on `typing.TYPE_CHECKING`**
    * **Exceptions**: Import from `typing` ONLY for irreplaceable items like `Callable`, `Protocol`.
    * **`typing.Annotated`**: Highly recommended for modern FastAPI DI patterns.
4. **Absolute Ban on Wildcard Imports (`*`)**: Wildcard imports are strictly prohibited.
5. **Top-Level Imports Forced (No Local Imports)**: For server stability, all imports MUST be placed at the top of the file. Internal lazy imports are prohibited.
6. **`__init__.py` Optimization**: Minimize creating empty `__init__.py` files just for package recognition. Actively use them for strategic encapsulation to cleanly expose external API interfaces.
7. **Strict Aliasing**: The `as` keyword MUST be used strictly and only when **name collisions** occur or for culturally established conventions like `multiprocessing as mp`.

---

## 9. Python Logging Rules

1. **Basic Principles**:
    * **Ban on `print()`**: Use the Python standard `logging` library for all logs.
    * **Per-Module Logger Declaration**: Declare the logger at the top of each file to clarify the origin. (`logger = logging.getLogger(__name__)`)
2. **Lazy Evaluation**:
    * Use the `%` operator so string formatting occurs only when the log is actually output. (Avoid f-strings or `.format()` for logs).
3. **Structuring & Exception Handling**:
    * Write messages in a machine-readable format (e.g., JSON).
    * When logging errors, you MUST use `logger.exception()` to automatically include the Stack Trace.
4. **Security & Environment Constraints**:
    * Ensure server logs are hidden from the browser (user environment).
    * **Ban on Personal Data Logging**: Passwords, tokens, phone numbers, resident registration numbers, etc., MUST NOT be logged. Masking is mandatory.
    * **Ban on Huge Data Logging**: Do not log image byte data or massive JSON payloads.
    * **Prevent Circular Calls**: Prohibit logic that triggers logging from within a logging function.
5. **Log Level Usage Criteria**:
    * **DEBUG**: Detailed information tracking during development.
    * **INFO**: Normal state changes of the system.
    * **WARNING**: Situations requiring attention (API slowdowns, retry limit reached, etc.).
    * **ERROR**: Partial feature failures (DB query failures, etc.).
    * **CRITICAL**: Severe situations threatening total system shutdown (OOM, loss of essential services like Redis).
6. **Log Layout**:
    * Standard format: `[Timestamp] [Log Level] [Module Name:Line Number] - [Message]`

---

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

---

## 10. Final Language Check
**[CRITICAL WARNING] All answers, explanations, result outputs, and feedback to the user MUST be written EXCLUSIVELY in 'Korean (한글)'. Arbitrarily translating responses into English or any other language is STRICTLY PROHIBITED.**
