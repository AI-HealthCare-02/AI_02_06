# QA Audit To-Do (Missing Links)

본 문서는 “기본 구현 완료” 이후에 숨어있는 **끊어진 연결(Missing Link)**, **더미/하드코딩 로직**, **통합 단절**, **트랜잭션 빈틈**을 빠르게 메워서 프로덕션 품질로 끌어올리기 위한 우선순위 작업 목록입니다.

스캔 범위: FastAPI 라우터(`app/apis/v1/*`), 서비스(`app/services/*`), Tortoise 모델(`app/models/*`), AI 워커(`ai_worker/*`)

---

## 1. 치명적 결함(당장 해야 할 것)

| 우선순위 | 관점 | 이슈 | 근거(파일) | 리스크 | To‑Do(액션) |
|---:|---|---|---|---|---|
| P0 | Integration Gap | **OCR: 동기식 `requests` + 동기식 OpenAI 호출이 요청 처리(이벤트 루프)를 블로킹** | `app/services/ocr_service.py` | 동시성 급락, 타임아웃/장애 전파 | (1) `httpx.AsyncClient`로 OCR 호출 async화 또는 (2) 큐(RQ/Celery 등)로 비동기 작업화하고 `job_id` 폴링/웹훅 제공 |
| P0 | Integration Gap | **채팅: `ask_and_reply()`에서 RAG(OpenAI)가 동기 호출 + `except Exception`로 실패를 성공처럼 덮음** | `app/services/message_service.py`, `ai_worker/utils/rag.py` | 장애시 원인 미노출, UX 악화, 이벤트 루프 블로킹 | OpenAI 호출을 async/백그라운드화, 실패 시 `HTTPException`(예: 503/502)로 명확히 전달 + 재시도 전략 정의 |
| P0 | 보안/성능 | **OCR 업로드 파일명(`UploadFile.filename`)을 경로에 그대로 결합** | `app/services/ocr_service.py` | Path traversal 가능성 | `Path(file.filename).name`으로 basename만 사용(또는 허용 문자 whitelist) + 확장자 제한 |
| P0 | 비즈니스 로직 누락 | **계정 생성 후 프로필 생성이 분리되어 원자성 부족(부분 성공 상태 가능)** | `app/services/oauth.py` (`dev_test_login`) | 더티 데이터/유령 계정 | `in_transaction()`로 account+profile을 atomic 처리, 실패 시 롤백/정리(또는 idempotency 키) |

---

## 2. 미구현 기능(빈 껍데기)

| 우선순위 | 관점 | 이슈 | 근거(파일) | 영향 | To‑Do(액션) |
|---:|---|---|---|---|---|
| P1 | Dummy Endpoint | **Readiness `/health/ready`가 TODO 상태로 항상 ready 반환** | `app/apis/v1/health_routers.py` | 오토스케일/배포 시 장애 감지 실패 | DB(Tortoise) + Redis ping 체크를 포함한 readiness 구현, 실패 시 503 |
| P1 | Dummy Logic | **약물 상호작용 체크가 “DUR API Mock” 하드코딩 결과를 저장/반환** | `app/services/medication_service.py` | 핵심 기능 신뢰도 하락 | 실제 DUR API(또는 AI 분석) 연동/스펙 정의, 실패 시 fallback 정책/에러코드 정의 |
| P1 | Dummy Worker | **AI 워커가 ‘Phase 4 TODO’로 태스크를 실제 처리하지 않음** | `ai_worker/main.py` | “비동기 처리” 설계가 실체 없음 | 큐/워커(RQ 등) 실제 구현, 최소 1개 OCR/LLM 작업을 워커로 이동해 end-to-end 연결 |
| P1 | Orphaned Model | **`UserChallenge` 모델이 정의돼 있으나 CRUD 연결이 불명확** | `app/models/challenge.py` | 기능 확장 시 레거시/잉여 테이블 | 실제 요구사항에 맞춰 라우터/서비스/레포지토리로 CRUD 연결 또는 모델 제거/마이그레이션 정리 |
| P1 | Orphaned Model | **`LLMResponseCache` 모델이 정의돼 있으나 사용처가 없음** | `app/models/llm_response_cache.py` | 비용 최적화 기능 미구현 | 캐시 키(프롬프트 해시) 정의, read-through cache 구현(서비스 레벨) + 만료/통계(hits) 업데이트 |

---

## 3. 성능/보안 개선점

| 우선순위 | 관점 | 개선 포인트 | 근거(파일) | 리스크 | To‑Do(액션) |
|---:|---|---|---|---|---|
| P2 | Integration Gap | **장시간 작업의 에러 메시지 표준화 부족(400/500 구분, 사용자 안내)** | OCR/채팅 서비스 전반 | 장애 시 UX 혼란 | 공통 에러 포맷 `{error, error_description, correlation_id}` 정의 + 라우터에서 명확한 status code로 매핑 |
| P2 | 성능 | **외부 호출 timeout/재시도/서킷브레이커 정책이 서비스별로 불균일** | `ocr_service.py`, RAG | 장애 전파 | 타임아웃/재시도 정책 표준화(지수 백오프), 관측(로그/메트릭) 추가 |
| P2 | 데이터 무결성 | **멀티 스텝 워크플로우에 보상(Compensation)/정리 로직 점검 필요** | OCR 업로드/DB write 흐름 | 잔여 파일/레코드 누적 | “중간 실패 시 정리” 체크리스트 작성 후 주요 플로우별 검증(이미지/캐시/토큰) |

---

## 빠른 점검 체크리스트(추천)

- [ ] OCR/챗/상호작용 등 “AI/외부 API” 호출이 라우터 요청-응답 경로에서 블로킹하지 않는가?
- [ ] 실패 시 **정확한 HTTP 코드(400/401/403/409/422/500/502/503)**와 사용자 안내가 내려가는가?
- [ ] 파일/이미지 저장이 있다면 경로/확장자/크기 제한과 실패 시 정리가 보장되는가?
- [ ] 2개 이상 DB 쓰기가 한 작업에 묶이면 `transaction`이 적용되는가?

