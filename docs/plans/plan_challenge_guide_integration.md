# PLAN: 챌린지 페이지 — 가이드 기반 전면 개편

> 상태: **승인 대기** — `go` 명령 후 구현 시작

---

## 목표

하드코딩된 TEMPLATES를 제거하고, AI 생활습관 가이드에서 추천받은 챌린지만 사용한다.
챌린지 조직 기준은 **사용자가 시작한날(started_date)** 기준으로 설계한다.

---

## 날짜 기준 결정: 시작한날 기준 ✅

| 기준 | 장점 | 단점 |
|------|------|------|
| 가이드 생성일 (처방일) | 처방 컨텍스트 명확 | 사용자가 통제 불가 — 동기 부여 약함 |
| **시작한날 (started_date)** | **"D+N 달성!" 커밋먼트** / 산업 표준 / 모멘텀 강조 | 없음 |

**결론:** 진행중 챌린지를 `D+N` (시작 후 N일째) 형태로 표시.
정렬은 **started_date 내림차순** (최근 시작한 챌린지 먼저).

---

## Best Example 레퍼런스

- **Duolingo**: Streak day counter + 하루 1회 완료 체크
- **Apple Fitness Rings**: 카테고리별 색상 + 진행률 링/바
- **Strava**: 날짜 기반 정렬 + 활동 요약 카드
- **Habitica**: 카테고리 아이콘 뱃지 + 즉각 피드백

---

## 현황 분석

### 현재 challenge/page.jsx
- TEMPLATES 10개 하드코딩 (금연, 걷기, 복약, 식단, 물, 수면, 혈압, 혈당, 카페인, 스트레칭)
- DifficultyModal로 난이도 선택 → `POST /api/v1/challenges` 생성
- 진행중 탭: `GET /api/v1/challenges?profile_id=` 필터링

### 문제점
- AI 가이드 추천과 완전히 분리되어 있음
- TEMPLATES는 모든 사용자에게 동일 — 개인화 없음
- 가이드에서 시작한 챌린지가 추천 탭에 표시되지 않음

---

## 변경 후 아키텍처

```mermaid
flowchart TD
    A[생활습관 가이드\n가이드 생성] -->|AI 추천 챌린지 자동 생성| B[DB: challenges\nguide_id 연결]
    B --> C[챌린지 페이지 추천 탭\nGET /lifestyle-guides/latest\n→ GET /lifestyle-guides/{id}/challenges\n→ is_active=False 필터링]
    C -->|시작하기 클릭| D[PATCH /challenges/{id}\nis_active=true]
    D --> E[챌린지 페이지 진행중 탭\nstarted_date 기준 정렬\nD+N 표시]
```

---

## 변경 파일

**프론트엔드 1개 (백엔드 변경 없음)**
- `medication-frontend/src/app/challenge/page.jsx`

---

## 상세 변경 내용

### 삭제
- `TEMPLATES` 배열 (10개 하드코딩 항목)
- `DifficultyModal` 컴포넌트 (가이드 챌린지는 난이도 고정)
- `handleAccept`, `handleConfirmStart` 함수
- `isAlreadyStarted`, `difficultyTarget` 상태

### 추가

#### 추천 탭 — 가이드 챌린지 페치

```jsx
// state 추가
const [guideId, setGuideId] = useState(null)
const [recommended, setRecommended] = useState([]) // is_active=false 챌린지
const [isLoadingRecommended, setIsLoadingRecommended] = useState(false)

// 데이터 페치
const fetchRecommended = async () => {
  const latestRes = await api.get(`/api/v1/lifestyle-guides/latest?profile_id=${profileId}`)
  const guide = latestRes.data
  setGuideId(guide.id)
  const challengeRes = await api.get(`/api/v1/lifestyle-guides/${guide.id}/challenges`)
  const unstarted = challengeRes.data.filter(c => !c.is_active && c.challenge_status !== 'DELETED')
  setRecommended(unstarted)
}
```

#### 추천 탭 — 시작하기 (PATCH)

```jsx
const handleStartGuideChallenge = async (challenge) => {
  const res = await api.patch(`/api/v1/challenges/${challenge.id}`, { is_active: true })
  // 추천에서 제거, 진행중에 추가
  setRecommended(prev => prev.filter(c => c.id !== challenge.id))
  setOngoing(prev => [{ ...res.data, icon: getIconByTitle(res.data.title), current: 0 }, ...prev])
  toast.success('챌린지가 시작되었습니다!')
  setActiveTab('진행중')
}
```

#### 진행중 탭 — D+N 표시 + started_date 정렬

```jsx
// 정렬: started_date 내림차순 (최근 시작 먼저)
const sortedOngoing = [...ongoing].sort(
  (a, b) => new Date(b.started_date) - new Date(a.started_date)
)

// D+N 계산 유틸
function getDaysSince(startedDate) {
  const diff = Date.now() - new Date(startedDate).getTime()
  return Math.floor(diff / (1000 * 60 * 60 * 24)) + 1
}

// UI: "D+7 · 14일 목표"
<p className="text-xs text-gray-400">D+{getDaysSince(item.started_date)} · {item.target_days}일 목표</p>
```

#### 카테고리 뱃지 (가이드 챌린지에 category 필드 있음)

```jsx
const CATEGORY_META = {
  interaction: { label: '약물', color: 'bg-red-50 text-red-500' },
  sleep:       { label: '수면', color: 'bg-indigo-50 text-indigo-500' },
  diet:        { label: '식단', color: 'bg-green-50 text-green-500' },
  exercise:    { label: '운동', color: 'bg-blue-50 text-blue-500' },
  symptom:     { label: '증상', color: 'bg-orange-50 text-orange-500' },
}

// 진행중 카드에 카테고리 뱃지 추가
{item.category && CATEGORY_META[item.category] && (
  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${CATEGORY_META[item.category].color}`}>
    {CATEGORY_META[item.category].label}
  </span>
)}
```

#### 추천 탭 — 가이드 없을 때 EmptyState

```jsx
// 가이드 404 → 가이드 페이지 안내
<EmptyState
  title="아직 AI 추천 챌린지가 없어요"
  message="생활습관 가이드를 먼저 받아보세요"
  onAction={() => router.push('/lifestyle-guide')}
  actionLabel="가이드 받기"
/>
```

---

## UI 변화 요약

| 탭 | 전 | 후 |
|----|----|----|
| 추천 | 하드코딩 TEMPLATES 10개 | 최신 가이드의 미시작 챌린지 (AI 맞춤) |
| 진행중 | created_at 순 | **started_date 내림차순 + D+N 뱃지 + 카테고리 색상** |
| 완료 | 변경 없음 | 카테고리 뱃지 추가 |

---

## 엣지 케이스

| 상황 | 처리 |
|------|------|
| 가이드 없음 (첫 사용자) | 추천 탭에 "가이드 받기" EmptyState + /lifestyle-guide 링크 |
| 모든 가이드 챌린지를 시작한 경우 | 추천 탭 "모든 추천 챌린지를 시작했습니다!" EmptyState |
| 수동으로 만든 챌린지 (guide=NULL) | 진행중/완료 탭에 정상 표시, 카테고리 뱃지 없음 |
| 가이드 로딩 실패 (API 에러) | 추천 탭에 에러 상태 + 재시도 버튼 |
