# API의 이해: 시스템 간 소통의 모든 것

---

## 1. API란 무엇인가? "식당의 웨이터"

**API(Application Programming Interface)**는 서로 다른 프로그램이 소통하기 위한 **약속된 규격**입니다.

* **비유:** 식당에서 손님(FE)이 주방(BE)에 직접 들어가지 않고, **웨이터(API)**를 통해 주문하고 음식을 받는 것과 같습니다.
* **핵심:** 손님은 주방의 복잡한 조리 과정을 몰라도 되고, 주방은 손님이 누구인지 신경 쓰지 않아도 됩니다. 오직 **메뉴판(API 명세서)**에 정의된 대로만 주문하면 됩니다.

---

## 2. HTTP 통신의 기초: "우편 시스템"

### **HTTP란?**
인터넷에서 데이터를 주고받는 **우편 시스템**입니다. 모든 API 요청은 HTTP라는 배달 트럭을 타고 이동합니다.

### **HTTP 요청의 구성 요소**

| 구성 요소 | 비유 | 설명 |
| :--- | :--- | :--- |
| **URL** | 배송 주소 | 요청이 도착할 목적지 (`/api/v1/auth/login`) |
| **Method** | 우편물 종류 | 조회(GET), 생성(POST), 수정(PUT), 삭제(DELETE) |
| **Headers** | 봉투 겉면 | 보내는 사람 신분증(JWT), 내용물 형식(JSON) 등 메타 정보 |
| **Body** | 편지 내용물 | 실제 전달할 데이터 (로그인 정보, 처방전 이미지 등) |

### **HTTP 응답의 구성 요소**

| 구성 요소 | 비유 | 설명 |
| :--- | :--- | :--- |
| **Status Code** | 배송 결과 | 성공(200), 생성됨(201), 잘못된 요청(400), 인증 실패(401), 서버 오류(500) |
| **Headers** | 수신 확인서 | 쿠키 설정, 캐시 정책 등 |
| **Body** | 답장 내용 | 요청에 대한 결과 데이터 (사용자 정보, 에러 메시지 등) |

### **주요 HTTP Method**

| Method | 용도 | 비유 | Body 유무 |
| :--- | :--- | :--- | :--- |
| **GET** | 데이터 조회 | 도서관에서 책 빌리기 | X |
| **POST** | 데이터 생성 | 새 책 기증하기 | O |
| **PUT** | 데이터 전체 수정 | 책 전체 내용 교체 | O |
| **PATCH** | 데이터 일부 수정 | 책 오타만 수정 | O |
| **DELETE** | 데이터 삭제 | 책 폐기 | X |

---

## 3. 네 가지 관점에서 본 API

### **3.1 FE(Frontend) 관점: "손님"**

FE는 사용자와 직접 마주하는 **접점**입니다. API를 통해 BE에 데이터를 요청하고, 받은 데이터를 화면에 그립니다.

```
[사용자] → [FE: 버튼 클릭] → [API 요청] → [BE] → [API 응답] → [FE: 화면 업데이트]
```

**FE가 API를 사용하는 방식:**
1. **Axios/Fetch:** HTTP 요청을 보내는 도구 (우체국)
2. **Interceptor:** 모든 요청에 자동으로 신분증(JWT)을 첨부하는 장치
3. **Error Handling:** 응답 코드에 따라 적절한 UI 피드백 제공

**예시 코드:**
```javascript
// FE에서 로그인 API 호출
const response = await api.get('/api/v1/auth/kakao/callback', {
  params: { code, state }
})
// 성공 시 메인 페이지로 이동
router.replace('/main')
```

---

### **3.2 BE(Backend) 관점: "주방"**

BE는 비즈니스 로직을 처리하는 **두뇌**입니다. FE의 요청을 받아 검증하고, DB와 소통하며, 적절한 응답을 반환합니다.

**BE의 계층 구조 (레이어드 아키텍처):**

| 계층 | 역할 | 비유 |
| :--- | :--- | :--- |
| **Router (`apis/`)** | HTTP 요청 수신, 응답 반환 | 접수 창구 |
| **DTO (`dtos/`)** | 요청/응답 데이터 검증 | 서류 검수 담당 |
| **Service (`services/`)** | 비즈니스 로직 처리 | 실무 담당자 |
| **Repository (`repositories/`)** | DB 접근 추상화 | 서류 보관함 관리자 |
| **Model (`models/`)** | DB 테이블 정의 | 서류 양식 |

**데이터 흐름:**
```
[FE 요청] → Router → DTO(검증) → Service(로직) → Repository → DB
                                                    ↓
[FE 응답] ← Router ← DTO(직렬화) ← Service ← Repository ← DB
```

**예시 코드:**
```python
# Router: HTTP 요청 수신
@oauth_router.get("/kakao/callback")
async def kakao_callback(code: str, state: str):
    # Service: 비즈니스 로직 위임
    account, is_new = await oauth_service.kakao_callback(code)
    # Repository를 통해 토큰 저장
    tokens = await oauth_service.issue_tokens(account)
    return OAuthLoginResponse(...)
```

---

### **3.3 AI(LLM, RAG) 관점: "전문 컨설턴트"**

AI Worker는 복잡한 분석 작업을 담당하는 **외부 전문가**입니다. BE가 직접 처리하기 어려운 작업을 위임받아 수행합니다.

**AI가 담당하는 작업:**
* **처방전 OCR:** 이미지에서 텍스트 추출
* **약물 상호작용 분석:** DUR(Drug Utilization Review) 검사
* **AI 채팅:** 복약 관련 질의응답 (RAG 기반)

**BE와 AI Worker의 통신 방식:**

```
[FE] → [BE API] → [메시지 큐/HTTP] → [AI Worker] → [LLM API]
                                          ↓
[FE] ← [BE API] ← [결과 저장/반환]  ← [AI Worker]
```

**RAG(Retrieval-Augmented Generation) 구조:**
```
1. 사용자 질문 수신
2. 벡터 DB에서 관련 문서 검색 (Retrieval)
3. 검색된 문서 + 질문을 LLM에 전달
4. LLM이 문서 기반으로 답변 생성 (Generation)
5. 응답 캐싱 후 반환
```

**비용 최적화:**
* **캐싱:** 동일한 질문은 DB에서 바로 반환 (`llm_response_cache`)
* **병용금기 캐시:** 이미 분석한 약물 조합은 재분석하지 않음 (`drug_interaction_cache`)

---

### **3.4 DB(Database) 관점: "창고"**

DB는 모든 데이터가 **영구 저장**되는 창고입니다. API의 최종 목적지이자 출발지입니다.

**우리 프로젝트의 DB 구조:**

| 테이블 | 용도 | 관계 |
| :--- | :--- | :--- |
| `accounts` | 로그인 계정 (소셜 OAuth) | 1:N → profiles, refresh_tokens |
| `profiles` | 건강 프로필 (본인 + 피보호자) | 1:N → medications, challenges |
| `medications` | 복용 약품 정보 | 1:N → intake_logs |
| `intake_logs` | 복용 기록 | N:1 → medications, profiles |
| `chat_sessions` | AI 상담 세션 | 1:N → messages |
| `messages` | 채팅 메시지 | N:1 → chat_sessions |
| `refresh_tokens` | 인증 토큰 관리 | N:1 → accounts |
| `drug_interaction_cache` | DUR 병용금기 캐시 | - |
| `llm_response_cache` | LLM 응답 캐시 | - |

**ORM과 실제 DB의 관계:**
```
Python 코드 (models/*.py)
        ↓ Tortoise ORM 변환
SQL 쿼리 (SELECT, INSERT...)
        ↓ asyncpg 드라이버
PostgreSQL 실행
```

---

## 4. 보안 관점: "성문과 신분증"

### **4.1 인증(Authentication): "넌 누구냐?"**

사용자가 **누구인지** 확인하는 과정입니다.

| 방식 | 설명 | 우리 프로젝트 |
| :--- | :--- | :--- |
| **OAuth 2.0** | 외부 서비스(카카오)에 인증 위임 | O |
| **JWT** | 서버가 발급한 디지털 신분증 | O |
| **Session** | 서버에 로그인 상태 저장 | X |

**JWT 구조:**
```
eyJhbGciOiJIUzI1NiIs...  (Header: 알고리즘)
.eyJ0eXBlIjoiYWNjZXNz...  (Payload: 사용자 정보, 만료 시간)
.d_j4GZ_-XZGRhKgF...      (Signature: 위조 방지 서명)
```

---

### **4.2 토큰 보안: "이중 잠금 금고"**

| 토큰 | 용도 | 저장 위치 | 유효 기간 |
| :--- | :--- | :--- | :--- |
| **Access Token** | API 요청 시 신분 증명 | HttpOnly 쿠키 | 60분 |
| **Refresh Token** | Access Token 재발급 | HttpOnly 쿠키 | 14일 |

**HttpOnly 쿠키의 삼중 보안:**
* **HttpOnly:** JavaScript가 쿠키를 읽지 못함 (XSS 방어)
* **Secure:** HTTPS에서만 전송 (도청 방어)
* **SameSite:** 다른 사이트에서 쿠키 전송 차단 (CSRF 방어)

---

### **4.3 RTR (Refresh Token Rotation): "일회용 마스터키"**

Refresh Token이 탈취되었을 때의 피해를 최소화하는 보안 기법입니다.

**동작 방식:**
```
1. Access Token 만료
2. Refresh Token으로 갱신 요청
3. 새 Access Token + 새 Refresh Token 발급
4. 기존 Refresh Token 즉시 무효화
```

**Grace Period (2초):**
* 동시에 여러 요청이 갈 때를 대비한 유예 시간
* 2초 내에는 구 토큰도 유효하게 처리

**탈취 감지:**
* Grace Period 초과 후 구 토큰 사용 시 → 403 Forbidden
* "누군가 당신의 토큰을 훔쳤을 수 있습니다"

---

### **4.4 CSRF 방지: "위조 명령 차단"**

**CSRF(Cross-Site Request Forgery):** 사용자가 모르는 사이에 악성 사이트가 우리 서버에 요청을 보내는 공격

**방어 방법 - HMAC State:**
```
1. BE가 서명된 state 생성: timestamp.nonce.signature
2. FE가 state를 저장하고 카카오로 전달
3. 카카오가 콜백 시 state 반환
4. BE가 서명 검증 + 만료 시간(5분) 확인
```

---

### **4.5 입력값 검증: "입구 경비원"**

**공격 패턴 차단 (400 응답):**
* Path Traversal: `../../../etc/passwd`
* Null Byte Injection: `%00`

**의심 패턴 로깅 (차단 안 함):**
* SQL Injection: `' OR 1=1 --`
* XSS: `<script>alert(1)</script>`

> ORM이 SQL Injection을 방어하므로, 의심 패턴은 로깅만 하고 차단하지 않습니다.

---

## 5. 전체 데이터 흐름 예시: "카카오 로그인"

```
[사용자]
    │ 1. 카카오 로그인 버튼 클릭
    ▼
[FE: login/page.tsx]
    │ 2. GET /api/v1/auth/kakao/config
    ▼
[BE: oauth_routers.py]
    │ 3. HMAC state 생성, 설정 반환
    ▼
[FE]
    │ 4. state 저장 → 카카오 로그인 페이지로 리다이렉트
    ▼
[카카오 서버]
    │ 5. 사용자 인증 → code + state와 함께 콜백
    ▼
[FE: callback/page.jsx]
    │ 6. state 검증 → GET /api/v1/auth/kakao/callback
    ▼
[BE: oauth_routers.py]
    │ 7. state 서명 검증 (CSRF 방지)
    │ 8. 카카오 서버에 code로 토큰 교환
    │ 9. 카카오 서버에서 사용자 정보 조회
    ▼
[BE: oauth_service.py]
    │ 10. 계정 조회/생성 (Repository → DB)
    │ 11. JWT 토큰 발급
    │ 12. Refresh Token DB 저장 (해시)
    ▼
[BE: oauth_routers.py]
    │ 13. HttpOnly 쿠키에 토큰 설정
    │ 14. 응답 반환
    ▼
[FE]
    │ 15. 메인 페이지로 이동
    ▼
[사용자]
    └── 로그인 완료!
```

---

## 6. 요약 테이블

| 관점 | 역할 | API와의 관계 | 비유 |
| :--- | :--- | :--- | :--- |
| **FE** | 사용자 인터페이스 | API 호출자 (소비자) | 손님 |
| **BE** | 비즈니스 로직 | API 제공자 (생산자) | 주방 |
| **AI** | 전문 분석 작업 | API를 통해 작업 위임받음 | 외부 컨설턴트 |
| **DB** | 데이터 영구 저장 | API의 최종 목적지/출발지 | 창고 |

---

## 7. 팀원들이 기억해야 할 핵심

> "API는 FE와 BE 사이의 **계약서**입니다.
> FE는 정해진 URL, Method, Body 형식대로 요청을 보내고,
> BE는 약속된 Status Code, Body 형식대로 응답합니다.
> 이 계약을 어기면 시스템이 멈춥니다.
>
> 보안은 **겹겹이 쌓는 것**입니다.
> 하나의 방어가 뚫려도 다음 방어가 막아줍니다.
> HttpOnly 쿠키 + RTR + CSRF State + 입력값 검증 = 안전한 시스템"

---
