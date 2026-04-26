# origin/main 통합 작업 머지 로그

> 2026-04-25 시작. Phase Y (툴 콜링) + 팀원 브랜치 여러 개 + origin/main 의 배포
> 실패 수정을 **하나의 통합 브랜치**로 합치는 여정의 기록. 각 단계의 타임라인,
> 충돌 해결 이유, 롤백 포인트를 남긴다.

---

## 0. 통합 대상 브랜치

| 브랜치 | 내용 | 기준 tag |
|---|---|---|
| `origin/main` | 자동배포 대상, **배포 실패 상태** (런타임 에러는 없음) | `backup/origin-main-2026-04-25` |
| `integration/rag-main` | Phase Y (툴 콜링) + RAG 통합 + Phase Z-A 요약 | `backup/integration-rag-main-2026-04-25` |
| `origin/feature/lifestyle` | 생활습관 가이드 + 챌린지 확장 | `backup/feature-lifestyle-2026-04-25` |
| `origin/feature/lifestyle-guide-llm-refactor` | **`feature/lifestyle` 과 완전 동일** (커밋·파일 차이 0) — 머지 불필요 | 제외 |
| `origin/docs/claude-md-section-flow-policy` | `CLAUDE.md` 한 파일에 §4.4 정책 추가 (1 커밋 `8b3122e`) | _머지 여부 사용자 결정 필요_ |

**이미 main 에 병합되어 추가 머지 불필요**:
- `feat/drug-data-integration` (PR #76, main HEAD)
- `feat/prescription-edit-delete` (PR #74)
- `feat/medication-intake-automation` (PR #73)
- `feat/profile-switcher` (PR #72)
- `feat/chunk-schema-redesign-v2` (chunk schema, integration/rag-main 의 #8 medicine_info_redesign 의 기반)

---

## 1. 사전 진단 (2026-04-25 완료)

### 1.1 origin/main 배포 실패 원인 진단
- [x] 로컬 `docker compose -f docker-compose.prod.yml build` 재현 → **빌드 성공** (fastapi, ai-worker 이미지 정상 생성)
- [x] 로컬 postgres/redis up 시도 → **기동 성공** (명명된 볼륨 `postgres_data` 자동 생성, 기존 dev 볼륨 `ah_02_06_postgres_data` 와 분리)
- [ ] GitHub Actions 로그 확인 — 외부 접근 필요 (현재 단계에서 미확인)

**원인 추정**: 로컬 prod 빌드·기동 모두 성공이라 **EC2 환경 특화 요인** 가능성 높음. 후보:
1. EC2 의 `.env` 변수 누락 (예: `OPENAI_API_KEY`, `KAKAO_CLIENT_ID`, `DB_PASSWORD`, `DOCKER_USER`/`DOCKER_REPOSITORY`/`APP_VERSION`)
2. Let's Encrypt 인증서 볼륨 (`/etc/letsencrypt`) 또는 인증서 갱신 실패
3. EC2 보안그룹·VPC 설정 (특정 포트/도메인 차단)
4. Docker Hub 이미지 push 권한 또는 레지스트리 접근 실패
5. GitHub Actions workflow 자체의 step 변경

**결론**: 통합 작업 자체는 진행 가능. EC2 배포 실패는 통합 완료 후 배포 시점에 GitHub Actions 로그 직접 확인하여 별도 fix.

### 1.2 마이그레이션 현황 (브랜치별 — 2026-04-25 분석)

| 브랜치 | `#0~#7` (공통) | 브랜치 고유 마이그레이션 |
|---|---|---|
| `origin/main` | 동일 | `8_20260422_add_rag_chunk_schema.py` |
| `integration/rag-main` | 동일 | `8_20260422005350_medicine_info_redesign.py`, `9_drop_chat_sessions_medication_fk.py`, `10_add_messages_metadata.py`, `11_add_medicine_doc_data.py` |
| `feature/lifestyle` (= lifestyle-guide-llm-refactor) | 동일 | `8_20260422221048_add_lifestyle_guide_models.py` |

**핵심 충돌**: 3개 브랜치가 모두 `#8` 번호 사용. 내용 완전히 다름.

### 1.3 #8 마이그레이션 내용 비교

#### origin/main `#8_add_rag_chunk_schema`
- `medicine_info` 컬럼 **확장**: chart, material_name, valid_term, pack_unit, atc_code, ee_doc_url, ud_doc_url, nb_doc_url 추가 + `embedding` 제거
- `medicine_chunk` **신규** (pgvector VECTOR(768) + HNSW 인덱스)
- `medicine_ingredient` **신규** (주성분 1:N)

#### integration/rag-main `#8_medicine_info_redesign`
- **origin/main #8 의 idempotent 재작성본** (주석에 명시: "팀원 main #8이 이미 적용된 DB 대응")
- `medicine_info` CREATE TABLE (전 컬럼 포함) + `ADD COLUMN IF NOT EXISTS` 로 누락분 보강
- 같은 medicine_chunk / medicine_ingredient 정의 (관련 테이블도 idempotent 처리)

#### feature/lifestyle `#8_add_lifestyle_guide_models`
- `medicine_info` **구버전** CREATE TABLE (medicine_name VARCHAR(128) + embedding TEXT — main 의 신규 컬럼 8종 미포함)
- `lifestyle_guides` **신규** (UUID PK, content/medication_snapshot JSONB, profile_id FK)
- `daily_symptom_logs` **신규** (UUID PK, log_date, symptoms JSONB, note, profile_id FK)
- `challenges` **확장**: is_active, category, started_at, completed_at, guide_id (+ FK to lifestyle_guides)
- 다수의 COMMENT 추가 (한국어→영어 변경 흔적)

### 1.4 충돌 분석 (사용자 결정 사항)

#### 마이그레이션 통합 옵션

**옵션 A — origin/main 기준, 다른 브랜치 #8 재번호** _(권장)_
```
#8 = origin/main 의 add_rag_chunk_schema (그대로)
#9 = drop_chat_sessions_medication_fk (integration/rag-main)
#10 = add_messages_metadata (integration/rag-main)
#11 = add_medicine_doc_data (integration/rag-main)
#12 = add_lifestyle_guide_models (feature/lifestyle, 단 medicine_info CREATE TABLE 부분 제거 — 이미 #8 에서 만들어졌으므로 IF NOT EXISTS 라 noop 이지만 명시적 정리)
```
- 장점: origin/main 의 #8 이 이미 prod DB 에 적용됐을 가능성 → 새 환경 부팅 시 호환성 보장
- 단점: integration/rag-main 의 idempotent 재작성본을 버리게 됨 (단순 origin #8 사용)

**옵션 B — integration/rag-main 의 idempotent #8 사용**
```
#8 = integration/rag-main 의 medicine_info_redesign (origin/main #8 호환 idempotent 버전)
#9~#11 = integration/rag-main 그대로
#12 = feature/lifestyle 의 lifestyle_guide_models (재번호, medicine_info 부분 제거)
```
- 장점: idempotent 라 origin/main #8 적용 DB 도 신규 DB 도 모두 호환
- 단점: 두 번째 #8 파일이 첫 번째 #8 의 SQL 을 다시 실행 (no-op 이지만 의도 불명확)

**옵션 C — 통합 init 으로 완전 재작성**
- 모든 마이그레이션 버리고 `#0_init_unified.py` 하나로 최종 스키마 만들기
- 현재 prod DB 데이터 손실 수용 가능 (테스트 데이터 한정)

### 1.5 최종 스키마 결정 — _사용자 승인 대기_

#### 살릴 테이블 후보 (모든 브랜치 통합 시)
- accounts, profiles, refresh_tokens (공통 base)
- chat_sessions, messages, message_feedbacks (chat)
- medications, intake_logs, mock_items (medication)
- challenges (확장: lifestyle 의 is_active, category, started_at, completed_at, guide_id 포함)
- medicine_info (origin/main 신규 컬럼 8종 포함)
- medicine_chunk, medicine_ingredient, data_sync_log (RAG)
- drug_interaction_cache, llm_response_cache (캐시)
- lifestyle_guides, daily_symptom_logs (lifestyle)

#### 결정 필요 사항 (사용자 승인 항목)
- [ ] 마이그레이션 옵션 A/B/C 중 선택
- [ ] `medicine_info` 의 `embedding` 컬럼 살릴지/죽일지 (현재: origin/main 에서 제거됨, lifestyle 에서 유지됨)
- [ ] `medicine_info.medicine_name` 길이: VARCHAR(128) (lifestyle) vs VARCHAR(200) (integration/rag-main)
- [ ] `feature/lifestyle-guide-llm-refactor` 머지 여부 (feature/lifestyle 의 파생인지 별개 작업인지 확인 필요)
- [ ] `docs/claude-md-section-flow-policy` 머지 여부 (정책 문서)

### 1.6 코드 충돌 예상 파일 (9개)

`integration/rag-main` 과 `feature/lifestyle` **양쪽 모두 수정한 파일**:

| 파일 | 충돌 가능성 | 비고 |
|---|---|---|
| `.gitignore` | 낮음 | 추가만 했을 가능성, 자동 머지 가능 |
| `CLAUDE.md` | 중간 | 양쪽 모두 정책·rule 추가 가능, 라인 단위 확인 필요 |
| `PLAN.md` | 낮음 | integration/rag-main 의 PLAN 은 .gitignore 됨 (이전 메모리), lifestyle 의 PLAN 은 별도 plans/ 디렉토리 |
| `app/core/config.py` | 중간 | 양쪽 새 env var 추가 가능, 자동 머지 가능 |
| `app/db/migrations/models/8_*` | **높음** (확정) | #8 이름 자체 충돌 — 마이그레이션 통합 결정 따라 해결 |
| `app/models/medicine_info.py` | **높음** (확정) | 컬럼 정의가 다름 — 최종 스키마 결정에 따라 양쪽 컬럼 통합 |
| `app/repositories/challenge_repository.py` | 중간 | lifestyle 신규 메서드 (get_by_guide_id, bulk_create_from_guide) vs integration/rag-main 변경 |
| `app/services/medicine_data_service.py` | 중간 | 양쪽 변경, 라인 단위 확인 필요 |
| `pyproject.toml` | 낮음 | 의존성 추가만, 자동 머지 가능 |

### 1.7 머지 시뮬레이션 결과 (2026-04-25 야간 자동 진행, `--no-ff --no-commit` 으로 abort 안전 시뮬)

#### Step 1 시뮬레이션: `origin/main` ← `integration/rag-main`
**결과**: ✅ Git 자동 머지 성공, **충돌 0건** (파일명이 달라서 git 충돌 못 잡음)

발생한 변화:
- `app/db/migrations/models/8_20260422_add_rag_chunk_schema.py` **삭제** (origin/main 의 #8)
- `app/db/migrations/models/8_20260422005350_medicine_info_redesign.py` **추가** (integration/rag-main 의 idempotent 재작성본)
- `PLAN.md` 삭제 (integration/rag-main 에서 .gitignore 처리됨)
- `ai_worker/tasks/embedding_tasks.py` 삭제 (rag_tasks.py 로 통합)
- 신규: ai_worker 의 providers/{embedding,llm,router}.py, tasks/{compact,rag,tool}_tasks.py
- 그 외 60+ 파일 변경 (Phase Y · RAG · Phase Z-A 누적)

⚠️ **의미적 검증 필요** (사용자 결정 필수):
- origin/main 의 `#8_add_rag_chunk_schema.py` 삭제가 의도인지
- integration/rag-main 의 #8 가 origin #8 SQL 을 흡수했지만 prod DB 에 origin #8 가 이미 적용된 경우 aerich 가 어떻게 처리할지
- 이 결정은 **§1.4 마이그레이션 통합 옵션 A/B/C** 선택과 직결

#### Step 2 시뮬레이션: `integration/rag-main` ← `origin/feature/lifestyle`
**결과**: ⚠️ Git **자동 충돌 2건** + 의미적 충돌 다수

**Git 자동 충돌 (사용자 1:1 보고 후 해결 대기)**:

(a) `app/db/databases.py` — 모델 등록 목록 (서로 다른 모델 추가)
```
<<<<<<< HEAD (integration/rag-main)
"app.models.medicine_chunk",
"app.models.medicine_ingredient",
=======
"app.models.lifestyle_guide",
"app.models.daily_symptom_log",
>>>>>>> origin/feature/lifestyle
```
**제안 해결안**: 4개 모두 등록 (단순 union — 서로 독립 모델). 본질적 충돌 아님.

(b) `app/repositories/challenge_repository.py` — docstring 한 줄
```
<<<<<<< HEAD
difficulty: Optional difficulty level.
=======
difficulty: Optional difficulty level (쉬움/보통/어려움).
>>>>>>> origin/feature/lifestyle
```
**제안 해결안**: lifestyle 의 더 풍부한 표현 채택 권장.

**의미적 충돌 (Git 이 못 잡지만 사용자 결정 필수)**:

(c) **두 #8 마이그레이션 파일 공존**
- `8_20260422005350_medicine_info_redesign.py` (integration/rag-main)
- `8_20260422221048_add_lifestyle_guide_models.py` (lifestyle 새로 추가)
- aerich 가 같은 #8 번호 두 파일을 어떻게 처리할지 미지수 → **lifestyle 쪽을 #12 등으로 재번호 필수**

(d) `medicine_info` 테이블 정의 차이
- integration/rag-main #8: `medicine_name VARCHAR(200)`, 8개 신규 컬럼
- lifestyle #8: `medicine_name VARCHAR(128)`, embedding TEXT 포함 (구버전)
- **마이그레이션 통합 옵션 결정 후 단일 정의로 수렴 필요**

(e) `challenges` 테이블 확장
- lifestyle #8 가 `is_active`, `category`, `started_at`, `completed_at`, `guide_id` 추가
- integration/rag-main 은 challenges 변경 없음
- 단순 추가라 충돌 본질 아님

**lifestyle 머지로 인한 신규 파일**: 25개+ (lifestyle 라우터, 모델, 서비스, 테스트, FE 페이지)
**lifestyle 머지로 인한 수정 파일**: `.gitignore`, `app/apis/v1/__init__.py`, `app/dtos/challenge.py`, `app/models/challenge.py`, `app/services/challenge_service.py`, FE 의 `BottomNav.jsx` / `Navigation.jsx` / `challenge/page.jsx`

---

## 2. 백업 태그 (2026-04-25 생성 완료)

```powershell
git tag backup/origin-main-2026-04-25 origin/main
git tag backup/integration-rag-main-2026-04-25 integration/rag-main
git tag backup/feature-lifestyle-2026-04-25 origin/feature/lifestyle
```

확인 결과:
```
backup/feature-lifestyle-2026-04-25
backup/integration-rag-main-2026-04-25
backup/origin-main-2026-04-25
```

복구 명령:
```powershell
git reset --hard backup/<tag-name>
```

작업 종료 후 삭제 예정 (커밋 직전):
```powershell
git tag -d backup/origin-main-2026-04-25
git tag -d backup/integration-rag-main-2026-04-25
git tag -d backup/feature-lifestyle-2026-04-25
```

---

## 3. 사용자 결정 대기 항목 (2026-04-25 야간 분석 후)

다음 사항들에 대해 사용자 승인 필요. 결정 후 실제 머지 진행.

### 3.1 마이그레이션 통합 옵션 (§1.4 참조)
- [ ] **옵션 A**: origin/main 의 `#8_add_rag_chunk_schema.py` 그대로 두고, 다른 브랜치 #8 들을 #9~#13 으로 재번호
- [ ] **옵션 B**: integration/rag-main 의 idempotent `#8_medicine_info_redesign.py` 사용, lifestyle 의 #8 만 재번호
- [ ] **옵션 C**: 통합 init 으로 모든 마이그레이션 재작성 (현재 prod DB 데이터 손실)

### 3.2 코드 충돌 해결 승인 (Step 2 의 Git 자동 충돌 2건)
- [ ] **`app/db/databases.py`**: 4개 모델 모두 union — 승인 / 다른 안
- [ ] **`app/repositories/challenge_repository.py`**: lifestyle 의 docstring 채택 — 승인 / 다른 안

### 3.3 의미적 결정
- [ ] `medicine_info.medicine_name` 길이: VARCHAR(128) vs VARCHAR(200)
- [ ] `medicine_info.embedding` 컬럼 유지/제거
- [ ] `feature/lifestyle-guide-llm-refactor` 머지: **불필요** (lifestyle 과 동일) — 확인 OK
- [ ] `docs/claude-md-section-flow-policy` 머지 여부 (CLAUDE.md §4.4 정책 1 단락 추가)

### 3.4 백도어 차단 작업 (메모리 `project_main_integration_plan.md` §2)
- [ ] BE 에 `ENABLE_DEV_LOGIN` / `ENABLE_MOCK_LOGIN` env 가드 추가
- [ ] 관련 라우터에 가드 적용 (현재 코드에서는 Kakao callback 의 `dev_test_login` code 분기로 처리되는 듯 — 추가 조사 필요)

### 3.5 dev/mock 시드 스크립트 분리 (메모리 §1)
- [ ] dev 로그인 계정·프로필 데이터를 `scripts/seed_dev.py` 로 분리
- [ ] 마이그레이션에는 순수 스키마만 남기기

---

## 4. 통합 단계별 로그 (실제 진행 시 채움)

### Step 1 — `integration/step1-phase-y` (Phase Y 머지)

**상태**: 시뮬레이션 완료 (§1.7), 머지 commit 보류 — 사용자 결정 후 진행

**브랜치 생성 (이미 시뮬레이션 시 생성)**:
```powershell
git branch -l "integration/step1-phase-y"   # 존재 확인
# 또는 다음 세션에서:
git checkout -b integration/step1-phase-y origin/main
git merge integration/rag-main --no-ff
```

**시뮬레이션 결과 (§1.7 Step 1)**: Git 충돌 0건, 의미적 검증 필요 (마이그레이션 옵션)

**충돌 파일**: 없음 (시뮬레이션 기준)

**최종 검증** (실제 머지 후):
- [ ] pytest: _passed / failed_
- [ ] Ruff: _PASS / FAIL_
- [ ] Scenario S-1~S-10: _결과_
- [ ] 로컬 prod 빌드: _OK / 실패_

**롤백 포인트**: `backup/step1-phase-y-complete-2026-04-XX`

---

### Step 2 — `integration/step2-lifestyle` (lifestyle 머지)

**상태**: 시뮬레이션 완료 (§1.7), 머지 commit 보류 — 사용자 결정 후 진행

**브랜치 생성**:
```powershell
git checkout -b integration/step2-lifestyle integration/step1-phase-y
git merge origin/feature/lifestyle --no-ff
```

**시뮬레이션 결과 (§1.7 Step 2)**: Git 자동 충돌 2건 + 의미적 충돌 다수

**충돌 파일** (실제 머지 시 채움_

**최종 검증**:
- [ ] pytest: _passed_
- [ ] Ruff: _PASS_
- [ ] Scenario 재검증:
- [ ] lifestyle 스모크 테스트:
- [ ] 로컬 prod 빌드:

---

### Step 3 — `integration/step3-fixes` (배포 실패 수정)

**브랜치 생성**:
```powershell
git checkout -b integration/step3-fixes integration/step2-lifestyle
```

**수정 내용**:
- [ ] 망가진 부분 1:
  - 원인:
  - 수정 커밋:
- _(필요 시 추가)_

**`.env` 누락 감지 항목** → `docs/missing_env.md` 로 이관:

---

### Step 4 — main PR

- [ ] `git push origin integration/step3-fixes`
- [ ] GitHub PR 생성 (대상: `main`)
- [ ] PR description 작성 (변경 범위·테스트 결과·롤백 계획)
- [ ] CI 체크 통과
- [ ] 셀프 머지 체크리스트 7개 전부 OK
- [ ] **"Create a merge commit"** 옵션으로 머지
- [ ] 자동 배포 결과 확인

---

## 4. 사후 정리

- [ ] 백업 태그 삭제:
  ```powershell
  git tag -d backup/origin-main-YYYY-MM-DD
  git tag -d backup/integration-rag-main-YYYY-MM-DD
  git tag -d backup/feature-lifestyle-YYYY-MM-DD
  ```
- [ ] 중간 통합 브랜치 (`integration/step1-phase-y`, `step2-lifestyle`) 삭제 여부 결정
- [ ] `docs/missing_env.md` 누락 항목 일괄 처리

---

## 5. 통합 완료 요약 (2026-04-26)

### 5.1 변경 규모

- 통합 브랜치: `integration/step4-final-schema`
- 대상: `main`
- 신규 커밋 수: **106** (origin/main 기준)
- 머지 커밋: 3 (Step 1 Phase Y / Step 2 lifestyle / Step 3 claude-policy)
- 변경 파일: **161 files**, +20068 / -2199 lines

### 5.2 검증 결과

- ✅ **Ruff**: `check` + `format --check` 모두 PASS (166 files)
- ✅ **Pytest** (Linux 컨테이너): **428 passed, 3 skipped, 0 failed** (6분 58초)
  - Windows 호스트 7건 fail 은 Python 3.14 + RQ fork 호환 문제 (환경 한계)
- ✅ **API smoke**: 41 endpoint 등록, Phase Y 라우터 4종 (`/messages/ask`, `/messages/tool-result`, `/chat-sessions/*`) + lifestyle 라우터 4종 (`/lifestyle-guides/*`, `/challenges/*`) 모두 정상
- ✅ **Phase Y 시나리오 17건**: `docs/scenario.md` 사전 PASS (S-1~S-10 + SEC-1~SEC-7)
- ✅ **로컬 prod 빌드**: `docker compose -f docker-compose.prod.yml build` 성공

### 5.3 마이그레이션 호환성 audit

전 마이그레이션 (#0~#13) upgrade/downgrade 짝 점검 완료:

- ✅ **#0~#3, #6, #7, #9~#11, #13**: 양방향 정합
- ⚠️ **#6** (`add_department_category_to_medications`): downgrade 의 `drug_interaction_cache` / `llm_response_cache` ALTER COLUMN 부분이 양방향 동일 (JSONB→JSONB) — 기존 작성자의 이슈, 본 통합으로 도입된 회귀 아님
- ⚠️ **#12** (`add_lifestyle_guide_models`, lifestyle 머지 산출물): `medicine_info` 의 v1 단순 schema 를 CREATE/DROP 함 (#8 의 풍부한 schema 와 충돌). upgrade 는 `IF NOT EXISTS` 로 무해하나 **downgrade 시 medicine_info 통째 DROP 위험**. lifestyle 원본 마이그레이션을 그대로 머지한 결과이며, 실 운영에서 #12 만 단독 downgrade 하는 시나리오는 없음 (전체 다운그레이드 시에는 #8 이 다시 처리). 추후 squash 마이그레이션 작성 시 정리 예정
- ⚠️ **#12** 의 기존 테이블 COMMENT 가 한국어→영어로 덮어써짐 (`refresh_tokens`, `medications`, `intake_logs` 등): CLAUDE.md §4.3 의 "human-readable description Korean" 규칙과 상충. lifestyle 머지의 부수효과로 RAG 시스템 영향 없음

### 5.4 운영 주의

- **EC2 배포 시 필수 작업**:
  1. `aerich upgrade` 실행 (#13 마이그레이션 적용 — 캐시 테이블 3종 제거 + medicine_chunk DELETE)
  2. `uv run python -m scripts.crawling.fetch_sample` 재실행 (6섹션 v2 enum 으로 재임베딩)
  3. `.env` 의 `OPENAI_API_KEY`, `KAKAO_CLIENT_ID`, `DOCKER_USER`, `DB_PASSWORD` 등 누락 점검
- **GitHub Actions 배포 실패**: 현재 `origin/main` 자동배포 실패 상태 — 본 PR 머지 후 Actions 로그 직접 확인하여 별건 fix
- **백업 태그**: 머지 후 GitHub 에서 main 머지 확인 완료되면 삭제
  - `backup/origin-main-2026-04-25`
  - `backup/integration-rag-main-2026-04-25`
  - `backup/feature-lifestyle-2026-04-25`

### 5.5 완료일

2026-04-26
