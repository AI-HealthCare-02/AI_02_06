# Kakao OAuth Mock Data

카카오 소셜 로그인 개발/테스트용 Mock 데이터입니다.

---

## 파일 구조 및 역할

| 파일 | 소비자 | 설명 |
|---|---|---|
| `kakao_auth_codes.json` | **FE 담당자** | 백엔드 콜백 엔드포인트로 전달할 인가코드 |
| `kakao_token_responses.json` | **API 담당자** | 가짜 카카오 서버의 토큰 교환 응답 |
| `kakao_userinfo_responses.json` | **API 담당자** | 가짜 카카오 서버의 유저정보 응답 |
| `app_accounts.json` | **API 담당자** | 우리 서비스 DB 가상 데이터 (accounts + profiles) |

---

## OAuth 플로우와 파일 매핑

```
[FE] 카카오 로그인 버튼 클릭
  └─ kakao_auth_codes.json 의 code 사용
       ↓
[백엔드] POST https://kauth.kakao.com/oauth/token (인가코드 → 토큰 교환)
  └─ kakao_token_responses.json 으로 응답 mocking
       ↓
[백엔드] GET https://kapi.kakao.com/v2/user/me (유저정보 조회)
  └─ kakao_userinfo_responses.json 으로 응답 mocking
       ↓
[백엔드] 우리 DB에서 provider_account_id로 Account 조회
  └─ app_accounts.json 의 accounts 배열로 DB mocking
```

---

## 시나리오별 예상 결과

| scenario | 인가코드 | 토큰교환 | 유저정보 | DB조회 | 최종 결과 |
|---|---|---|---|---|---|
| `existing_user` | | 200 | 200 | 존재 + is_active=true | **로그인 성공 → JWT 발급** |
| `new_user` | | 200 | 200 | 없음 | **회원가입 프로세스 진입** |
| `no_email_user` | | 200 | email 없음 | - | **400 이메일 필수값 누락** |
| `unlinked_user` | | 200 | 401 | - | **401 카카오 연결 끊김** |
| `deactivated_user` | | 200 | 200 | 존재 + is_active=false | **423 비활성화 계정** |
| `expired_code` | | 400 KOE320 | - | - | **400 인가코드 만료** |

---

## FE 사용법

콜백 URL에 `code` 쿼리파라미터로 전달:

```
GET /auth/kakao/callback?code=mock_auth_code_existing_user_abc123
```

각 시나리오 테스트 시 `kakao_auth_codes.json`의 `code` 값을 교체하여 사용.

---

## API 담당자 사용법 (pytest fixture 예시)

```python
# conftest.py
import json
from pathlib import Path

MOCK_DIR = Path(__file__).parent / "mock_data"

@pytest.fixture
def kakao_token_responses():
    return {r["scenario"]: r for r in json.loads((MOCK_DIR / "kakao_token_responses.json").read_text())["responses"]}

@pytest.fixture
def kakao_userinfo_responses():
    return {r["scenario"]: r for r in json.loads((MOCK_DIR / "kakao_userinfo_responses.json").read_text())["responses"]}

@pytest.fixture
def app_accounts():
    return json.loads((MOCK_DIR / "app_accounts.json").read_text())
```
