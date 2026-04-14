# Security Enhancement Plan

## 1. RTR (Refresh Token Rotation) + Grace Period

### 개념
- **RTR**: Refresh Token 사용 시 새 토큰 발급 + 기존 토큰 무효화
- **Grace Period**: 동시 요청 시 구 토큰도 잠시 유효하게 유지

### Grace Period 적정값 분석

| 값 | 장점 | 단점 |
|----|------|------|
| 0.01초 (10ms) | 보안 극대화 | 네트워크 지연 시 실패 (RTT 50-200ms) |
| 1-2초 | 대부분 동시 요청 커버 | 짧은 공격 윈도우 |
| 5초 | 모바일/느린 네트워크 대응 | 탈취 시 악용 가능 |
| 30초 | 안정성 최대 | 보안 약화 |

**권장: 2초**
- 일반적인 네트워크 지연(RTT 200ms) + 서버 처리 시간 고려
- 다중 탭/요청 동시 발생 대응
- 공격자가 2초 내 재사용해야 하므로 실질적 위험 낮음

### DB 스키마 변경
```sql
-- refresh_tokens 테이블에 추가
rotated_at TIMESTAMP NULL,  -- 교체된 시점 (grace period 계산용)
replaced_by BIGINT NULL,    -- 새 토큰 ID (추적용)
```

### 토큰 검증 로직
```
1. token_hash로 조회
2. is_revoked = True?
   - rotated_at이 있고, 현재시간 - rotated_at < 2초 → 유효 (grace)
   - 그 외 → 무효
3. is_revoked = False?
   - expires_at 확인 → 유효/만료
```

---

## 2. Request Deduplication (FE)

### 문제점
| 문제 | 설명 |
|------|------|
| 죽음의 무한루프 | 401 → refresh → 401 → refresh... |
| 약속의 실종 | refresh 중 다른 요청이 새 토큰 못 받음 |
| 잘못된 합치기 | 여러 refresh 요청이 각각 토큰 발급 |
| 레이스 컨디션 | 동시 요청이 서로 다른 토큰 사용 |

### 해결: Token Refresh Queue

```javascript
// tokenManager.js
let isRefreshing = false;
let refreshSubscribers = [];

function subscribeTokenRefresh(callback) {
  refreshSubscribers.push(callback);
}

function onRefreshed(newToken) {
  refreshSubscribers.forEach(cb => cb(newToken));
  refreshSubscribers = [];
}

async function refreshToken() {
  if (isRefreshing) {
    // 이미 갱신 중이면 대기
    return new Promise(resolve => subscribeTokenRefresh(resolve));
  }

  isRefreshing = true;
  try {
    const { data } = await api.post('/api/v1/auth/refresh');
    localStorage.setItem('access_token', data.access_token);
    onRefreshed(data.access_token);
    return data.access_token;
  } finally {
    isRefreshing = false;
  }
}
```

### Axios Interceptor 흐름
```
요청 실패 (401)
  ↓
isRefreshing 체크
  ├─ false → refreshToken() 호출, isRefreshing = true
  │           ↓
  │         성공 → 대기 중인 요청들에 새 토큰 전달
  │         실패 → 로그아웃 처리
  │
  └─ true → Promise 반환, refreshSubscribers에 등록
            (토큰 갱신 완료 시 자동 재시도)
```

---

## 3. 입력값 검증 (BE Middleware)

### 검증 대상
| 패턴 | 공격 유형 | 처리 |
|------|----------|------|
| `<script>`, `javascript:`, `on\w+=` | XSS | 차단 |
| `' OR`, `" OR`, `; DROP`, `UNION SELECT` | SQL Injection | 차단 |
| `{{`, `${`, `#{` | Template Injection | 차단 |
| `../`, `..\\` | Path Traversal | 차단 |

### 미들웨어 구조
```python
# app/middlewares/security.py

DANGEROUS_PATTERNS = [
    r'<script',
    r'javascript:',
    r'on\w+\s*=',
    r"('\s*OR|\"\s*OR)",
    r'(UNION\s+SELECT|DROP\s+TABLE)',
    r'\{\{|\$\{|#\{',
    r'\.\.[/\\]',
]

async def validate_input_middleware(request, call_next):
    # Body, Query, Path 파라미터 검사
    # 위험 패턴 발견 시 400 Bad Request
```

### 주의사항
- 정규표현식은 case-insensitive로
- JSON body의 모든 string 필드 재귀 검사
- 로깅하되 민감 정보는 마스킹

---

## 4. CSP (Content Security Policy)

### 헤더 설정
```python
# app/middlewares/security.py

CSP_POLICY = {
    "default-src": "'self'",
    "script-src": "'self'",  # unsafe-inline 불허
    "style-src": "'self' 'unsafe-inline'",  # Tailwind 등 인라인 스타일 허용 (필요시)
    "img-src": "'self' https://k.kakaocdn.net data:",  # 카카오 프로필 이미지
    "connect-src": "'self' https://kauth.kakao.com https://kapi.kakao.com",
    "frame-ancestors": "'none'",
    "form-action": "'self'",
}

async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Content-Security-Policy"] = build_csp(CSP_POLICY)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response
```

### Next.js (FE)
```javascript
// next.config.mjs
const securityHeaders = [
  { key: 'Content-Security-Policy', value: "..." }
];
```

---

## 5. 즉시 차단 / 즉시 알림 / 간편 복구

### 즉시 차단
- **BE**: 토큰 탈취 감지 시 `revoke_all_for_account()` 호출
- **탈취 감지 조건**:
  - Grace period 이후 구 토큰 재사용 시도
  - 동일 토큰이 다른 IP/User-Agent에서 사용

### 즉시 알림
- **FE**: 403 응답 시 Toast + 모달로 안내
  - "다른 기기에서 로그인되어 현재 세션이 종료되었습니다"
- **BE**: (선택) 이메일/푸시 알림

### 간편 복구
- **FE**: 로그아웃 처리 후 로그인 페이지로 리다이렉트
- 재로그인만으로 새 세션 시작 (별도 복구 절차 없음)

```javascript
// errors.js 확장
if (parsed.code === 'token_compromised') {
  showError('보안을 위해 로그아웃되었습니다. 다시 로그인해주세요.');
  localStorage.removeItem('access_token');
  window.location.href = '/login';
}
```

---

## 6. 구현 순서 (커밋 단위)

### Phase 1: Backend 기반
1. **refresh_tokens 모델 확장** (rotated_at, replaced_by)
2. **RTR 엔드포인트 추가** (POST /auth/refresh)
3. **Grace Period 로직** (repository 수정)

### Phase 2: Security Middleware
4. **입력값 검증 미들웨어**
5. **CSP 헤더 미들웨어**
6. **탈취 감지 로직** (이상 사용 감지)

### Phase 3: Frontend
7. **tokenManager.js** (Request Deduplication)
8. **api.js 인터셉터 개선** (401 처리 큐)
9. **에러 처리 확장** (token_compromised)

### Phase 4: Integration
10. **E2E 테스트** (시나리오별 검증)

---

## 7. 예상 파일 변경

| 파일 | 변경 내용 |
|------|----------|
| `app/models/refresh_tokens.py` | rotated_at, replaced_by 필드 추가 |
| `app/repositories/refresh_token_repository.py` | rotate(), validate_with_grace() |
| `app/services/oauth.py` | refresh_access_token() 메서드 |
| `app/apis/v1/oauth_routers.py` | POST /auth/refresh 엔드포인트 |
| `app/middlewares/__init__.py` | 신규 |
| `app/middlewares/security.py` | 입력값 검증 + CSP |
| `app/main.py` | 미들웨어 등록 |
| `medication-frontend/src/lib/tokenManager.js` | 신규 |
| `medication-frontend/src/lib/api.js` | 인터셉터 개선 |
| `medication-frontend/src/lib/errors.js` | 에러 코드 추가 |

---

## 8. 결정 완료

| 항목 | 결정 |
|------|------|
| Grace Period | **2초** |
| CSP style-src | **nonce 기반** (unsafe-inline 불허) |
| 탈취 감지 시 | **해당 토큰만 종료** |
| 입력값 검증 실패 | **400 Bad Request** |
| 입력값 검증 방식 | **Middleware(1차) + Pydantic+Bleach(2차)** |

---

# Survey Popup 자동 표시 기능

## 목표
- **Dev 사용자**: main 페이지 진입 시 항상 설문 팝업 표시
- **Kakao 로그인 사용자**: 신규 가입자(최초 생성)만 설문 팝업 표시

---

## 현재 상태 분석

### 1. 기존 흐름
```
[로그인] --> {is_new_user?}
           |
           |--(Yes)--> /survey 페이지로 리다이렉트
           |
           |--(No)--> /main 페이지로 이동
                        |
                        --> SurveyModal 있지만 수동 트리거만 가능
```

### 2. 관련 파일
| 파일 | 현재 역할 |
|------|----------|
| `auth/kakao/callback/page.jsx` | `is_new_user` 확인 후 `/survey` 리다이렉트 |
| `main/page.jsx` | SurveyModal 컴포넌트 존재, 수동 트리거만 |
| `login/page.jsx` | Dev 로그인 시 `code=dev_test_login` 사용 |

### 3. 문제점
- 신규 유저가 `/survey`로 리다이렉트되면 main 페이지 경험 없음
- Dev 사용자 구분 로직 없음
- main 페이지에서 자동 팝업 트리거 없음

---

## 수정 계획

### Phase 1: 백엔드 수정 (is_dev_user 플래그 추가)

**파일**: `app/apis/v1/oauth_routers.py`

- Dev 로그인 응답에 `is_dev_user: true` 플래그 추가
- 기존 `is_new_user` 플래그 유지

```python
# 예시: callback 응답
{
    "access_token": "...",
    "is_new_user": true,
    "is_dev_user": true  # Dev 로그인인 경우만
}
```

### Phase 2: 프론트엔드 콜백 수정

**파일**: `medication-frontend/src/app/auth/kakao/callback/page.jsx`

- 기존: `is_new_user`면 `/survey`로 리다이렉트
- 변경: `/main`으로 이동하면서 쿼리 파라미터로 상태 전달

```javascript
// Before
if (is_new_user) {
  router.replace('/survey')
} else {
  router.replace('/main')
}

// After
if (is_new_user || is_dev_user) {
  router.replace('/main?showSurvey=true')
} else {
  router.replace('/main')
}
```

### Phase 3: main 페이지 수정

**파일**: `medication-frontend/src/app/main/page.jsx`

- URL 쿼리 파라미터 `showSurvey=true` 감지
- 감지 시 자동으로 SurveyModal 표시
- 표시 후 URL에서 파라미터 제거 (clean URL)

```javascript
'use client'
import { useSearchParams, useRouter } from 'next/navigation'

// 컴포넌트 내부
const searchParams = useSearchParams()
const router = useRouter()

useEffect(() => {
  if (searchParams.get('showSurvey') === 'true') {
    setShowSurvey(true)
    // Clean URL
    router.replace('/main', { scroll: false })
  }
}, [searchParams])
```

---

## 데이터 플로우 (수정 후)

```
[로그인 시도] --> {로그인 타입?}
                    |
                    |--(Dev 로그인)--> Backend: is_dev_user=true 반환
                    |                      |
                    |                      v
                    |--(Kakao 로그인)--> {신규 유저?}
                                           |
                                           |--(Yes)--> Backend: is_new_user=true 반환
                                           |                 |
                                           |                 v
                                           |            Callback: /main?showSurvey=true로 이동
                                           |                 |
                                           |                 v
                                           |            Main: showSurvey 파라미터 감지
                                           |                 |
                                           |                 v
                                           |            SurveyModal 자동 표시
                                           |                 |
                                           |                 v
                                           |            URL 파라미터 제거
                                           |
                                           |--(No)--> Backend: is_new_user=false 반환
                                                          |
                                                          v
                                                     Callback: /main으로 이동
                                                          |
                                                          v
                                                     Main: 일반 화면 표시
```

---

## 체크리스트

### Phase 1: Backend
- [x] `oauth_routers.py`에서 dev 로그인 또는 신규 유저일 때 `?showSurvey=true` 쿼리 파라미터 추가
- [ ] 기존 테스트 통과 확인

### Phase 2: Frontend Callback
- [x] 백엔드에서 직접 리다이렉트하므로 프론트엔드 콜백 수정 불필요

### Phase 3: Frontend Main
- [x] `main/page.jsx`에 useSearchParams 훅 추가
- [x] showSurvey 파라미터 감지 로직 추가
- [x] URL 클린업 로직 추가
- [x] Suspense boundary 추가 (useSearchParams 필수 요구사항)

### Phase 4: 테스트
- [ ] Dev 로그인 -> 설문 팝업 표시 확인
- [ ] 신규 Kakao 유저 -> 설문 팝업 표시 확인
- [ ] 기존 Kakao 유저 -> 설문 팝업 미표시 확인

---

## 대안 검토

### 대안 A: localStorage 사용 (선택하지 않음)
- 장점: URL이 깔끔함
- 단점: 브라우저 간 동기화 불가, 개발자 도구로 조작 가능

### 대안 B: 쿼리 파라미터 사용 (선택)
- 장점: 상태 명확, SSR 호환, 디버깅 용이
- 단점: URL에 잠시 파라미터 노출 (바로 제거됨)

---

## 예상 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `app/apis/v1/oauth_routers.py` | is_dev_user 플래그 추가 |
| `medication-frontend/src/app/auth/kakao/callback/page.jsx` | 리다이렉트 로직 수정 |
| `medication-frontend/src/app/main/page.jsx` | useSearchParams로 자동 팝업 |

