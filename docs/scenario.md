# Phase Y Tool Calling — UI 수동 테스트 시나리오

> **목적**: Phase Y (Router LLM 기반 병원·약국 툴콜링) 가 실제 사용자 입력부터
> FE 렌더링까지 end-to-end 로 정상 동작하는지 수동 검증. 자동화 테스트 (426건)
> 가 커버하는 계약 레벨 위에, **실제 LLM 응답 / Kakao 실 데이터 / 브라우저
> GPS 권한 모달** 까지 포함한 통합 시나리오를 돌려본다.

> **일시**: \_\_\_\_-\_\_-\_\_ / **검증자**: \_\_\_\_\_\_\_\_\_\_ / **환경**: local docker compose

---

## 0. 사전 조건

### 0.1 서버 기동
```powershell
docker compose up -d
docker ps --format "table {{.Names}}\t{{.Status}}"
```
모든 컨테이너가 `(healthy)` 상태여야 함.

### 0.2 환경 변수
`.env` / `envs/.env` 에 아래 값 존재 확인:
- `OPENAI_API_KEY` — Router LLM + 2nd LLM 호출용
- `KAKAO_CLIENT_ID` — Kakao Local API REST 키
- `REDIS_URL`, `DATABASE_URL` 기존 설정

### 0.3 마이그레이션
```powershell
docker exec fastapi uv run --no-sync aerich heads
```
→ `No available heads` (RAG #8 까지 적용됨) 이어야 함.

### 0.4 개발자 로그인
- 접속: http://localhost:3000/
- 카카오 로그인 또는 dev 계정으로 진입
- 채팅 세션 하나 생성하거나 기존 세션 선택

### 0.5 실시간 로그 모니터링
별도 터미널 2개에서:
```powershell
docker logs fastapi -f
docker logs ai-worker -f
```

---

## 1. 대상 파일 · 기능 매핑

| 계층 | 파일 | 역할 |
|---|---|---|
| **Router (app)** | `app/apis/v1/message_routers.py` | `/messages/ask`, `/messages/tool-result` 엔드포인트 |
| **Service (app)** | `app/services/message_service.py` | `ask_with_tools` / `resolve_pending_turn` 3분기 |
| **Service (app)** | `app/services/tools/rq_adapters.py` | AI-Worker RQ job 위임 어댑터 |
| **Service (app)** | `app/services/tools/pending.py` | PendingTurn Redis 저장소 |
| **Service (app)** | `app/services/tools/router.py` | Router LLM 응답 파서 |
| **Tool (app)** | `app/services/tools/maps/kakao_client.py` | Kakao Local API 클라이언트 |
| **Tool (app)** | `app/services/tools/maps/hospital_search.py` | 병원/약국 두 검색 진입점 |
| **Worker** | `ai_worker/tasks/tool_tasks.py` | `route_intent_job` / `run_tool_calls_job` |
| **Worker** | `ai_worker/providers/router.py` | Router LLM 실제 호출 (OpenAI) |
| **FE** | `medication-frontend` (Next.js) | 200/202 분기 UI, GPS 권한 모달 |

---

## 2. 시나리오 목록

| # | 분류 | 입력 | 기대 HTTP | 기대 분기 |
|---|---|---|---|---|
| S-1 | keyword-only | `"강남역 약국"` | 200 | Router → tool_calls (keyword) → 즉시 2nd LLM |
| S-2 | location (allow) | `"내 주변 약국 알려줘"` + GPS 허용 | 202 → 200 | Router → pending → GPS → run_tool_calls → 2nd LLM |
| S-3 | location (deny) | `"내 주변 약국 알려줘"` + GPS 거부 | 202 → 200 | Router → pending → denied → 2nd LLM with error payload |
| S-4 | RAG 폴백 | `"활명수 효능 알려줘"` | 200 | Router → text → `ask_and_reply` (RAG) |
| S-5 | out_of_scope | `"오늘 날씨 어때"` | 200 | Router → text → RAG → out_of_scope 응답 |
| S-6 | mix | `"강남역 약국이랑 내 주변 병원 알려줘"` | 202 → 200 | keyword 즉시 실행, location 은 pending |
| S-7 | 병렬 keyword | `"강남역 약국이랑 역삼동 약국"` | 200 | 두 keyword 병행 실행 |
| S-8 | 만료 콜백 | S-2 에서 60초+ 대기 후 권한 응답 | 202 → 410 | PendingTurn TTL 만료 |
| S-9 | 재생성 | 만료 후 같은 질문 재입력 | 200 또는 202 | 새 turn_id 로 정상 흐름 |
| S-10 | 미로그인 | 토큰 없이 `/ask` 호출 | 401 | 인증 미들웨어 차단 |

---

## 3. 시나리오 상세

### S-1: Keyword 단독 검색

**목적**: Router LLM 이 keyword 툴을 인식하고, 좌표 없이 즉시 카카오 호출 + 2nd LLM 을 한 HTTP 요청 안에 끝내는지 확인.

**입력**
```
"강남역 약국"
```

**기대 HTTP 응답**: `200 OK`
```json
{
  "user_message": { "content": "강남역 약국", ... },
  "assistant_message": { "content": "강남역 근처 약국은 ..." }
}
```

**기대 로그 (fastapi)**
```
[ToolCalling] enqueue route_intent_job messages=N
[ToolCalling] route kind=tool_calls calls=1
[ToolCalling] enqueue run_tool_calls_job calls=1
[ToolCalling] enqueue generate_chat_response_job messages=N
```

**기대 로그 (ai-worker)**
```
[ToolCalling] route_intent_job start messages=N
[ToolCalling] router LLM response tool_calls=1 tokens=...
[ToolCalling] route_intent_job done tool_calls=1 names=search_hospitals_by_keyword
[ToolCalling] run_tool_calls_job start calls=1 names=search_hospitals_by_keyword
[ToolCalling] Kakao Local search hit=N query='강남역 약국'
[ToolCalling] run_tool_calls_job done ok=1 errors=0
```

**기대 UI 동작**
- 메시지 전송 직후 assistant 메시지 영역에 스켈레톤 / 로딩 인디케이터
- 2~4초 후 약국 목록이 포함된 자연어 답변 렌더링
- GPS 권한 모달 뜨지 않아야 함

**실제 결과**
- [ ] HTTP: \_\_\_
- [ ] 응답 시간: \_\_\_ 초
- [ ] 답변에 약국 이름이 실제로 포함: Y / N
- [ ] 비고:

---

### S-2: 위치 기반 검색 (권한 허용)

**목적**: 202 pending → GPS 허용 → `/tool-result` 로 좌표 전달 → 카카오 호출 → 2nd LLM 전체 플로우 검증.

**입력**
```
"내 주변 약국 알려줘"
```

**사전**: 브라우저에서 `localhost` 의 위치 권한이 **"차단"** 상태면 설정에서 "요청 시 묻기" 로 리셋.

**기대 HTTP (1차)**: `202 Accepted`
```json
{
  "user_message": { "content": "내 주변 약국 알려줘", ... },
  "action": "request_geolocation",
  "turn_id": "uuid-...",
  "session_id": "uuid-...",
  "ttl_sec": 60
}
```

**기대 UI 동작 (1차 직후)**
- 브라우저 기본 위치 권한 모달 자동 노출
- (선택 UI 가 있다면) "근처 검색 준비 중" 스피너

**사용자 액션**: 브라우저 모달에서 **"허용"** 클릭

**기대 HTTP (2차)**: `POST /messages/tool-result` → `200 OK`
```json
{
  "assistant_message": { "content": "현재 위치 근처 약국으로는 ..." }
}
```

**기대 로그 (fastapi)**
```
[ToolCalling] route kind=tool_calls calls=1
[ToolCalling] pending turn=<uuid> eager=0 geo=1
[ToolCalling] pending store create turn=<uuid> ttl=60s
--- (GPS 콜백 수신) ---
[ToolCalling] enqueue run_tool_calls_job calls=1
[ToolCalling] enqueue generate_chat_response_job messages=N
[ToolCalling] resolved turn=<uuid> status=ok
```

**기대 로그 (ai-worker)**
```
[ToolCalling] run_tool_calls_job start calls=1 names=search_hospitals_by_location
[ToolCalling] Kakao Local search hit=N query='약국'   # 내부 query 는 카테고리 라벨
[ToolCalling] run_tool_calls_job done ok=1 errors=0
```

**실제 결과**
- [ ] 1차 HTTP: \_\_\_ (202 기대)
- [ ] 권한 모달 노출: Y / N
- [ ] 2차 HTTP: \_\_\_ (200 기대)
- [ ] 답변에 실제 주소 근처 약국명 포함: Y / N
- [ ] 1차~2차 총 소요 시간: \_\_\_ 초
- [ ] 비고:

---

### S-3: 위치 기반 검색 (권한 거부)

**목적**: GPS 거부 시 denial payload 가 2nd LLM 에 전달돼 "지역 이름으로 알려주세요" 류의 자연어 안내가 나오는지 확인.

**입력**: S-2 와 동일 (`"내 주변 약국 알려줘"`)

**사용자 액션**: 브라우저 모달에서 **"차단"** 클릭

**기대 HTTP (2차)**: `POST /messages/tool-result` with `{ status: "denied" }` → `200 OK`

**기대 답변 예시**
> "위치 정보에 접근할 수 없어서요. 검색하실 지역 이름(예: 강남역, 역삼동) 을 알려주시면 찾아드릴게요!"

**기대 로그 — 중요**
- `run_tool_calls_job` **호출되지 않아야 함** (denied 분기는 tool 실행 skip)
- `[ToolCalling] enqueue generate_chat_response_job` 만 나와야 함

**실제 결과**
- [ ] 2차 HTTP: \_\_\_
- [ ] 답변이 지역 재입력을 유도: Y / N
- [ ] ai-worker 로그에 `run_tool_calls_job start` 없음 확인: Y / N
- [ ] 비고:

---

### S-4: RAG 폴백 (약 정보 질의)

**목적**: Router LLM 이 툴 호출 없이 자연어로 응답해야 할 쿼리 (약학 지식) 에서 `ask_and_reply` 경로가 제대로 타는지 확인.

**입력**
```
"활명수 효능 알려줘"
```

**기대 HTTP**: `200 OK`

**기대 로그**
```
[ToolCalling] route kind=text calls=0
--- (이후는 RAG 파이프라인 로그) ---
[RAG] intent=...
[RAG] path=retrieve+llm
[RAG] retrieved=N
```

**기대 답변**: 활명수에 대한 효능 설명. RAG DB 에 샘플 약품 데이터가 있으면 더 구체적인 답. 없으면 일반 답변 + 전문가 상담 권유.

**실제 결과**
- [ ] HTTP: \_\_\_
- [ ] 답변에 활명수 효능 언급: Y / N
- [ ] 툴콜링 로그 없이 RAG 로그만 찍힘 확인: Y / N
- [ ] 비고:

---

### S-5: Out-of-scope

**목적**: Router LLM 이 의료 무관 질의를 판별하고 RAG 쪽 out_of_scope 분기로 빠지는지 확인.

**입력**
```
"오늘 날씨 어때"
```

**기대 HTTP**: `200 OK`

**기대 답변**: 의료·복약 외 질문은 답변하지 않는다는 안내 (Dayak 페르소나).

**기대 로그**
```
[ToolCalling] route kind=text calls=0
[RAG] intent=out_of_scope
[RAG] path=out_of_scope
```

**실제 결과**
- [ ] HTTP: \_\_\_
- [ ] 답변 톤이 out_of_scope 안내 맞음: Y / N
- [ ] 비고:

---

### S-6: 혼합 (keyword + location)

**목적**: LLM 이 parallel_tool_calls=True 로 두 툴을 동시 호출했을 때, keyword 는 즉시 실행하고 location 만 pending 처리하는 mix 분기 검증.

**입력**
```
"강남역 약국이랑 내 주변 병원 알려줘"
```

**기대 HTTP (1차)**: `202 Accepted`

**기대 로그 (fastapi, 1차)**
```
[ToolCalling] route kind=tool_calls calls=2
[ToolCalling] enqueue run_tool_calls_job calls=1       # keyword 만 즉시 실행
[ToolCalling] pending turn=<uuid> eager=1 geo=1         # keyword 결과 eager, location pending
```

**GPS 허용 후 기대 로그 (fastapi, 2차)**
```
[ToolCalling] enqueue run_tool_calls_job calls=1       # location 만 추가 실행
[ToolCalling] enqueue generate_chat_response_job messages=N
[ToolCalling] resolved turn=<uuid> status=ok
```

**기대 답변**: 강남역 약국 목록 + 내 주변 병원 목록이 한 답변에 자연스럽게 묶여 등장.

**실제 결과**
- [ ] 1차 HTTP: \_\_\_
- [ ] 1차 로그에 `eager=1 geo=1` 확인: Y / N
- [ ] 2차 HTTP: \_\_\_
- [ ] 답변에 강남역 약국 + 내 주변 병원 둘 다 언급: Y / N
- [ ] 비고:

---

### S-7: 병렬 keyword 두 개

**목적**: 좌표 불필요한 키워드 2개를 한 번에 묶어서 `asyncio.gather` 로 병행 처리되는지 확인. pending 분기 없이 200 한 번에 완료.

**입력**
```
"강남역 약국이랑 역삼동 약국 알려줘"
```

**기대 HTTP**: `200 OK` (202 없이 바로 200)

**기대 로그**
```
[ToolCalling] route kind=tool_calls calls=2
[ToolCalling] enqueue run_tool_calls_job calls=2
[ToolCalling] run_tool_calls_job start calls=2 names=search_hospitals_by_keyword,search_hospitals_by_keyword
[ToolCalling] Kakao Local search hit=N query='강남역 약국'
[ToolCalling] Kakao Local search hit=N query='역삼동 약국'
[ToolCalling] run_tool_calls_job done ok=2 errors=0
```

두 Kakao 호출 로그가 **거의 동시에** 찍혀야 함 (병렬 처리 증거).

**실제 결과**
- [ ] HTTP: \_\_\_
- [ ] Kakao 호출 2건 로그 시간차: \_\_\_ ms
- [ ] 답변에 두 지역 모두 등장: Y / N
- [ ] 비고:

---

### S-8: Pending 만료

**목적**: 60초 TTL 후 콜백 도달 시 410 Gone 반환 확인.

**절차**
1. S-2 와 동일하게 `"내 주변 약국 알려줘"` 전송 → 202 수신
2. 브라우저 권한 모달 **즉시 답하지 않고 60초 이상 대기**
3. 이후 "허용" 클릭

**기대 HTTP (2차)**: `410 Gone`
```json
{ "detail": "Pending turn not found or expired." }
```

**기대 로그**
```
[ToolCalling] pending store claim miss turn=<uuid> (expired or unknown)
```

**기대 UI**: "시간이 지났어요, 다시 물어봐주세요" 류 안내 메시지 노출 (FE 가 410 을 잡아 처리).

**실제 결과**
- [ ] 2차 HTTP: \_\_\_
- [ ] FE 에서 사용자에게 재시도 안내: Y / N
- [ ] 비고:

---

### S-9: 만료 후 재시도

**목적**: 만료된 turn_id 로 사용할 수 없는 상황에서 사용자가 같은 질문 재입력 시 새 turn_id 로 정상 흐름이 되는지 확인.

**절차**: S-8 완료 직후 같은 질문 다시 전송

**기대 HTTP (1차)**: `202 Accepted` (새로운 turn_id)

**기대**: S-2 와 동일한 성공 플로우 반복 가능.

**실제 결과**
- [ ] 새 turn_id 발급됨: Y / N
- [ ] 정상 완료: Y / N
- [ ] 비고:

---

### S-10: 미인증 요청

**목적**: 보안 — Access Token 없이 `/messages/ask` 호출 차단 확인.

**절차**: Postman 이나 curl 로 Authorization 헤더 없이 호출

```bash
curl -X POST http://localhost/api/v1/messages/ask \
  -H "Content-Type: application/json" \
  -d '{"session_id": "00000000-0000-0000-0000-000000000000", "content": "test"}'
```

**기대 HTTP**: `401 Unauthorized`

**실제 결과**
- [ ] HTTP: \_\_\_
- [ ] 비고:

---

## 4. 에러 복원력 관찰 (참고용 — 수동 유발 어려움)

다음 케이스는 자동 테스트 (`test_message_service_tool_branching.py` 등) 로 이미 커버되며, UI 상에서 인위 유발이 어렵지만 **운영 중 만나면 로그로 확인** 할 것:

- **Kakao API 5xx**: 로그에 `[ToolCalling] Kakao API 5XX (attempt 1/2); retrying` 이후 `exhausted retries` 면 답변에 "일부 실패" 안내 포함
- **OpenAI timeout**: `ToolTimeoutError` → 503 + `[ToolCalling] RQ job timeout after 30.0s`
- **ai-worker 다운**: FastAPI 가 폴링하다 timeout 으로 503 변환

---

## 5. 체크리스트 (머지 전)

- [ ] S-1 ~ S-7 모두 **기대 HTTP 상태코드** 일치
- [ ] S-1 ~ S-7 모두 **기대 답변 의미** 맞음 (자연어 답변 내용은 LLM 출력이라 100% 동일할 순 없음, 의미 일치만 확인)
- [ ] S-8 만료 동작 확인
- [ ] S-10 인증 차단 확인
- [ ] 로그에 PII (lat/lng 원본, 토큰, 원문 message payload) **노출 안 됨** 재확인
- [ ] 브라우저 콘솔 에러 0건
- [ ] Ruff / pytest 기존 통과 상태 유지

---

## 6. 이슈 기록

테스트 중 발견한 문제는 아래 표에 기록:

| 시나리오 | 증상 | 예상 원인 | 대응 |
|---|---|---|---|
|   |   |   |   |
|   |   |   |   |

---

## 7. 테스트 종료 후

- 모든 시나리오 통과 시: `feature/RAG` 로 머지 진행
- 하나라도 실패 시: 원인 디버깅 후 재테스트. 필요 시 hotfix 커밋 후 다시 전체 시나리오.
