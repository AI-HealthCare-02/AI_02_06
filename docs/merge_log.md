# origin/main 통합 작업 머지 로그

> 2026-04-25 시작. Phase Y (툴 콜링) + 팀원 브랜치 여러 개 + origin/main 의 배포
> 실패 수정을 **하나의 통합 브랜치**로 합치는 여정의 기록. 각 단계의 타임라인,
> 충돌 해결 이유, 롤백 포인트를 남긴다.

---

## 0. 통합 대상 브랜치

| 브랜치 | 내용 | 기준 tag |
|---|---|---|
| `origin/main` | 자동배포 대상, 배포 실패 상태 (런타임 에러는 없음) | `backup/origin-main-YYYY-MM-DD` |
| `integration/rag-main` | Phase Y (툴 콜링) + RAG 통합 + Phase Z-A 요약 | `backup/integration-rag-main-YYYY-MM-DD` |
| `feature/lifestyle` | 생활습관 가이드 + 챌린지 확장 | `backup/feature-lifestyle-YYYY-MM-DD` |
| `<팀원 추가 브랜치>` | _TBD_ | _TBD_ |

---

## 1. 사전 진단

### 1.1 origin/main 배포 실패 원인
- [ ] GitHub Actions 로그 확인
- [ ] 로컬 `docker compose -f docker-compose.prod.yml build` 재현
- [ ] 로컬 `up -d` 기동 확인 (postgres/redis/fastapi/ai-worker)
- [ ] 원인 요약:

  _채워넣기_

### 1.2 마이그레이션 현황 (각 브랜치별)

| 브랜치 | `app/migrations/models/` 파일 목록 | `app/models/*.py` 신규·변경 |
|---|---|---|
| `origin/main` |  |  |
| `integration/rag-main` |  |  |
| `feature/lifestyle` |  |  |

### 1.3 최종 스키마 결정 (사용자 승인)
- [ ] 살릴 테이블:
- [ ] 삭제할 테이블:
- [ ] 살릴 컬럼:
- [ ] 삭제할 컬럼:
- [ ] 결정 근거:

---

## 2. 백업 태그

```powershell
git tag backup/origin-main-YYYY-MM-DD origin/main
git tag backup/integration-rag-main-YYYY-MM-DD integration/rag-main
git tag backup/feature-lifestyle-YYYY-MM-DD feature/lifestyle
```

- [ ] 태그 생성 완료:
- [ ] 작업 종료 후 삭제 예정:

---

## 3. 통합 단계별 로그

### Step 1 — `integration/step1-phase-y` (Phase Y 머지)

**브랜치 생성**:
```powershell
git checkout -b integration/step1-phase-y origin/main
git merge integration/rag-main --no-ff
```

**충돌 파일**:

#### 3.1.1 `<파일 경로>` (줄 X-Y)
- 양쪽 의도:
  - origin/main:
  - integration/rag-main:
- 선택한 해결:
- 선택 이유:

_(충돌마다 반복)_

**최종 검증**:
- [ ] pytest: _passed / failed_
- [ ] Ruff: _PASS / FAIL_
- [ ] Scenario S-1~S-10: _결과_
- [ ] 로컬 prod 빌드: _OK / 실패_

**롤백 포인트**: `backup/step1-phase-y-complete-YYYY-MM-DD`

---

### Step 2 — `integration/step2-lifestyle` (lifestyle 머지)

**브랜치 생성**:
```powershell
git checkout -b integration/step2-lifestyle integration/step1-phase-y
git merge feature/lifestyle --no-ff
```

**충돌 파일**:

_(Step 1 동일 형식으로 채움)_

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

## 5. 통합 완료 요약

- 총 커밋 수: _N_
- 머지 커밋 수: _M_
- 해결한 충돌: _K_ 건
- 테스트 결과: _pytest, ruff, scenario_
- 완료일:
