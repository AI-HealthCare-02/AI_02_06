# AI Healthcare System Design

이 문서는 AI 헬스케어 시스템의 기술적 설계 세부사항을 다룹니다.

---

## 데이터베이스 설계

### 핵심 테이블 스키마
```sql
-- 계정 관리
CREATE TABLE accounts (
    id SERIAL PRIMARY KEY,
    kakao_id VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE profiles (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    nickname VARCHAR(50) NOT NULL,
    profile_image TEXT,
    birth_date DATE,
    gender VARCHAR(10),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE refresh_tokens (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES accounts(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 복용약 관리
CREATE TABLE medications (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    dosage VARCHAR(50),
    frequency VARCHAR(50),
    start_date DATE,
    end_date DATE,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE intake_logs (
    id SERIAL PRIMARY KEY,
    medication_id INTEGER REFERENCES medications(id) ON DELETE CASCADE,
    taken_at TIMESTAMP NOT NULL,
    status VARCHAR(20) DEFAULT 'taken',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- AI 기능
CREATE TABLE chat_sessions (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(200),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'user' or 'assistant'
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE llm_response_cache (
    id SERIAL PRIMARY KEY,
    input_hash VARCHAR(64) UNIQUE NOT NULL,
    response TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 챌린지 시스템
CREATE TABLE challenges (
    id SERIAL PRIMARY KEY,
    profile_id INTEGER REFERENCES profiles(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    difficulty VARCHAR(20) DEFAULT 'medium',
    progress INTEGER DEFAULT 0,
    target INTEGER NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 인덱싱 전략
```sql
-- 성능 최적화를 위한 인덱스
CREATE INDEX idx_accounts_kakao_id ON accounts(kakao_id);
CREATE INDEX idx_profiles_account_id ON profiles(account_id);
CREATE INDEX idx_refresh_tokens_account_id ON refresh_tokens(account_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);

CREATE INDEX idx_medications_profile_id ON medications(profile_id);
CREATE INDEX idx_intake_logs_medication_id ON intake_logs(medication_id);
CREATE INDEX idx_intake_logs_taken_at ON intake_logs(taken_at);

CREATE INDEX idx_chat_sessions_profile_id ON chat_sessions(profile_id);
CREATE INDEX idx_messages_session_id ON messages(session_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

CREATE INDEX idx_llm_response_cache_input_hash ON llm_response_cache(input_hash);
CREATE INDEX idx_challenges_profile_id ON challenges(profile_id);
```

---

## API 성능 규칙 및 기준

### 응답 시간 요구사항
- **P95 Latency < 3초**: 95%의 요청이 3초 이내 응답 완료
- **P99 Latency < 5초**: 99%의 요청이 5초 이내 응답 완료
- **평균 응답 시간 < 1초**: 일반적인 API 요청의 평균 처리 시간

### 엔드포인트별 성능 기준

| 엔드포인트 | 목표 응답 시간 | 최대 허용 시간 | 비고 |
|------------|----------------|----------------|------|
| `/api/v1/health` | < 100ms | < 500ms | 헬스체크 |
| `/api/v1/auth/*` | < 500ms | < 2초 | 인증 관련 |
| `/api/v1/profiles/*` | < 300ms | < 1초 | 프로필 CRUD |
| `/api/v1/medications/*` | < 500ms | < 2초 | 복용약 관리 |
| `/api/v1/ocr/analyze` | < 10초 | < 30초 | OCR 처리 (비동기) |
| `/api/v1/chat/*` | < 2초 | < 5초 | 채팅 응답 |

### 성능 모니터링 지표
- **처리량**: 초당 요청 수 (RPS)
- **동시 연결**: 최대 100개 동시 요청 처리
- **에러율**: < 1% (5xx 에러 기준)
- **가용성**: 99.5% 이상 (월 기준)

### API 설계 원칙
```yaml
RESTful API 설계:
  GET: 데이터 조회 (멱등성 보장)
  POST: 새 리소스 생성
  PATCH: 부분 업데이트
  DELETE: 리소스 삭제

HTTP 상태 코드:
  200: 성공
  201: 생성 성공
  400: 잘못된 요청
  401: 인증 실패
  403: 권한 없음
  404: 리소스 없음
  429: 요청 제한 초과
  500: 서버 오류
```

---

## 비동기 처리 성능 최적화

### AI 추론 비동기화
```python
# OCR + RAG 파이프라인 처리 시간
처리 단계별 시간:
  - 이미지 전처리: 평균 0.5초
  - OCR API 호출: 평균 3-8초
  - 텍스트 정제: 평균 0.2초
  - 약품명 매칭: 평균 0.5초
  - 텍스트 청킹: 평균 0.3초
  - RAG 생성: 평균 5-15초
  - 후처리: 평균 0.5초
  - 총 처리 시간: 평균 10-30초
```

### I/O 작업 최적화 전략
```python
# 비동기 처리 구현
async def process_ocr_request(image_data: bytes) -> dict:
    # 1. 비동기 파일 저장
    async with aiofiles.open(temp_path, 'wb') as f:
        await f.write(image_data)

    # 2. 비동기 외부 API 호출
    async with httpx.AsyncClient() as client:
        response = await client.post(ocr_api_url, files=files)

    # 3. 비동기 데이터베이스 저장
    await OCRResult.create(
        user_id=user_id,
        result=response.json(),
        processed_at=datetime.now()
    )

    return response.json()
```

### 리소스 사용 효율 개선
- **메모리 사용률**: 평균 60% 이하 유지
- **CPU 사용률**: 평균 70% 이하 유지
- **동시 처리**: FastAPI + Uvicorn 워커 기반
- **커넥션 풀**: PostgreSQL 최대 20개 연결
- **Redis 연결**: 최대 10개 연결 풀

---

## 보안 정책 및 규칙

### JWT 토큰 정책
```yaml
Access Token:
  - 유효 기간: 60분
  - 알고리즘: HS256
  - 클레임: user_id, exp, iat, token_type
  - 저장 위치: Authorization 헤더
  - 형식: "Bearer <token>"

Refresh Token:
  - 유효 기간: 14일
  - 저장 위치: HttpOnly 쿠키
  - 자동 갱신: Access Token 만료 시
  - 보안 옵션: Secure, SameSite=Strict
  - 해시 저장: SHA-256으로 해시 후 DB 저장
```

### Rate Limiting 상세 규칙
```yaml
IP별 요청 제한:
  일반 GET 요청:
    - 제한: 200회/60초
    - 버스트: 250회 (10초간)

  변경 요청 (POST/PATCH/DELETE):
    - 제한: 30회/60초
    - 버스트: 40회 (10초간)

  인증 엔드포인트:
    - 제한: 10회/60초
    - 버스트: 15회 (10초간)

  OCR 요청:
    - 제한: 5회/60초
    - 버스트: 없음

제한 초과 시 처리:
  - HTTP 429 응답
  - Retry-After 헤더 포함
  - 로그 기록 및 알림
  - 일시적 IP 차단 (심각한 경우)
```

### 보안 미들웨어 설정
```python
# 공격 패턴 탐지
ATTACK_PATTERNS = [
    (r"\.\.[\\/]", "path_traversal"),
    (r"%00", "null_byte_injection"),
    (r"<script", "xss_attempt"),
    (r"javascript:", "javascript_injection"),
    (r"(union|select|insert|delete|update|drop)\s", "sql_injection")
]

# 보안 헤더
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
}
```

### HTTPS 및 암호화 정책
```yaml
SSL/TLS 설정:
  - 지원 버전: TLS 1.2, TLS 1.3
  - 암호화 스위트: ECDHE-RSA-AES256-GCM-SHA384
  - 키 교환: ECDHE (Perfect Forward Secrecy)
  - 인증서: Let's Encrypt (자동 갱신)
  - HSTS: 1년 (includeSubDomains)

데이터 암호화:
  - 저장 데이터: AES-256 암호화
  - 전송 데이터: TLS 1.3
  - 비밀번호: bcrypt (cost=12)
  - API 키: 환경 변수로 관리
```

---

## AI 모델 성능 규칙

### 결과 일관성 기준
```yaml
동일 입력 테스트 프로토콜:
  - 반복 횟수: 10회 이상
  - 허용 편차: 텍스트 유사도 95% 이상
  - 응답 시간 편차: ±20% 이내
  - 성공률: 95% 이상
  - 테스트 주기: 주 1회
```

### OCR 성능 지표 및 최적화
```yaml
CLOVA OCR 성능:
  정확도 목표:
    - 한글 텍스트: 90% 이상
    - 숫자: 95% 이상
    - 영문: 85% 이상

  처리 시간:
    - 이미지당 평균: 3-8초
    - 최대 허용: 30초
    - 타임아웃: 45초

  지원 형식:
    - 이미지: JPG, PNG (최대 10MB)
    - 문서: PDF (최대 10MB, 5페이지)
    - 해상도: 최소 300DPI 권장

  전처리 최적화:
    - 이미지 크기 조정: 최대 2048x2048
    - 노이즈 제거: Gaussian blur
    - 대비 향상: CLAHE 적용
```

### RAG 생성 성능 지표
```yaml
OpenAI GPT 설정:
  모델 선택:
    - 개발환경: gpt-4o-mini (비용 최적화)
    - 운영환경: gpt-4o (품질 최적화)

  토큰 관리:
    - 입력 제한: 4000토큰
    - 출력 제한: 2000토큰
    - 컨텍스트 윈도우: 128k토큰

  품질 관리:
    - 응답 품질: 의료진 검토 80% 이상 적절성
    - 생성 시간: 평균 5-15초
    - 할루시네이션 방지: 소스 기반 답변 강제
    - 안전성 필터: OpenAI Moderation API 적용
```

### 모델 A/B 테스트 프레임워크
```yaml
A/B 테스트 설정:
  실험 설계:
    - 트래픽 분할: 50:50 (Control vs Treatment)
    - 테스트 기간: 최소 7일 (통계적 유의성 확보)
    - 샘플 크기: 최소 1000건

  평가 지표:
    - 주요 지표: 응답 시간, 정확도, 사용자 만족도
    - 보조 지표: 토큰 사용량, 에러율, 재시도율

  통계적 검증:
    - 유의수준: α = 0.05
    - 검정력: β = 0.8
    - 효과 크기: 최소 5% 개선

  배포 전략:
    - Canary 배포: 5% → 25% → 50% → 100%
    - 롤백 조건: 에러율 2% 초과 시 즉시 롤백
```

---

## 사용자 피드백 및 개선 체계

### 피드백 수집 아키텍처
```yaml
피드백 데이터 모델:
  message_feedbacks:
    - message_id: 메시지 식별자
    - rating: 1-5 점수 또는 좋음/나쁨
    - feedback_text: 자유 텍스트 피드백
    - category: 정확성, 유용성, 이해도 등
    - created_at: 피드백 시간

  ocr_corrections:
    - ocr_result_id: OCR 결과 식별자
    - original_text: 원본 OCR 결과
    - corrected_text: 사용자 수정 텍스트
    - correction_type: 추가, 삭제, 수정
    - created_at: 수정 시간

  usage_analytics:
    - user_id: 사용자 식별자
    - action: 수행한 액션
    - context: 액션 컨텍스트
    - duration: 소요 시간
    - success: 성공 여부
```

### 개선 프로세스 자동화
```python
# 피드백 분석 파이프라인
class FeedbackAnalyzer:
    def analyze_weekly_feedback(self):
        # 1. 피드백 데이터 수집
        feedbacks = self.collect_feedback_data()

        # 2. 패턴 분석
        patterns = self.identify_patterns(feedbacks)

        # 3. 우선순위 결정
        priorities = self.calculate_priority_scores(patterns)

        # 4. 개선 제안 생성
        improvements = self.generate_improvement_suggestions(priorities)

        # 5. 자동 알림
        self.notify_development_team(improvements)

        return improvements
```

### 지속적 개선 KPI
```yaml
피드백 관련 KPI:
  수집률:
    - 목표: 전체 상호작용 대비 20% 이상
    - 측정: 일일/주간/월간 피드백 수집률

  반영률:
    - 목표: 수집된 피드백의 80% 이상 검토
    - 측정: 피드백 → 개선사항 전환율

  성능 개선:
    - 목표: 월 단위 성능 지표 5% 이상 개선
    - 측정: 정확도, 응답시간, 사용자 만족도

  응답 시간:
    - 목표: 피드백 접수 후 48시간 내 1차 검토
    - 측정: 평균 응답 시간, SLA 준수율
```

---

## 시스템 확장성 및 용량 계획

### 현재 시스템 용량 분석
```yaml
EC2 t3.medium 리소스 분석:
  하드웨어 제약:
    - CPU: 2 vCPU (버스트 크레딧: 24 크레딧/시간)
    - Memory: 4GB RAM
    - Storage: 30GB EBS gp3 (3000 IOPS)
    - Network: 최대 5 Gbps (버스트)

  예상 처리 용량:
    - 동시 사용자: 50-100명
    - 일일 API 요청: 10,000-20,000건
    - 일일 OCR 요청: 500-1,000건
    - 일일 채팅 메시지: 2,000-5,000건
    - DB 연결: 최대 20개 동시 연결
```

### 성능 모니터링 및 알림
```yaml
모니터링 지표:
  시스템 리소스:
    - CPU 사용률: 80% 이상 시 경고, 90% 이상 시 위험
    - Memory 사용률: 85% 이상 시 경고, 95% 이상 시 위험
    - Disk 사용률: 80% 이상 시 경고, 90% 이상 시 위험
    - Network I/O: 대역폭 80% 이상 시 경고

  애플리케이션 성능:
    - 응답 시간: P95 > 3초 지속 시 경고
    - 에러율: 1% 이상 지속 시 경고, 5% 이상 시 위험
    - 처리량: 기준 대비 50% 감소 시 경고
    - 큐 대기: Redis 큐 100개 이상 적체 시 경고
```

### 확장 전략 로드맵
```yaml
단계별 확장 계획:
  Phase 1 - 수직 확장 (즉시 적용 가능):
    - EC2 인스턴스: t3.medium → t3.large
    - 메모리: 4GB → 8GB
    - 예상 용량: 동시 사용자 200명

  Phase 2 - 데이터베이스 분리 (1-2개월):
    - RDS PostgreSQL 도입
    - 읽기 전용 복제본 추가
    - 연결 풀링 최적화

  Phase 3 - 수평 확장 (3-6개월):
    - Application Load Balancer 도입
    - 다중 EC2 인스턴스 (2-3개)
    - ElastiCache Redis 클러스터
    - 세션 스토어 외부화

  Phase 4 - 마이크로서비스 (6-12개월):
    - AI Worker 서비스 분리
    - API Gateway 도입
    - 서비스 메시 (Istio/Linkerd)
    - 분산 추적 (Jaeger/Zipkin)
```

### 비용 최적화 전략
```yaml
비용 효율성 계획:
  현재 비용 구조:
    - EC2 t3.medium: $30/월
    - EBS 30GB: $3/월
    - 데이터 전송: $5/월
    - 총 예상 비용: $40/월

  확장 시 비용 예측:
    - Phase 1: $80/월 (2x 성능)
    - Phase 2: $150/월 (RDS 추가)
    - Phase 3: $300/월 (수평 확장)
    - Phase 4: $500/월 (마이크로서비스)

  비용 최적화 방안:
    - Reserved Instance 활용 (30-50% 절약)
    - Spot Instance 활용 (개발/테스트 환경)
    - CloudWatch 기반 Auto Scaling
    - 사용하지 않는 리소스 자동 정리
```

---

## 모니터링 및 로깅 전략

### 로깅 아키텍처
```yaml
로그 레벨별 정책:
  DEBUG:
    - 용도: 개발 환경 디버깅
    - 내용: 함수 호출, 변수 값, 실행 경로
    - 보관: 1일

  INFO:
    - 용도: 정상적인 시스템 동작 기록
    - 내용: API 요청/응답, 사용자 액션
    - 보관: 7일

  WARNING:
    - 용도: 주의가 필요한 상황
    - 내용: 성능 저하, 재시도, 임계값 근접
    - 보관: 30일

  ERROR:
    - 용도: 오류 상황 기록
    - 내용: 예외 발생, API 실패, DB 오류
    - 보관: 90일

  CRITICAL:
    - 용도: 시스템 장애 상황
    - 내용: 서비스 중단, 보안 침해
    - 보관: 1년
```

### 구조화된 로깅 형식
```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "INFO",
  "service": "fastapi",
  "module": "auth.oauth",
  "function": "kakao_login",
  "user_id": "user_12345",
  "request_id": "req_abcd1234",
  "message": "User login successful",
  "duration_ms": 245,
  "metadata": {
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "endpoint": "/api/v1/auth/kakao/callback"
  }
}
```

### 성능 메트릭 수집
```yaml
애플리케이션 메트릭:
  HTTP 요청:
    - 요청 수 (카운터)
    - 응답 시간 (히스토그램)
    - 상태 코드별 분포 (카운터)
    - 엔드포인트별 통계 (게이지)

  데이터베이스:
    - 쿼리 실행 시간 (히스토그램)
    - 연결 풀 사용률 (게이지)
    - 슬로우 쿼리 수 (카운터)
    - 트랜잭션 롤백 수 (카운터)

  AI 모델:
    - OCR 처리 시간 (히스토그램)
    - RAG 생성 시간 (히스토그램)
    - 모델 호출 성공률 (게이지)
    - 토큰 사용량 (카운터)
```

### 알림 및 대응 체계
```yaml
알림 규칙:
  즉시 알림 (Critical):
    - 서비스 다운 (5분 이상)
    - 에러율 10% 이상
    - 응답 시간 P95 > 10초
    - 디스크 사용률 95% 이상

  경고 알림 (Warning):
    - CPU 사용률 80% 이상 (10분)
    - 메모리 사용률 85% 이상 (5분)
    - 에러율 5% 이상 (5분)
    - 응답 시간 P95 > 5초 (5분)

  정보 알림 (Info):
    - 일일 사용량 리포트
    - 주간 성능 요약
    - 월간 비용 리포트
    - 보안 이벤트 요약
```
