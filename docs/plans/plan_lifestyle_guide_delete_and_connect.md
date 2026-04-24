# PLAN: 생활습관 가이드 삭제 + 챌린지 연결

> 상태: **챌린지 연결 구현 완료** / 가이드 삭제 승인 대기

---

## 1. 챌린지 연결 (완료)

### 변경 내용
- `lifestyle-guide/page.jsx`에 `useRouter` 추가
- `handleChallengeStart` 토스트 → "보러가기" 버튼 포함 커스텀 토스트
- `ChallengeBanner`에 `onGoToChallenge` prop 추가 + "오늘 완료!" 상태에 `→` 이동 버튼

### 완료된 흐름
```
시작하기 클릭 → PATCH is_active=true 성공 → toast("챌린지 시작됨 | 보러가기") → /challenge
오늘 완료! 상태 → 배너 우측 → 버튼 → /challenge
```

---

## 2. 가이드 삭제 기능 (미구현 — `go` 대기)

### 모델 제약
- `LifestyleGuide`에 `deleted_at` 없음 → **하드 삭제** 적용
- `Challenge.guide` FK: `null=True` → guide 삭제 전 처리 필요

### 챌린지 처리 방침

| 챌린지 상태 | 처리 | 이유 |
|------------|------|------|
| `is_active=False` | `soft_delete(challenge)` | 미시작 → 가이드와 함께 제거 |
| `is_active=True` | `Challenge.filter(id=c.id).update(guide_id=None)` | 진행중/완료 → 챌린지 페이지에 유지 |

**참고:** `challenge_repo.soft_delete(challenge: Challenge)` 메서드 확인 완료.

### 변경 파일

**백엔드 3개**
- `app/repositories/lifestyle_guide_repository.py` — `delete_by_id()` 추가
- `app/services/lifestyle_guide_service.py` — `delete_guide_with_owner_check()` 추가
- `app/apis/v1/lifestyle_guide_routers.py` — `DELETE /{guide_id}` 엔드포인트 추가

**프론트엔드 1개**
- `medication-frontend/src/app/lifestyle-guide/page.jsx` — 날짜 칩에 × 버튼 + `handleDeleteGuide` 함수

### API 설계

```
DELETE /api/v1/lifestyle-guides/{guide_id}
Response: 204 No Content
```

### 데이터 흐름

```mermaid
flowchart TD
    A[날짜 칩 × 클릭] --> B[confirm 다이얼로그]
    B --> C[DELETE /api/v1/lifestyle-guides/{id}]
    C --> D{연결 챌린지 처리}
    D -->|is_active=False| E[soft_delete — deleted_at 설정]
    D -->|is_active=True| F[guide_id=NULL — 챌린지 유지]
    D --> G[가이드 하드 삭제]
    G --> H[프론트 목록에서 제거\n이전 최신 가이드 선택]
```
