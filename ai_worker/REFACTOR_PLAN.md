# ai_worker/ 도메인 기반 리팩토링 PLAN

> 작성일: 2026-04-26
> 대상: `ai_worker/` 패키지 전체
> 원칙: Domain-Driven 폴더 구조 + Clean Code (PEP 8 / Google Style / SRP / Low Depth)

---

## 1. 현재 구조 진단

### 1.1 현재 트리

```
ai_worker/
├── core/                       # ✅ 인프라 (config, logger, redis_client, redis_retry)
├── providers/                  # ⚠️ 역할 기반 — embedding/llm/router 가 어느 도메인 소속인지 불명확
│   ├── embedding.py            #   → RAG 도메인 전용
│   ├── llm.py                  #   → RAG + Session-Compact 양쪽에서 사용
│   └── router.py               #   → Tool-Calling 도메인 전용
├── tasks/                      # ⚠️ 역할 기반 — RQ task 라는 공통점만으로 묶임
│   ├── compact_tasks.py        #   → Session-Compact 도메인
│   ├── ocr_tasks.py            #   → OCR 도메인
│   ├── rag_tasks.py            #   → RAG 도메인
│   └── tool_tasks.py           #   → Tool-Calling 도메인
├── utils/                      # 🔴 가장 모호 — 5개 파일이 4개 다른 도메인에 속함
│   ├── chunker.py              #   → dead (service.py 만 사용, service.py 도 dead)
│   ├── image_preprocessor.py   #   → OCR 도메인
│   ├── ocr.py                  #   → dead (service.py 만 사용)
│   ├── rag.py                  #   → RAG 도메인 (RAGGenerator 클래스, 417줄!)
│   └── text_postprocessor.py   #   → OCR 도메인
├── data/medicines.json         #   → dead 데이터 (service.py 만 참조)
├── service.py                  #   → 🔴 dead code (외부 import 0건, RQ task 가 직접 호출 안 함)
└── main.py                     # ✅ 엔트리포인트
```

### 1.2 발견된 문제

| 코드 | 문제 |
|---|---|
| `service.py` | **사용처 0** (`grep -r "ai_worker.service"` 결과 0건). 옛 동기 호출 흐름의 잔재. |
| `utils/chunker.py` | service.py 에서만 사용 → 같이 dead. |
| `utils/ocr.py` | service.py 에서만 사용 → 같이 dead. (실제 OCR 은 `tasks/ocr_tasks.py` 의 `_call_clova_ocr` 가 처리) |
| `data/medicines.json` | service.py 의 `_MEDICINES_PATH` 만 참조 → 같이 dead. |
| `utils/rag.py` | **417줄** — `RAGGenerator` 클래스 하나가 너무 큼. 책임 4가지 혼재 (프롬프트 조립 / 쿼리 재작성 / 청크 정렬 / OpenAI 호출). |
| `tasks/ocr_tasks.py` | **250줄** — RQ task 함수 + CLOVA OCR 호출 + DB 매칭 + Redis IO 모두 한 파일. |
| `providers/llm.py` | RAG `RAGGenerator` import + 자체 `summarize_messages` 정의 — 두 도메인 혼합. |
| `utils/` 폴더 자체 | "잡동사니" 의미. 도메인 정보 0. |

### 1.3 외부 의존성 (수정 시 영향)

리팩토링 시 import 경로를 따라가야 할 외부 참조:

| 외부 파일 | 현재 import |
|---|---|
| `app/tests/test_ai_worker_embedding_provider.py` | `from ai_worker.providers import embedding`, `from ai_worker.tasks import rag_tasks` |
| `app/tests/test_ai_worker_rag_tasks.py` | `from ai_worker.tasks import rag_tasks` |
| `app/tests/test_ai_worker_router_provider.py` | `from ai_worker.providers import router` |
| `app/tests/test_ai_worker_tool_tasks.py` | `from ai_worker.tasks import tool_tasks`, `from ai_worker.providers import router` |
| `app/tests/test_rewrite_query.py` | `from ai_worker.utils.rag import RAGGenerator` |
| `app/tests/test_summarize_prompt.py` | `from ai_worker.utils.rag import RAGGenerator, _strip_code_fence` |

→ 7개 테스트 파일의 import 경로를 새 구조로 일괄 교체 필요.

---

## 2. 목표 구조 (도메인 기반)

```
ai_worker/
├── main.py                          # 엔트리포인트 (변경 최소)
│
├── core/                            # 인프라 (도메인 독립)
│   ├── __init__.py
│   ├── config.py                    # (변경 없음)
│   ├── logger.py                    # (변경 없음)
│   ├── redis_client.py              # (변경 없음)
│   ├── redis_retry.py               # (변경 없음)
│   ├── openai_client.py             # 🆕 AsyncOpenAI 싱글톤 분리 (현재 llm.py / router.py 중복)
│   └── rq_result_publisher.py       # 🆕 OCR/RAG 의 Redis SETEX 로직 공통화 (DRY)
│
└── domains/
    ├── __init__.py
    │
    ├── ocr/                         # 처방전 이미지 → 약품 인식
    │   ├── __init__.py
    │   ├── jobs.py                  # ← tasks/ocr_tasks.py (RQ entry)
    │   ├── image_preprocessor.py    # ← utils/image_preprocessor.py (이름 유지, 이미 명확)
    │   ├── text_extractor.py        # ← ocr_tasks.py 내부의 _call_clova_ocr (CLOVA API 호출만)
    │   ├── text_normalizer.py       # ← utils/text_postprocessor.py (clean / extract_candidates)
    │   └── medicine_matcher.py      # ← ocr_tasks.py 내부의 _match_candidates_from_db (pg_trgm DB 매칭)
    │
    ├── rag/                         # RAG 검색 + 응답 생성
    │   ├── __init__.py
    │   ├── jobs.py                  # ← tasks/rag_tasks.py (RQ entry)
    │   ├── embedding_provider.py    # ← providers/embedding.py (이름 명확화)
    │   ├── response_generator.py    # ← utils/rag.py 의 RAGGenerator.generate_chat_response 부분
    │   ├── query_rewriter.py        # ← utils/rag.py 의 rewrite_query 부분
    │   ├── prompt_builder.py        # ← utils/rag.py 의 시스템/유저 프롬프트 조립 부분
    │   └── chunk_ranker.py          # ← utils/rag.py 의 청크 정렬·필터 헬퍼들
    │
    ├── tool_calling/                # Phase Y — Router LLM + tool execution
    │   ├── __init__.py
    │   ├── jobs.py                  # ← tasks/tool_tasks.py (RQ entry)
    │   └── router_llm.py            # ← providers/router.py (Router LLM 호출)
    │
    └── session_compact/             # Phase Z — 채팅 세션 요약
        ├── __init__.py
        ├── jobs.py                  # ← tasks/compact_tasks.py (RQ entry)
        └── summarizer.py            # ← providers/llm.py 의 summarize_messages
```

### 2.1 폐기 대상 (dead code)

| 파일 | 처분 |
|---|---|
| `ai_worker/service.py` | **삭제** (외부 import 0) |
| `ai_worker/utils/chunker.py` | **삭제** (service.py 만 사용) |
| `ai_worker/utils/ocr.py` | **삭제** (service.py 만 사용; 실제 OCR 은 ocr_tasks.py) |
| `ai_worker/data/medicines.json` | **삭제** (service.py 만 참조) |
| `ai_worker/data/` 폴더 | 비어있으면 삭제 |
| `ai_worker/utils/` 폴더 | 모든 파일 이전 후 삭제 |
| `ai_worker/providers/` 폴더 | 모든 파일 이전 후 삭제 |
| `ai_worker/tasks/` 폴더 | 모든 파일 이전 후 삭제 |

---

## 3. 파일 매핑 테이블

### 3.1 OCR 도메인

| 옛 위치 | 새 위치 | 책임 변경 |
|---|---|---|
| `tasks/ocr_tasks.py` (전체 250줄) | `domains/ocr/jobs.py` | RQ task 함수만 남김 — `process_ocr_task()` 가 다른 모듈 함수 호출 |
| `tasks/ocr_tasks.py` 내 `_call_clova_ocr()` | `domains/ocr/text_extractor.py::extract_text_from_image()` | CLOVA API 호출만 |
| `tasks/ocr_tasks.py` 내 `_match_candidates_from_db()` | `domains/ocr/medicine_matcher.py::match_candidates_to_medicines()` | pg_trgm DB 매칭만 |
| `tasks/ocr_tasks.py` 내 `_redis_setex()` | `core/rq_result_publisher.py::publish_result()` | DRY — RAG/OCR 공통 |
| `utils/image_preprocessor.py` (`preprocess_for_ocr`) | `domains/ocr/image_preprocessor.py` (그대로) | 이름 유지 (이미 명확) |
| `utils/text_postprocessor.py` (`clean_ocr_text`, `extract_medicine_candidates`) | `domains/ocr/text_normalizer.py` | 더 명확한 도메인 용어 |

### 3.2 RAG 도메인

| 옛 위치 | 새 위치 | 책임 변경 |
|---|---|---|
| `tasks/rag_tasks.py` (3개 함수) | `domains/rag/jobs.py` | RQ task 함수만 |
| `providers/embedding.py` | `domains/rag/embedding_provider.py` | 이름 명시화, 위치만 이동 |
| `providers/llm.py` 의 RAG 부분 (`generate_chat_response`, `rewrite_query`) | 아래 3개로 분해 | — |
| └ generate_chat_response | `domains/rag/response_generator.py::generate_response()` | 응답 생성 단일 책임 |
| └ rewrite_query | `domains/rag/query_rewriter.py::rewrite_user_query()` | 쿼리 재작성 단일 책임 |
| `utils/rag.py` (417줄, `RAGGenerator` 클래스) | 아래 4개로 분해 | **클래스 분해 + Low Depth 적용** |
| └ 시스템/유저 프롬프트 조립 | `domains/rag/prompt_builder.py` | 함수형 빌더 |
| └ 청크 정렬·필터 헬퍼 | `domains/rag/chunk_ranker.py` | 청크 score 기반 reorder |
| └ OpenAI 호출 본체 | `domains/rag/response_generator.py` | (위와 동일 파일) |
| └ `_strip_code_fence` | `core/text_helpers.py` 또는 `domains/rag/response_generator.py` 내부 private | 사용처 1곳이라 private 유지 |

### 3.3 Tool-Calling 도메인

| 옛 위치 | 새 위치 | 책임 변경 |
|---|---|---|
| `tasks/tool_tasks.py` (138줄, 6 def) | `domains/tool_calling/jobs.py` | RQ task 함수만 (병렬 tool_calls 라우팅) |
| `providers/router.py` (94줄) | `domains/tool_calling/router_llm.py` | Router LLM 호출 |

### 3.4 Session-Compact 도메인

| 옛 위치 | 새 위치 | 책임 변경 |
|---|---|---|
| `tasks/compact_tasks.py` (32줄) | `domains/session_compact/jobs.py` | RQ task |
| `providers/llm.py` 의 `summarize_messages()` | `domains/session_compact/summarizer.py` | 요약 단일 책임 |

### 3.5 Core (도메인 독립 인프라)

| 옛 위치 | 새 위치 | 책임 |
|---|---|---|
| `core/config.py` | (그대로) | 환경변수 |
| `core/logger.py` | (그대로) | 로깅 |
| `core/redis_client.py` | (그대로) | Redis connection (Consumer) |
| `core/redis_retry.py` | (그대로) | retry 데코레이터 |
| AsyncOpenAI 싱글톤 (현재 `providers/llm.py`, `providers/router.py`, `utils/rag.py` 3곳에 중복) | `core/openai_client.py::get_openai_client()` | DRY — 1회 인스턴스화 |
| Redis SETEX 결과 publish 로직 (현재 `ocr_tasks.py`, `rag_tasks.py` 산재) | `core/rq_result_publisher.py::publish_result(key, payload, ttl)` | DRY |

---

## 4. Clean Code 적용 포인트

### 4.1 함수 분해 우선순위 (긴 함수)

| 함수 | 현재 줄수 | 분해 방향 |
|---|---|---|
| `tasks/ocr_tasks.py::process_ocr_task` | ~70줄 | Step1~5 를 각각 별도 함수로 추출 → 메인은 5줄짜리 orchestrator |
| `utils/rag.py::RAGGenerator.generate_chat_response` | ~130줄 추정 | 프롬프트 조립 / 청크 정렬 / OpenAI 호출 / 응답 파싱 4단계로 분리 |
| `tasks/tool_tasks.py::run_tool_calls_via_rq` | ~50줄 추정 | 병렬 호출 dispatch / 결과 수집 / 에러 처리 분리 |

### 4.2 Low Depth (Guard Clauses)

```python
# Before (Depth 4)
def process(item):
    if item:
        if item.is_valid:
            for entry in item.entries:
                if entry.score > 0.5:
                    do_thing(entry)

# After (Depth 1)
def process(item):
    if not item:
        return
    if not item.is_valid:
        return
    valid_entries = [e for e in item.entries if e.score > 0.5]
    for entry in valid_entries:
        do_thing(entry)
```

→ `utils/rag.py` 의 청크 필터링·프롬프트 조립 코드 우선 적용 대상.

### 4.3 Docstring 한글 Google 스타일

```python
def extract_text_from_image(image_path: str) -> str:
    """OCR 이미지에서 텍스트를 추출한다.

    CLOVA OCR API 를 호출하여 이미지에서 글자만 추출한다.
    네트워크 오류는 호출자가 처리하도록 그대로 전파한다.

    Args:
        image_path: OCR 처리할 이미지 파일의 절대 경로.

    Returns:
        추출된 텍스트 (공백으로 구분된 inferText 들의 연결).

    Raises:
        ValueError: CLOVA_OCR 환경변수가 설정되지 않은 경우.
        httpx.HTTPStatusError: API 응답이 4xx/5xx 인 경우.
    """
```

→ 모든 public 함수/클래스에 적용. 기존 영문 docstring 은 한글로 교체.

### 4.4 Type Hint 일관성

- 모든 함수 시그니처에 built-in 타입 사용 (`list[str]`, `dict[str, int]`, `int | None`)
- `Any` 금지 (CLAUDE.md §7-3 룰)
- DTO 가 필요한 곳은 `app.dtos.*` 의 Pydantic 모델 그대로 사용

### 4.5 DRY — `core/` 공통 컴포넌트 신규

```python
# core/openai_client.py — 싱글톤 (현재 3곳 중복)
def get_openai_client() -> AsyncOpenAI: ...

# core/rq_result_publisher.py — RAG/OCR 공통 SETEX 로직
@redis_retry()
def publish_result(redis_conn, key: str, payload: str, ttl: int) -> None: ...
```

---

## 5. 단계별 실행 순서 (승인 후)

### Step 0 — 안전망
- 현재 브랜치 (`integration/step4-final-schema`) 위에서 진행
- `git stash` 또는 작업 시작 전 commit 으로 현 시점 보존
- ruff + pytest baseline 통과 확인

### Step 1 — Dead code 제거 (위험 0)
1. `ai_worker/service.py` 삭제
2. `ai_worker/utils/chunker.py` 삭제
3. `ai_worker/utils/ocr.py` 삭제
4. `ai_worker/data/medicines.json` 삭제 + 빈 폴더 정리
5. ruff + pytest 회귀 (모두 통과해야 다음 단계)

### Step 2 — 새 도메인 폴더 + core 헬퍼 생성 (이동 X)
1. `ai_worker/domains/` 폴더 + 4개 도메인 서브폴더 (`__init__.py` 만)
2. `core/openai_client.py` 신규 — 싱글톤 정의
3. `core/rq_result_publisher.py` 신규 — `@redis_retry()` 적용
4. ruff 통과

### Step 3 — OCR 도메인 이전 + 함수 분해
1. `tasks/ocr_tasks.py` → `domains/ocr/jobs.py`
2. CLOVA 호출 부분 → `domains/ocr/text_extractor.py`
3. DB 매칭 부분 → `domains/ocr/medicine_matcher.py`
4. `utils/image_preprocessor.py` → `domains/ocr/image_preprocessor.py`
5. `utils/text_postprocessor.py` → `domains/ocr/text_normalizer.py`
6. `_redis_setex` → `core/rq_result_publisher.publish_result` 사용으로 교체
7. `process_ocr_task` 5줄 orchestrator 로 단순화
8. 외부 테스트 import 경로 0건 (OCR 테스트는 cross-service 가 아니므로) — 변경 없음
9. ruff + pytest 회귀

### Step 4 — RAG 도메인 이전 + 클래스 분해
1. `providers/embedding.py` → `domains/rag/embedding_provider.py`
2. `tasks/rag_tasks.py` → `domains/rag/jobs.py`
3. `utils/rag.py` 의 `RAGGenerator` 분해 → `prompt_builder.py` / `response_generator.py` / `query_rewriter.py` / `chunk_ranker.py`
4. AsyncOpenAI 인스턴스화는 `core/openai_client.get_openai_client()` 로 통일
5. **외부 테스트 import 경로 변경**:
   - `test_ai_worker_embedding_provider.py`: `ai_worker.providers.embedding` → `ai_worker.domains.rag.embedding_provider`
   - `test_ai_worker_rag_tasks.py`: `ai_worker.tasks.rag_tasks` → `ai_worker.domains.rag.jobs`
   - `test_rewrite_query.py`: `ai_worker.utils.rag.RAGGenerator` → `ai_worker.domains.rag.query_rewriter.rewrite_user_query`
   - `test_summarize_prompt.py`: `ai_worker.utils.rag.RAGGenerator` + `_strip_code_fence` → 새 위치 (Step 6 의 summarizer 로 합쳐질 가능성)
6. ruff + pytest 회귀

### Step 5 — Tool-Calling 도메인 이전
1. `tasks/tool_tasks.py` → `domains/tool_calling/jobs.py`
2. `providers/router.py` → `domains/tool_calling/router_llm.py`
3. **외부 테스트 import 경로 변경**:
   - `test_ai_worker_router_provider.py`: `ai_worker.providers.router` → `ai_worker.domains.tool_calling.router_llm`
   - `test_ai_worker_tool_tasks.py`: 위 두 경로 모두
4. ruff + pytest 회귀

### Step 6 — Session-Compact 도메인 이전
1. `tasks/compact_tasks.py` → `domains/session_compact/jobs.py`
2. `providers/llm.py` 의 `summarize_messages` → `domains/session_compact/summarizer.py`
3. `providers/llm.py` 자체는 RAG 부분이 Step 4 에서 이미 이전됐으므로 **삭제**
4. ruff + pytest 회귀

### Step 7 — 빈 폴더 정리
1. `ai_worker/utils/` 삭제
2. `ai_worker/providers/` 삭제
3. `ai_worker/tasks/` 삭제

### Step 8 — main.py import 경로 업데이트
1. `from ai_worker.providers.embedding import _ensure_model` → `from ai_worker.domains.rag.embedding_provider import _ensure_model`

### Step 9 — 최종 검증
1. Ruff 전체 PASS
2. Pytest 전체 PASS (Linux 컨테이너)
3. ai-worker 빌드 + 부팅 확인
4. RAG/OCR/Tool 시나리오 smoke

---

## 6. 위험 평가

| 위험 | 발생 가능성 | 완화책 |
|---|---|---|
| `RAGGenerator` 클래스 분해 시 동작 변경 | 중 | 각 분해 함수에 기존 입력/출력 보존 unit test 가 이미 있음 (test_rewrite_query, test_summarize_prompt) |
| RQ task 의 `import path` 가 enqueue 시점에 string 으로 박혀있음 | **고** | `app/services/message_service.py` 등에서 `queue.enqueue('ai_worker.tasks.rag_tasks.func', ...)` 같은 string-based 호출 있는지 사전 확인 필요 |
| 외부 테스트 7개 import 경로 변경 | 중 | Step 별로 실행해서 테스트 통과 확인 후 다음 진행 |
| Dead code 라고 판단한 `service.py` 가 실제로 어딘가에서 동적 import 됨 | 저 | git log 로 마지막 사용 시점 확인, 안전하면 삭제 |

### 6.1 추가 사전 점검 필요

```powershell
# RQ enqueue 시 string 경로 사용 여부
grep -rn "enqueue.*ai_worker" --include="*.py"
grep -rn "ai_worker\." --include="*.py" | grep -i "queue\|enqueue\|job"
```

→ 만약 string 경로로 호출하는 곳이 있다면 매핑 테이블에 추가 필요.

---

## 7. 승인 체크리스트

- [ ] 새 도메인 4개 (`ocr`, `rag`, `tool_calling`, `session_compact`) 분류가 사용자 도메인 모델과 일치하는가?
- [ ] `core/openai_client.py`, `core/rq_result_publisher.py` 신규 모듈 추가 OK?
- [ ] Dead code 4개 (`service.py`, `utils/chunker.py`, `utils/ocr.py`, `data/medicines.json`) 삭제 OK?
- [ ] `utils/rag.py` 의 `RAGGenerator` 클래스를 4개 함수형 모듈로 분해 OK? (또는 클래스 유지를 선호하면 별도 알림)
- [ ] 외부 테스트 7개 파일의 import 경로 자동 갱신 OK?
- [ ] Step 3~6 사이에 사용자 확인 단계 두지 말고 자동 진행 OK?

---

**준비 완료**. 위 PLAN 검토 후 GO 신호 주시면 Step 0 부터 순서대로 진행합니다.
사항 변경 (도메인 이름, 분해 단위, 일부 dead code 보존 등) 있으면 알려주세요.
