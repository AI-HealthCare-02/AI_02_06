# Migration Chain Normalization Guide

> **Branch**: `refactor/migrations-normalize`
> **Date**: 2026-05-02
> **Author**: kimyeongbin-dev
> **Scope**: aerich migration chain 0~28 정상화 (시나리오 A 정공 강제)

---

## 1. 배경 — 왜 정상화가 필요한가

### 1.1 현재 chain 의 손상 진단

`scripts/_chain_audit.py` 실행 결과:

| 영역 | 문제 |
|---|---|
| **20번** (`add_drug_recalls`) | `MODELS_STATE = None`. PR #89 zlib 사고 후 영구 None 으로 정리. DrugRecall 모델 dict 누락 |
| **21번** (`medicine_info_jsonb_and_dosage`) | 19번 zlib 위에 19~21번 누적 변경을 흡수해 점프. chain 의미 깨짐 |
| **13~19번** (7개) | raw SQL only 마이그 — 모델 클래스 변경 없이 raw SQL 만 추가. zlib 직전 동일 복사 (DB-first 패턴) |
| **22번** (`profile_relation_v2`) | DrugRecall 모델이 22번 zlib 에서 첫 등장 — 20번 시점에 들어갔어야 함 |

### 1.2 본질 — 시나리오 A vs B vs C 충돌

본 프로젝트는 **시나리오 A (모델 클래스 우선)** 을 채택했으나, 일부 마이그가 **DB-first (raw SQL → fake migration)** 로 작성되어 chain 손상.

```
┌────────────────────────────────────────────────────────────┐
│ 시나리오 A (정공)                                          │
│  app/models/*.py 수정 (개발자)                             │
│   → aerich migrate (자동 SQL + zlib 생성)                  │
│   → 개발자가 SQL 본문만 수정 (인덱스 이름, BIGSERIAL 등)   │
│   → MODELS_STATE 는 절대 손대지 않음                       │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ 시나리오 B (DB-first, 금지)                                │
│  raw SQL 마이그 직접 작성 (모델 변경 없음)                 │
│   → aerich 가 자동 생성 안 함                              │
│   → MODELS_STATE 는 직전 zlib 복사 또는 None               │
│   → chain 의미 깨짐                                        │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ 시나리오 C (혼합, 금지)                                    │
│  모델 클래스 추가 + raw SQL 마이그 직접 작성               │
│   → aerich 자동 생성 zlib 손실                             │
│   → 위반 사례: 20번 (drug_recalls)                         │
└────────────────────────────────────────────────────────────┘
```

### 1.3 운영 정책 (확정)

> **시나리오 A 만 허용**. 모든 마이그는 모델 클래스 우선 + aerich 자동 zlib 보존.
> 모델 클래스로 표현 불가능한 PostgreSQL 기능 (pgvector / tsvector / 함수 / 트리거 / 데이터 마이그레이션) 은 **자동 생성된 SQL 본문에 추가** 로 처리.

---

## 2. 정상화 작업 절차

### 2.1 정방향 (0 → 28) chain 재생성

```
[Setup]
  - 별도 PR `refactor/migrations-normalize` (main 기준 분기)
  - 백업: docs-private/aerich_backup_20260502/  (이미 완료)
  - 로컬 docker postgres 의 downforce_db DROP + CREATE

For N in [0, 1, 2, ..., 28]:
  [A] 그 시점 모델 코드 재현
      git show <N번 commit>:app/models/*.py | 또는 git worktree
      → app/models/ 에 적용

  [B] aerich migrate --name <원 이름>
      → 자동 SQL + 정확한 zlib 생성

  [C] 자동 생성된 SQL 본문을 백업의 N번 raw SQL 로 비교
      - 의도된 부분 (BIGSERIAL, 인덱스 이름, COMMENT, 데이터 마이그, GIN, EXTENSION, pgvector, tsvector) 만 raw SQL 로 덮어씀
      - MODELS_STATE 는 손대지 않음

  [D] aerich upgrade
      → 로컬 DB 적용 + aerich 테이블 INSERT
      → 다음 N+1 의 직전 zlib 으로 사용
```

### 2.2 raw SQL only 마이그의 시나리오 A 변환

본 정상화에서 가장 어려운 케이스. 13~19번이 해당. 각 마이그의 raw SQL 을 보고 **모델 클래스 변경을 추론**:

| # | raw SQL 본질 | 모델 클래스 변경 |
|---|---|---|
| 13 | `DROP TABLE drug_interaction_cache, llm_response_cache, mock_items` + `DELETE FROM medicine_chunk` | DrugInteractionCache / LLMResponseCache 모델 *삭제*. mock_items 는 모델 무관 |
| 14 | `CREATE TABLE ocr_drafts` | OcrDraft 모델 *신규 추가* |
| 15 | `lifestyle_guides + status, processed_at` + UPDATE backfill | LifestyleGuide.status, processed_at 필드 *추가* |
| 16 | `medicine_info.pack_unit TYPE VARCHAR(2048)` | MedicineInfo.pack_unit max_length=2048 *변경* |
| 17 | `medications DROP prescription_image_url` | Medication 의 prescription_image_url 필드 *삭제* |
| 18 | `medicine_chunk.interaction_tags JSONB + GIN` | MedicineChunk.interaction_tags 필드 *추가* |
| 19 | `chat_sessions.summary, summary_updated_at 추가` | ChatSession.summary, summary_updated_at 필드 *추가* |

→ **각 마이그 정상화 시 모델 클래스를 정확한 상태로 만든 후 aerich migrate** 실행. 그러면 그 마이그가 raw SQL only 가 아니라 **자동 SQL 마이그가 됨** + 추가 raw SQL (데이터 마이그, GIN 등) 만 본문에 더해짐.

### 2.3 시점별 모델 코드 재현 — git worktree

각 N번 commit 시점의 모델 코드를 별도 worktree 로 분리:

```bash
git worktree add /tmp/wt_<N>_<short_sha> <N번 commit>
# 그 시점 코드 + DB 상태가 진실
```

본 정상화는 **현재 worktree 에서 모델 클래스를 단계별로 후퇴/전진** 하는 방식이 더 단순:
- 0번 시점: 현재 코드 → 1~28번 변경 모두 역적용 (수동) → init 직전 상태
- 1번 시점: 0번 init + 1번 변경
- ...

git worktree 는 검증 보조 (현재 코드 ↔ 시점별 코드 비교).

### 2.4 28번 처리 (본 PR 의 RAG 작업 흡수)

28번은 정상화 PR 에서도 신규 작성. feature/RAG 의 `9424f38` commit 의 28번 SQL 을 참고:
- 모델 변경 0 (medicine_chunk.embedding 그대로 TextField)
- raw SQL: pgvector vector(768→3072) + tsvector + trigger + GIN + HNSW 재생성
- aerich migrate 가 "No changes" 출력 → **dummy 모델 변경 (예: TextField description 한 글자) → aerich migrate → dummy revert → 자동 zlib 추출 후 raw SQL 본문 채움**

---

## 3. 팀원 적용 가이드

### 3.1 사전 준비 (정상화 PR 머지 전 공지)

> **공지 시점**: 정상화 PR 머지 직후 Slack/공유 채널
>
> **내용**:
> ```
> [중요] aerich migration chain 정상화 PR 이 머지됐습니다.
>
> 모든 팀원은 다음 절차로 로컬 환경 갱신:
>
> 1. git pull origin main
> 2. 본인의 로컬 docker postgres 데이터 백업 (필요 시)
> 3. docker compose down -v        # ← 로컬 DB volume 삭제
> 4. docker compose up -d           # ← DB 재생성
> 5. docker compose exec fastapi aerich upgrade
>      → 정상화된 0~28번 마이그 모두 적용
> 6. 정상 동작 확인
>
> 운영 EC2 는 자동배포 + aerich 가 "이미 적용된 마이그" 로 인식하므로
> 운영 영향 없습니다.
> ```

### 3.2 향후 마이그 작성 시 룰 (시나리오 A 강제)

```
[1] app/models/*.py 만 수정 (개발자)
    - 새 모델 클래스 추가
    - 컬럼 추가 / 삭제 / 타입 변경

[2] docker compose exec fastapi aerich migrate --name <descriptive_name>
    - aerich 가 자동으로 마이그 파일 생성
    - upgrade()/downgrade() SQL 자동 생성
    - MODELS_STATE 자동 zlib 채워짐

[3] 자동 생성된 SQL 본문 검토
    - 의도된 인덱스 이름, BIGSERIAL, COMMENT, IF NOT EXISTS 등 변경 가능
    - 데이터 마이그레이션 (UPDATE), pgvector / tsvector / 함수 / 트리거 추가

[4] MODELS_STATE 는 절대 손대지 않음

[5] git add + commit + PR
```

### 3.3 raw SQL only 마이그 금지

- 모델 변경이 0 이라도 **마이그 파일을 사람이 처음부터 작성하지 말 것**
- 모델 변경 없이 데이터 마이그 / 인덱스만 변경이 필요하면:
  - 임시 dummy 모델 변경 (CharField description 1글자 변경 등)
  - aerich migrate 실행 → 자동 zlib 채워진 마이그 파일 생성
  - dummy 변경 revert → 자동 SQL 본문에 의도된 raw SQL 추가
  - MODELS_STATE 는 보존

---

## 4. 운영 EC2 영향 평가

### 4.1 자동배포 시 동작

```
정상화 PR 머지 → GitHub Actions 자동배포
  → ghcr.io 이미지 빌드 (정상화된 마이그 파일 포함)
  → EC2 docker compose pull + up
  → fastapi 컨테이너 시작 시 aerich upgrade 자동 실행 (compose 의 entrypoint 또는 수동)
  → aerich 가 DB 의 aerich 테이블 조회
    → 0~27번 이미 적용 (기존 운영 상태)
    → 새 마이그 파일의 version 이름이 동일하면 "이미 적용" 으로 인식
    → 28번만 신규 적용
```

### 4.2 aerich.content 텍스트 차이

- 운영 DB 의 `aerich.content` 컬럼엔 기존 마이그의 raw SQL 텍스트 저장됨
- 정상화 후 새 마이그의 SQL 텍스트와 미세 차이 가능 (인덱스 이름 hash, 자동 생성 부분 등)
- aerich 는 `version` 이름만으로 적용 여부 판정 → **content 차이는 동작 영향 없음**
- 단 content 차이가 발생하므로, 향후 디버깅 시 혼동 방지 위해 **운영 EC2 의 aerich 테이블 content 도 새 SQL 로 갱신** 검토 (선택)

### 4.3 DB schema 차이

- 정상화 시 자동 생성 SQL 의 인덱스 이름이 기존과 다를 수 있음 (`idx_<table>_<col>_<hash>` 의 hash 부분 변경 가능성)
- 본 정상화는 **백업의 raw SQL DDL 의미 100% 보존** 이 원칙 → 인덱스 이름도 동일하게 유지
- 검증: 정상화 후 로컬 DB 의 `\d+ <table>` 출력 vs 운영 DB 비교

---

## 5. 진행 체크리스트

### Step 1: PLAN 문서화 (현재)
- [x] docs/MIGRATIONS_NORMALIZATION.md 작성
- [x] docs-private/aerich_backup_20260502/_chain_audit.py 보존 (검증용)
- [x] 백업 27 마이그 + 18 모델 + MANIFEST.md5 (docs-private/aerich_backup_20260502/)

### Step 2: 환경 준비
- [ ] 로컬 docker postgres 의 downforce_db DROP + CREATE
- [ ] app/db/migrations/models/ 비움 (백업은 docs-private/)
- [ ] 현재 모델 코드 백업 확인

### Step 3~7: 마이그 0~28번 정방향 재생성
- [ ] 0~7번 (8개)
- [ ] 8~12번 (5개)
- [ ] 13~19번 (7개) — raw SQL only 변환
- [ ] 20~22번 (3개) — drug_recalls / JSONB / relation_v2
- [ ] 23~28번 (6개)

### Step 8: 통합 검증
- [ ] audit 도구 재실행 → 모든 zlib OK + chain 정합
- [ ] 백업의 raw SQL ↔ 정상화된 raw SQL DDL 의미 동등 검증

### Step 9: Commit + Push
- [ ] Ruff 검사 통과
- [ ] git commit (단계별 또는 단일)
- [ ] git push

### Step 10: 팀 공지 + 운영 검증
- [ ] Slack 공지 초안 (위 §3.1)
- [ ] 본 PR 머지 후 운영 EC2 자동배포 모니터링

---

## 5.5. 진입 시 발견된 환경 함정 (2026-05-02 첫 시도)

### 함정 1: `app/db/databases.py` 의 `TORTOISE_APP_MODELS` 가 hardcode
- 18 모듈명 직접 나열 (`app.models.accounts`, ..., `app.models.drug_recall`)
- 시점별 정상화 시 *각 마이그 시점의 모듈 리스트* 로 변경 필요
- 0번 시점 → 13개, 13번 시점 → 11개 (2개 삭제), ...
- 정상화 절차에 `databases.py` 도 함께 시점별 변경하는 단계 추가 필요

### 함정 2: `docker-compose.yml` 의 `./app:/app/app` bind mount
- 호스트 `app/` 와 컨테이너 `/app/app/` 이 동일 파일
- 컨테이너 안에서 `rm -rf /app/app/db/migrations/models/*` 실행 시 **호스트 파일도 동시 삭제**
- 정상화 작업 중 의도치 않은 삭제 위험
- 회복: `git restore app/db/migrations/models/` → bind mount 통해 컨테이너에도 즉시 동기화 ✅

### 함정 3: 컨테이너 권한 (USER appuser)
- `/app/app/db/migrations/models/` 디렉터리 = root 소유 + appuser 쓰기 X
- 컨테이너 안에서 `mkdir` / `touch` 시 Permission denied
- 단 `docker cp` (호스트 → 컨테이너) 는 권한 우회 가능 — 그러나 PowerShell glob 변환 충돌 추가 함정

### 함정 4: aerich CLI PATH
- 컨테이너 내부의 aerich = `/app/.venv/bin/aerich` (PATH 미등록)
- `aerich` 명령은 작동 안 함 → `/app/.venv/bin/aerich` 절대 경로 필수
- 또는 `uv run aerich` (호스트에서)

### 함정 5: Git Bash 의 경로 변환 (MSYS_NO_PATHCONV)
- `docker compose exec ... /app/...` 호출 시 Git Bash 가 `/app/` 을 Windows 경로로 변환
- 우회: `MSYS_NO_PATHCONV=1` prefix
- 또는 `docker exec` (compose 우회) + PowerShell

### 작업 영향
- 위 5가지 함정은 정상화 작업의 *진짜 어려움*. 실 진행 시 매 시점마다 우회 필요
- 시점별 모델 변경 (한 번에 27회) + 이런 함정 5종 동시 처리는 사용자 입력 + 실시간 디버깅 필수
- → 단계별 commit + 사용자 확인 권장 (한 세션 내 일괄 진행은 위험)

---

## 6. 위험 + 회복

### 위험 1: 정상화 중 chain 깨짐
- **회복**: docs-private/aerich_backup_20260502/ 에서 마이그 파일 복원
- **명령**: `cp docs-private/aerich_backup_20260502/migrations/*.py app/db/migrations/models/`

### 위험 2: 모델 클래스 시점 추정 오류
- **회복**: git history 의 각 마이그 commit 시점 코드 재확인 + 비교

### 위험 3: aerich migrate 가 dummy 모델 변경 인식 실패
- **회복**: dummy 변경 폭 늘림 (CharField max_length 변경 등)

### 위험 4: 운영 EC2 의 자동배포 시점 정상화 PR 가 깨진 chain 으로 도착
- **회복**: 머지 전 로컬에서 100% 검증 + 별도 staging EC2 검증 (있으면)

---

## 7. 참고 자료

- `docs-private/aerich_backup_20260502/_chain_audit.py` — chain 무결성 / 인코딩 / 위험 SQL 검증 도구 (1회성, docs-private 보존, git 추적 X)
- `docs-private/aerich_backup_20260502/` — 백업 (29 파일, 268KB)
- `docs-private/2026-05-02_plan_cleancode_archive.md` — 직전 PLAN archive
- aerich 공식 docs: https://github.com/tortoise/aerich (0.9.2)
