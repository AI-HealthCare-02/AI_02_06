# 4개 기능 통합 검증 — 진행 상황

> 작성일: 2026-04-26
> 범위: lifestyle 가이드 / 청킹 6섹션 / RAG 파이프라인 / 툴 콜링 (+ OCR 흐름 재정비)

---

## 1. 한눈에 보는 검증 결과

| 시나리오 | 상태 | 비고 |
|---|---|---|
| **D-1** 키워드 툴 콜링 | ✅ PASS | `search_hospitals_by_keyword` — 강남역 병원 검색 정상 |
| **A** lifestyle 가이드 + 챌린지 | ✅ PASS | 5섹션 카드 + 챌린지 생성/완료, DB 정합 OK |
| **B** 청킹 6섹션 스키마 | ✅ PASS | enum 깨끗(13섹션 잔재 0), 헤더 프리픽스 정확, 768d L2 정규화 |
| **C** RAG 파이프라인 | ✅ PASS | rewrite → intent → embed → retrieve → LLM 모든 단계 정상 (응답 품질은 데이터 양 의존, 별건) |
| **D-2** 위치 기반 툴 (callback) | ✅ PASS | GPS 권한 → tool-result → Kakao 약국 검색 |
| **D-3** 병렬 툴 콜링 | ✅ PASS | `parallel_tool_calls=True` 정상 작동 |
| **OCR** 비동기 + DB 영속 | ✅ PASS | dedup, 폴링, 카드, 페이지간 회수 모두 정상 |

---

## 2. 핵심 흐름

### 2.1 OCR 비동기 처리 (DB 영속화)

```
[프론트 /ocr]
   │ 파일 선택 + "분석 시작"
   ▼
[프론트 /ocr/loading]
   │ POST /ocr/extract (multipart, image bytes)
   ├─ 즉시 200 + draft_id (medicines=[])
   │  └─ ocr_drafts INSERT (status=pending) + RQ enqueue
   │     (dedup: 같은 사용자+image_hash 활성 draft 있으면 기존 ID 재사용)
   │
   │ 1초마다 GET /ocr/draft/{id} 폴링
   │  └─ status=pending 동안 STEPS 진행 + 우측상단 X (main 으로 빠지기)
   │
   │ status=ready 도달
   ▼
"분석 완료!" overlay (1.2초)
   │
   ▼
[프론트 /ocr/result]
   │ ai-worker 완료된 medicines 표시
   │ 검수 + 사용자 입력
   ├─ ← "메인으로"
   ├─ "다시 촬영" → DELETE /ocr/draft/{id} (consumed_at 설정) + /ocr 이동
   └─ "수정 완료 및 저장" → POST /ocr/confirm (consumed_at + Medication INSERT)

[ai-worker] (백그라운드)
   process_ocr_task(image_bytes, filename, draft_id)
     ├─ extract_text_from_image_bytes (CLOVA OCR)
     ├─ clean_ocr_text + extract_medicine_candidates (정규화 + 약품명 패턴 휴리스틱)
     ├─ asyncio.run(_match_and_save):  ← Tortoise lifecycle 한 번
     │    ├─ search_candidates_in_open_db (pg_trgm + raw fallback)
     │    └─ ocr_drafts UPDATE (status, medicines, processed_at)
     └─ 실패 시 _persist_terminal (FAILED / NO_TEXT / NO_CANDIDATES)
```

#### main 페이지 동선 (사용자가 페이지 닫고 돌아왔을 때)

```
[프론트 /main]
   ├─ GET /ocr/drafts/active  (24h, consumed_at IS NULL)
   ├─ 활성 draft N건 → 우측하단 ActiveDraftsCard (챗봇 위, bottom-44)
   │     ├─ 각 항목: 좌측 휴지통 (DELETE /draft/{id}) + 우측 시각/상태/이동
   │     └─ 헤더 X (state 기반 임시 숨김, 새로고침 시 복귀)
   └─ 상단 "처방전 등록하기" / 빈 약 카드 등록 버튼
        └─ goToOcrFlow: 활성 draft 있으면 result 로, 없으면 /ocr
```

### 2.2 RAG 파이프라인

```
[사용자 메시지]
   ▼
[FastAPI message_service.ask_with_tools]
   ├─ route_intent_via_rq → ai-worker route_intent_job (Router LLM)
   │
   ├─ Router 응답 분기:
   │    text   → ask_and_reply 로 RAG 흐름
   │    tool_calls → _dispatch_tool_calls (eager + geo 분리)
   │
   └─ RAG 흐름 (ask_and_reply):
        ├─ intent classify (medication_info / drug_interaction / general_chat / ...)
        ├─ rewrite_query_via_rq (multi-turn → self-contained)
        ├─ embed_text_via_rq (768d ko-sroberta)
        ├─ HybridRetriever (pgvector cosine + pg_trgm keyword + 가중 합산)
        ├─ context build (상위 K 청크 + 사용자 프로필)
        └─ generate_chat_response_via_rq (gpt-4o-mini)

[messages 테이블 metadata]
   USER 측: intent / retrieval(score, names) / query_keywords
   ASSISTANT 측: llm(model, tokens) / intent
```

### 2.3 툴 콜링 (Phase Y — 위치 기반 callback)

```
[사용자] "내 위치 근처 약국 + 강남역 근처 병원"
   ▼
[FastAPI _dispatch_tool_calls]
   ├─ Router LLM tool_calls=[location, keyword]  (parallel_tool_calls=True)
   ├─ eager_calls = [keyword]  → 즉시 run_tool_calls_via_rq
   └─ geo_calls = [location]   → _park_pending_turn (PendingTurn 60s TTL)
        └─ 응답 202 + turn_id (좌표 없이 enqueue 안 함 — race condition 차단)

[프론트 ChatModal.handleGeolocationCallback]
   └─ navigator.geolocation.getCurrentPosition() ── 1번만
        └─ POST /messages/tool-result {turn_id, lat, lng}

[FastAPI resolve_pending_turn]
   ├─ _is_valid_coords(lat, lng) ── None/NaN/Inf/bool 거부
   ├─ pending.claim (atomic, 이미 처리됐으면 410)
   ├─ ownership 검증 (계정 mismatch 시 403)
   ├─ remaining_geo_calls 모두에 같은 좌표 inject
   ├─ run_tool_calls_via_rq (한 번 호출, 모든 geo 포함)
   │    └─ ai-worker run_tool_calls_job → asyncio.gather (병렬 실행)
   │         └─ _is_valid_geolocation 2차 안전망 + Kakao Local API
   └─ generate_chat_response_via_rq (2nd LLM)
```

**GPS 보장 사항**:
- 사용자 권한 요청 = **1회**
- 한 좌표를 모든 geo 툴이 공유
- Race condition 차단: location 의 RQ enqueue 는 callback 후에만

---

## 3. 코드 위치 매핑

### 3.1 OCR 도메인

| 책임 | 파일 |
|---|---|
| HTTP 라우터 (extract / draft / drafts/active / confirm / DELETE) | `app/apis/v1/ocr_routers.py` |
| Service (RQ enqueue + dedup + DB CRUD) | `app/services/ocr_service.py` |
| OcrDraft 모델 + status enum | `app/models/ocr_draft.py` |
| Repository (CRUD + ownership + 24h list) | `app/repositories/ocr_draft_repository.py` |
| 마이그레이션 (#14 ocr_drafts) | `app/db/migrations/models/14_*.py` |
| DTO (status / summary / poll response) | `app/dtos/ocr.py` |
| ai-worker RQ entry | `ai_worker/domains/ocr/jobs.py` |
| CLOVA OCR 호출 (bytes 입력) | `ai_worker/domains/ocr/text_extractor.py` |
| 텍스트 정규화 + 약품명 패턴 추출 | `ai_worker/domains/ocr/text_normalizer.py` |
| pg_trgm DB 매칭 + raw fallback | `ai_worker/domains/ocr/medicine_matcher.py` |
| 프론트 업로드 페이지 | `medication-frontend/src/app/ocr/page.jsx` |
| 프론트 로딩 (폴링 + STEPS + X 버튼) | `medication-frontend/src/app/ocr/loading/page.jsx` |
| 프론트 결과 검수 (← main, retake DELETE) | `medication-frontend/src/app/ocr/result/page.jsx` |
| 프론트 main 카드 | `medication-frontend/src/app/main/page.jsx` (`ActiveDraftsCard`) |

### 3.2 RAG 도메인

| 책임 | 파일 |
|---|---|
| Pipeline orchestrator | `app/services/rag/pipeline.py` |
| Intent classifier | `app/services/rag/intent/classifier.py` |
| Hybrid retriever (vector + keyword) | `app/services/rag/retrievers/hybrid.py` |
| RQ adapter (embedding) | `app/services/rag/providers/rq_embedding.py` |
| RQ adapter (LLM) | `app/services/rag/providers/rq_llm.py` |
| ai-worker RQ entry | `ai_worker/domains/rag/jobs.py` |
| Embedding (ko-sroberta singleton) | `ai_worker/domains/rag/embedding_provider.py` |
| Query rewriter | `ai_worker/domains/rag/query_rewriter.py` |
| Response generator | `ai_worker/domains/rag/response_generator.py` |
| Prompt builder (system/user) | `ai_worker/domains/rag/prompt_builder.py` |

### 3.3 Tool Calling 도메인 (Phase Y)

| 책임 | 파일 |
|---|---|
| Service dispatch (eager/geo 분리, pending) | `app/services/message_service.py` (`_dispatch_tool_calls`, `_park_pending_turn`, `resolve_pending_turn`) |
| RQ adapter (route + run_tool + 2nd LLM) | `app/services/tools/rq_adapters.py` |
| PendingTurn 저장소 (Redis 60s TTL) | `app/services/tools/pending.py` |
| 툴 분류 (needs_geolocation) | `app/services/tools/router.py` |
| Router LLM tool spec | `app/services/tools/schemas.py` |
| Kakao Local API 클라이언트 | `app/services/tools/maps/kakao_client.py` |
| 병원/약국 검색 함수 | `app/services/tools/maps/hospital_search.py` |
| ai-worker Router LLM | `ai_worker/domains/tool_calling/router_llm.py` |
| ai-worker RQ entry (route + run + dispatch) | `ai_worker/domains/tool_calling/jobs.py` |
| 좌표 검증 헬퍼 | `app/services/message_service.py::_is_valid_coords` + `ai_worker/domains/tool_calling/jobs.py::_is_valid_geolocation` |

### 3.4 Lifestyle 도메인

| 책임 | 파일 |
|---|---|
| Service (가이드 생성, 챌린지 추천) | `app/services/lifestyle_guide_service.py` |
| Prompt builder | `app/services/lifestyle_guide_prompt_builder.py` |
| Models | `app/models/lifestyle_guide.py`, `app/models/challenge.py` |
| 라우터 | `app/apis/v1/lifestyle_guide_routers.py`, `app/apis/v1/challenge_routers.py` |

### 3.5 인프라 (Redis / OpenAI / Logging)

| 책임 | 파일 |
|---|---|
| Producer redis client (FastAPI) | `app/core/redis_client.py` |
| Consumer redis client (ai-worker) | `ai_worker/core/redis_client.py` |
| RQ result publisher | `ai_worker/core/rq_result_publisher.py` |
| Redis retry 데코레이터 | `ai_worker/core/redis_retry.py` |
| AsyncOpenAI singleton (ai-worker) | `ai_worker/core/openai_client.py` |
| 텍스트 헬퍼 (코드펜스/토큰포맷/sanitize) | `ai_worker/core/text_helpers.py` |
| ai-worker supervision loop | `ai_worker/main.py` |

---

## 4. 완료된 일

### 4.1 마이그레이션
- ✅ #14 `ocr_drafts` 테이블 (id/profile_id/status/medicines/filename/image_hash/timestamps + partial 인덱스 2개)
- ✅ #13 cache 테이블 폐기 + medicine_chunk 정리
- ✅ #12 lifestyle_guides + daily_symptom_logs

### 4.2 OCR — 동기 → 비동기 + DB 영속
- ✅ FastAPI Producer (LLM 코드 제거, RQ enqueue, dedup, ownership)
- ✅ ai-worker Consumer (DB-only 결과 저장, Tortoise lifecycle)
- ✅ 프론트 폴링 + 스켈레톤 + 페이지 동선 (← main, retake DELETE)
- ✅ main 페이지 ActiveDraftsCard (위치 회피 bottom-44, 휴지통, X 닫기)
- ✅ 24h 보관 정책 + dedup (image_hash)

### 4.3 ai-worker 도메인 기반 리팩토링
- ✅ `utils/`, `providers/`, `tasks/` 폐기 → `domains/{ocr, rag, tool_calling, session_compact}/`
- ✅ `RAGGenerator` 클래스 (417줄) → 함수형 4모듈로 분해
- ✅ `core/` 신규 (openai_client / rq_result_publisher / text_helpers)
- ✅ supervision loop (TimeoutError 후 자동 재시작)
- ✅ Redis keepalive + retry (애플리케이션 레벨 보호)

### 4.4 보안 / 안정화
- ✅ `/ocr/*` 라우터 전역 인증 게이트
- ✅ DB connect timeout 5 → 10 (asyncpg pool 일시 부하 완화)
- ✅ 좌표 검증 (`_is_valid_coords` + `_is_valid_geolocation` 2중 안전망)

### 4.5 테스트 + 도메인 분리
- ✅ pytest 428 passed (Linux 컨테이너)
- ✅ 7개 테스트 파일 import 경로 갱신 (도메인 리팩토링 반영)
- ✅ 4개 기능 + OCR 시나리오 7개 모두 PASS

---

## 5. 해야할 일 (Follow-up) — 사용자 결정 작업 순서 반영

### 작업 1 (다음) — lifestyle 가이드 비동기화
- [ ] OCR 패턴 적용 (5~30초 동기 호출 → RQ + 폴링)
   - `LifestyleGuide` 모델에 `status` 컬럼 추가 (마이그레이션 #15)
   - `ai_worker/domains/lifestyle/jobs.py::generate_guide_job` 신규
   - `lifestyle_guide_service.generate_guide` 가 RQ enqueue 만, AsyncOpenAI 제거
   - 프론트 가이드 생성 페이지에 폴링 + 스켈레톤

### 작업 2 — medications Bulk DELETE 엔드포인트
- [ ] `POST /medications/bulk-delete` (body: `{ids: [uuid, ...]}`)
   - rate limit (30/60s) 회피 — 일괄 삭제 시 한 번의 요청
   - 프론트도 일괄 모드에서 새 endpoint 사용

### 작업 3 — DB 모델 정리 (한 PR 묶음)
- [ ] **`MedicineInfo.pack_unit` 길이 256 → 2048** — 긴 포장 단위 표기 데이터 손실 방지
- [ ] **`Medication.prescription_image_url` 컬럼 폐기** — 채우는 코드 0건 dead column
   - 마이그레이션 #16 (또는 #15·#16 분리, #15 가 lifestyle 이면 #17)

### 작업 4 이후 (우선순위 낮음, 백로그)
- [ ] **VectorDB 시드 보강** — `fetch_sample --limit 200` 또는 `sync_medicine_data` (Ctrl+C 안 함)
   - 현재 medicine_info 27건 / chunk ~179건으로 RAG 검색 hit 률 낮음
- [ ] **D-3 location 두 번째 호출 미스터리 추가 추적** — React StrictMode dev 모드 영향 확인
   - production 빌드에서 재현 안 되면 dev only 이슈로 정리
- [ ] **`message_service.py` 큰 함수 분해** — `ask_and_reply` (92줄), `ask_with_tools` (73줄), `resolve_pending_turn` (84줄, 본문은 49줄로 양호)
- [ ] **OCR 24h 정리 cron** — `ocr_drafts` 의 24h 경과 row 자동 삭제 (apscheduler)
- [ ] **DB connection pool 상향 검토** — maxsize 10 → 20, 또는 retry on timeout
- [ ] **`/ocr/draft/{id}` ownership 검증 강화** — 현재는 profile_id 단순 비교 (UUID brute force 어려움)
- [ ] **main PR 진행** — origin/main 통합 (누적 commit 정리 + push + GitHub PR)

---

## 6. 알려진 제약·결정사항

| 제약 | 결정 |
|---|---|
| `MUTATION_MAX_REQUESTS = 30/60s` | 유지 (사용자 선택). 일괄 DELETE 시 사용자가 분할 처리 |
| OpenCV 전처리 | 폐기 (CLOVA OCR 자체 전처리에 위임). text_normalizer 는 유지 |
| 처방전 이미지 영구 저장 | 안 함 (개인정보 부담, OCR 후 즉시 폐기) |
| OCR 24h 보관 | DB-only (Redis 아님 — list/dedup/ownership 효율) |
| GPS 호출 | 1회만, 좌표 공유, asyncio.gather 병렬 실행 |
| Race condition (좌표 없이 location enqueue) | 코드 path 자체 없음 (callback 후에만 enqueue) |

---

## 7. 검증 통계 (이번 통합 검증)

- **변경 파일**: 약 30개 (OCR 비동기 + lifestyle 머지 + 도메인 리팩토링 누적)
- **신규 commit**: ~15개 (작업 단위별 분리)
- **신규 마이그레이션**: 1개 (#14)
- **신규 신규 모듈**: 12개 (`ocr_draft.py`, repo, jobs, ActiveDraftsCard 등)
- **dead code 제거**: `service.py`, `utils/chunker.py`, `utils/ocr.py`, `data/medicines.json`, `image_preprocessor.py`
- **pytest**: 428 passed, 3 skipped, 0 failed (컨테이너 회귀)
- **Ruff**: 180 files all PASS

---

## 8. 다음 작업 권장 순서

1. **commit 누적 정리** (현재 unstaged: `app/services/message_service.py`, `ai_worker/domains/tool_calling/jobs.py`, `app/core/config.py`)
2. **lifestyle 비동기화** (OCR 패턴 적용, 1~2 PR)
3. **VectorDB 시드 보강** (시간 있을 때, 5~15분)
4. **main PR 진행** (origin/main 통합 — 누적 commit 정리 + 검증 + push)
5. (옵션) production 배포 + 모니터링
