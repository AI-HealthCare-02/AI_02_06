# 심화 플로우차트 (멘토 피드백 반영)

> 기초 플로우차트(`FLOWCHART.md`)와 겹치지 않는 **기술 깊이** 중심 문서입니다.  
> 이미지 저장 전략 · 배치 임베딩 · 멀티턴 챗봇 세 가지를 다룹니다.

---

## 목차
1. [OCR 심화 — 이미지 저장·전처리·후처리·DB 매칭](#1-ocr-심화) `AS-IS / TO-BE`
2. [임베딩 배치 — 47,000건 초기 적재 파이프라인](#2-임베딩-배치) `신규 기능`
3. [챗봇 심화 — 멀티턴·컨텍스트 관리·세션 전략](#3-챗봇-심화--멀티턴) `AS-IS / TO-BE`

---

## 1. OCR 심화

### AS-IS

> **현재 상태**: 전처리 없이 원본 이미지를 바로 Clova OCR에 전달, 이미지는 로컬 /tmp에만 임시 저장

```mermaid
flowchart TD
    INPUT(["👤 사용자가 처방전 사진 업로드"])

    INPUT --> VALIDATE{"파일 검증<br />(형식: jpg·png·webp<br />크기: 5MB 이하)"}
    VALIDATE -- "❌ 실패" --> ERR_VAL["⚠️ 오류 안내 후 재업로드 요청"]
    VALIDATE -- "✅ 통과" --> S_LOCAL["📁 로컬 임시 저장<br />/tmp/ocr_images/<br />처리 중에만 유지"]

    S_LOCAL --> OCR["🔍 Clova OCR API 호출<br />원본 이미지 그대로 전달<br />(전처리 없음)"]
    OCR --> OCR_RESULT{"OCR 성공?"}
    OCR_RESULT -- "❌ 실패" --> ERR_OCR["⚠️ 다시 찍어주세요"]
    OCR_RESULT -- "✅ 성공" --> LLM["🤖 GPT-4o-mini 호출<br />Structured Outputs으로<br />약품명·복용법 구조화<br />오타 자동 보정"]

    LLM --> LLM_RESULT{"약품 정보<br />추출됐나?"}
    LLM_RESULT -- "❌ 없음" --> ERR_OCR
    LLM_RESULT -- "✅ 있음" --> REDIS["💾 Redis 임시 저장<br />key: ocr_draft:{draft_id}<br />TTL: 10분"]

    REDIS --> CLEANUP["🗑️ 로컬 임시 이미지 삭제"]
    CLEANUP --> RESULT(["📋 결과 화면으로 이동"])

    ERR_OCR --> ERR_VAL

    style S_LOCAL fill:#fefce8,stroke:#eab308,color:#713f12
    style OCR fill:#f0fdf4,stroke:#22c55e,color:#14532d
    style LLM fill:#f5f3ff,stroke:#7c3aed,color:#581c87
```

**AS-IS 문제점**
- 사진이 어둡거나 기울어진 경우 OCR 인식률 저하
- 서버 재시작 시 /tmp 파일 유실 위험
- DB 약품 매칭 없이 OCR 결과만 반환

---

### TO-BE

> **읽는 포인트**: 이미지가 어디에 어떻게 저장되는지, 전처리·후처리가 각각 무슨 역할인지 확인하세요.

```mermaid
flowchart TD
    INPUT(["👤 사용자가 처방전 사진 업로드"])

    INPUT --> VALIDATE{"파일 검증<br />(형식: jpg·png·webp<br />크기: 5MB 이하)"}
    VALIDATE -- "❌ 실패" --> ERR_VAL["⚠️ 오류 안내 후 재업로드 요청"]
    VALIDATE -- "✅ 통과" --> STORAGE

    subgraph STORAGE ["📦 이미지 저장 전략"]
        direction LR
        S_LOCAL["로컬 임시 저장<br />/tmp/ocr_images/<br />(처리 중에만 유지)"]
        S_NOTE["💡 현재: 로컬 임시 저장<br />처리 완료 즉시 삭제<br /><br />TO-BE: AWS S3 업로드<br />버킷: prescription-images/<br />경로: {user_id}/{uuid}.jpg<br />처리 완료 후 S3에서도 삭제"]
        S_LOCAL -.->|"개선 방향"| S_NOTE
    end

    VALIDATE --> S_LOCAL
    S_LOCAL --> PREPROCESS

    subgraph PREPROCESS ["🖼️ 전처리 (Pre-processing)"]
        direction TB
        P_NOTE["💡 현재: 전처리 없음<br />원본 이미지 그대로 Clova OCR 전달<br /><br />TO-BE: OpenCV 적용"]
        P1["① 그레이스케일 변환<br />컬러 → 흑백 (노이즈 감소)"]
        P2["② 이진화 (Thresholding)<br />글자/배경 명확히 분리"]
        P3["③ 기울기 보정 (Deskewing)<br />사진이 삐뚤어졌을 때 자동 수평 맞춤"]
        P4["④ 노이즈 제거<br />얼룩·그림자 최소화"]

        P_NOTE --> P1 --> P2 --> P3 --> P4
    end

    PREPROCESS --> OCR_CALL

    subgraph OCR_CALL ["🔍 OCR 엔진 호출"]
        O1["Clova OCR API 호출<br />(네이버 클라우드)"]
        O2{"API 응답 성공?"}
        O3["⚠️ OCR 실패<br />타임아웃 or API 오류"]
        O4["원문 텍스트 추출<br />fields[].inferText 조합"]

        O1 --> O2
        O2 -- "❌" --> O3
        O2 -- "✅" --> O4
    end

    O3 --> ERR_VAL

    subgraph POSTPROCESS ["✨ 후처리 (Post-processing)"]
        direction TB
        PP1["① GPT-4o-mini 호출<br />Structured Outputs 형식"]
        PP2["오타 자동 보정<br />'타이레뉼' → '타이레놀'"]
        PP3["필드별 구조화<br />약품명 / 복용량 / 횟수 / 일수 / 시점"]
        PP4{"약품 정보가<br />추출됐나?"}
        PP5["⚠️ 인식 실패<br />다시 찍어달라고 안내"]

        PP1 --> PP2 --> PP3 --> PP4
        PP4 -- "❌" --> PP5
    end

    O4 --> POSTPROCESS

    subgraph DB_MATCH ["🗄️ DB 매칭"]
        direction TB
        DB1["medicine_info 테이블에서<br />약품명 조회<br />(정확도 매칭)"]
        DB2{"DB에 해당 약품이<br />등록돼 있나?"}
        DB3["✅ DB 정보로 보완<br />효능·부작용·분류 자동 채움"]
        DB4["❓ 미등록 약품<br />OCR 추출 정보만 사용<br />(수동 입력 유도)"]

        DB1 --> DB2
        DB2 -- "✅ 있음" --> DB3
        DB2 -- "❌ 없음" --> DB4
    end

    PP4 -- "✅" --> DB_MATCH

    DB3 --> REDIS["💾 Redis 임시 저장<br />key: ocr_draft:{draft_id}<br />TTL: 10분"]
    DB4 --> REDIS
    REDIS --> CLEANUP["🗑️ 임시 이미지 삭제<br />(로컬 or S3에서 제거)"]
    CLEANUP --> RESULT(["📋 결과 화면으로 이동<br />사용자가 내용 확인·수정"])

    style STORAGE fill:#fefce8,stroke:#eab308,color:#713f12
    style PREPROCESS fill:#eff6ff,stroke:#3b82f6,color:#1e3a8a
    style OCR_CALL fill:#f0fdf4,stroke:#22c55e,color:#14532d
    style POSTPROCESS fill:#f5f3ff,stroke:#7c3aed,color:#581c87
    style DB_MATCH fill:#fff7ed,stroke:#f97316,color:#7c2d12
```

---

## 2. 임베딩 배치

> **읽는 포인트**: 47,000건을 한 번에 처리하면 메모리가 터집니다. 청킹·제너레이터로 어떻게 나눠 처리하는지 보세요.

```mermaid
flowchart TD
    TRIGGER(["⚡ 배치 임베딩 트리거"])

    subgraph TRIGGER_METHOD ["트리거 방법 (택 1)"]
        direction LR
        T1["🖥️ 수동 실행<br />python scripts/embed_batch.py<br />(초기 1회 적재 시)"]
        T2["⏰ 스케줄 실행<br />Cron Job (매일 새벽 3시)<br />신규 약품만 증분 처리"]
        T3["📡 API 트리거<br />관리자 버튼 클릭<br />→ RQ 작업 큐에 등록"]
    end

    TRIGGER --> TRIGGER_METHOD
    TRIGGER_METHOD --> LOAD

    subgraph LOAD ["📥 데이터 로드"]
        L1["medicine_info 테이블 전체 조회<br />총 47,000건"]
        L2{"이미 임베딩된<br />항목 제외<br />(embedding IS NOT NULL)"}
        L3["처리 대상 목록 확정<br />(신규 or 갱신 필요 항목만)"]

        L1 --> L2 --> L3
    end

    LOAD --> CHUNK

    subgraph CHUNK ["✂️ 청킹 (메모리 이슈 해결)"]
        direction TB
        C_WHY["❗ 47,000건을 한 번에 올리면<br />RAM 부족으로 OOM(메모리 부족) 발생<br />→ 100건씩 잘라서 처리"]
        C1["제너레이터(Generator)로<br />100건씩 yield<br />전체를 메모리에 올리지 않음"]
        C2["배치 1: 1~100번<br />배치 2: 101~200번<br />배치 N: ..."]

        C_WHY --> C1 --> C2
    end

    CHUNK --> EMBED_LOOP

    subgraph EMBED_LOOP ["🔄 배치 반복 처리"]
        direction TB
        E1["배치 1개 꺼냄 (100건)"]
        E2["텍스트 조합<br />약품명 + 효능 + 부작용 + 주의사항"]
        E3["OpenAI Embeddings API 호출<br />model: text-embedding-3-small<br />input: 100건 한 번에 전송"]
        E4{"API 성공?"}
        E5["⚠️ 실패 시 3회 재시도<br />지수 백오프 (1s→2s→4s)"]
        E6["128차원 벡터 100개 반환"]
        UPSERT["업설트 처리"]
        E7{"다음 배치<br />있나?"}
        E8(["✅ 전체 완료<br />47,000건 임베딩 적재 완료"])

        E1 --> E2 --> E3 --> E4
        E4 -- "❌" --> E5 --> E3
        E4 -- "✅" --> E6 --> UPSERT --> E7
        E7 -- "✅ 있음" --> E1
        E7 -- "❌ 없음" --> E8
    end

    subgraph UPSERT ["💾 업설트 로직"]
        direction LR
        U1{"medicine_info 테이블에<br />해당 ID가 이미 있나?"}
        U2["UPDATE<br />embedding 컬럼만 덮어씀<br />(기존 약품 정보 유지)"]
        U3["INSERT<br />새 행 추가"]

        U1 -- "✅ 있음" --> U2
        U1 -- "❌ 없음" --> U3
    end

    subgraph MONITOR ["📊 진행 상황 모니터링"]
        direction LR
        M1["처리된 건수 로깅<br />[INFO] Batch 10/470 완료 (1000/47000건)"]
        M2["실패 건수 별도 파일 기록<br />failed_ids.txt → 수동 재처리"]
        M3["완료 시 슬랙·이메일 알림 (선택)"]
    end

    EMBED_LOOP --> MONITOR

    style TRIGGER_METHOD fill:#fefce8,stroke:#eab308,color:#713f12
    style CHUNK fill:#fef2f2,stroke:#ef4444,color:#7f1d1d
    style EMBED_LOOP fill:#f0fdf4,stroke:#22c55e,color:#14532d
    style UPSERT fill:#eff6ff,stroke:#3b82f6,color:#1e3a8a
    style MONITOR fill:#f5f3ff,stroke:#7c3aed,color:#581c87
```

---

## 3. 챗봇 심화 — 멀티턴

### AS-IS

> **현재 상태**: 매 질문이 독립적으로 처리됨 — 이전 대화 맥락 없이 RAG + 현재 질문만 GPT에 전달

```mermaid
flowchart TD
    U_START(["👤 사용자가 챗봇 페이지 열기"])

    U_START --> INPUT["⌨️ 궁금한 점 입력<br />예: '이 약 졸리나요?'"]
    INPUT --> EMB["질문을 벡터로 변환<br />(OpenAI 임베딩)"]

    EMB --> SEARCH["pgvector 코사인 유사도 검색<br />관련 약품 정보 최대 3개"]
    SEARCH --> CONTEXT["참고 자료(Context) 텍스트 생성"]

    CONTEXT --> GPT["🤖 GPT-4o-mini 호출<br />시스템 프롬프트 + Context<br />+ 현재 질문만 전달<br />(이전 대화 기록 없음)"]

    GPT --> RESULT{"답변 생성 성공?"}
    RESULT -- "✅ 성공" --> SHOW["💬 답변 화면에 표시"]
    RESULT -- "❌ 실패" --> ERR["⚠️ 잠시 후 다시 말씀해 주세요"]

    SHOW --> NEXT{"더 물어볼 것이 있나요?"}
    NEXT -- "✅ 예" --> INPUT
    NEXT -- "❌ 아니오" --> END(["대화 종료<br />(대화 기록 보존 없음)"])

    style GPT fill:#ede9fe,stroke:#7c3aed,color:#1e1b4b
    style ERR fill:#fef2f2,stroke:#ef4444
```

**AS-IS 문제점**
- "아까 말한 약"처럼 이전 맥락을 참고하는 질문에 대답 불가
- 대화를 닫으면 내용이 사라져 이어서 대화 불가
- 세션 구분이 없어 약별 대화 이력 관리 불가

---

### TO-BE

> **읽는 포인트**: 대화가 쌓일수록 GPT에 넘기는 토큰이 늘어납니다. 컨텍스트 창이 꽉 찰 때 어떻게 자르는지가 핵심입니다.

```mermaid
flowchart TD
    START(["👤 사용자가 챗봇 화면 열기"])

    START --> SESSION

    subgraph SESSION ["💬 세션 관리 전략"]
        direction TB
        SE1{"기존 세션이<br />있나?"}
        SE2["✅ 기존 세션 불러오기<br />DB에서 이전 대화 기록 조회"]
        SE3["➕ 새 세션 생성<br />chat_sessions 테이블에 행 추가<br />account_id + profile_id 연결"]
        SE4["세션 화면 표시<br />이전 대화 내역 렌더링"]

        SE1 -- "✅ 있음" --> SE2 --> SE4
        SE1 -- "❌ 없음" --> SE3 --> SE4
    end

    START --> SESSION
    SE4 --> INPUT["⌨️ 사용자가 새 메시지 입력"]
    INPUT --> SAVE_MSG["📝 메시지 DB 저장<br />messages 테이블<br />role: user / content: 입력 내용"]

    SAVE_MSG --> HISTORY

    subgraph HISTORY ["📚 대화 기록 불러오기 (멀티턴 핵심)"]
        direction TB
        H1["현재 세션의 전체 대화 기록 조회<br />messages 테이블에서 시간순 정렬"]
        H2["각 메시지를 GPT 형식으로 변환<br />{role: user/assistant, content: ...}"]
        H3["전체 토큰 수 계산<br />(tiktoken 라이브러리 활용)"]

        H1 --> H2 --> H3
    end

    H3 --> TOKEN_CHECK

    subgraph TOKEN_CHECK ["⚖️ 컨텍스트 초과 처리"]
        direction TB
        TC1{"전체 토큰 수가<br />한도(예: 6,000)를<br />초과하나?"}
        TC2["✅ 한도 이내<br />전체 기록 그대로 사용"]
        TC3["오래된 대화부터 제거<br />(슬라이딩 윈도우 방식)<br />최근 N턴만 유지"]
        TC4{"그래도 초과?"}
        TC5["가장 오래된 1턴 추가 제거<br />반복"]
        TC6["최종 컨텍스트 확정"]

        TC1 -- "✅ 이내" --> TC2 --> TC6
        TC1 -- "❌ 초과" --> TC3 --> TC4
        TC4 -- "❌ 아직 초과" --> TC5 --> TC4
        TC4 -- "✅ 해결" --> TC6
    end

    TC6 --> RAG

    subgraph RAG ["🧠 RAG 파이프라인"]
        direction TB
        R1["최신 메시지로 임베딩 생성"]
        R2["pgvector 코사인 유사도 검색<br />관련 약품 정보 최대 3개"]
        R3["참고 자료(Context) 텍스트 생성"]

        R1 --> R2 --> R3
    end

    R3 --> GPT_CALL

    subgraph GPT_CALL ["🤖 GPT 호출 구성"]
        direction TB
        G1["시스템 프롬프트<br />'다약(Dayak)' 약사 캐릭터 설정<br />+ RAG Context 삽입"]
        G2["멀티턴 대화 기록 삽입<br />[{role:user,...}, {role:assistant,...}, ...]"]
        G3["현재 질문 추가<br />{role: user, content: 현재 입력}"]
        G4["GPT-4o-mini 호출<br />temperature: 0.7 / max_tokens: 800"]

        G1 --> G2 --> G3 --> G4
    end

    GPT_CALL --> RESULT{"답변<br />생성 성공?"}

    RESULT -- "✅ 성공" --> SAVE_REPLY["📝 AI 답변 DB 저장<br />messages 테이블<br />role: assistant"]
    RESULT -- "❌ 실패" --> ERR["⚠️ '잠시 후 다시<br />말씀해 주세요' 안내<br />(DB 저장 안 함)"]

    SAVE_REPLY --> DISPLAY["💬 화면에 답변 표시"]
    DISPLAY --> CONTINUE{"계속 대화?"}
    CONTINUE -- "✅ 예" --> INPUT
    CONTINUE -- "❌ 종료" --> END(["세션 유지 (DB에 기록 보존)<br />나중에 다시 이어서 대화 가능"])

    subgraph SESSION_LIFECYCLE ["🔄 세션 생명주기"]
        direction LR
        SL1(["ACTIVE<br />대화 중"])
        SL2(["CLOSED<br />사용자가 종료"])
        SL3(["EXPIRED<br />30일 미사용 자동 만료"])

        SL1 -- "종료 버튼" --> SL2
        SL1 -- "30일 경과" --> SL3
    end

    style SESSION fill:#eff6ff,stroke:#3b82f6,color:#1e3a8a
    style HISTORY fill:#f0fdf4,stroke:#22c55e,color:#14532d
    style TOKEN_CHECK fill:#fef2f2,stroke:#ef4444,color:#7f1d1d
    style RAG fill:#f5f3ff,stroke:#7c3aed,color:#581c87
    style GPT_CALL fill:#fefce8,stroke:#eab308,color:#713f12
    style SESSION_LIFECYCLE fill:#fff7ed,stroke:#f97316,color:#7c2d12
```

---

## 핵심 기술 포인트 요약

| 구분 | 핵심 결정 사항 | 이유 |
|------|--------------|------|
| **OCR 이미지 저장** | 로컬 임시 → TO-BE: S3 | 서버 재시작 시 파일 유실 방지 |
| **OCR 전처리** | 현재 없음 → TO-BE: OpenCV | 사진 품질이 낮을 때 인식률 향상 |
| **배치 청킹** | 100건 단위 제너레이터 | 47,000건 한 번에 올리면 OOM 발생 |
| **임베딩 업설트** | INSERT or UPDATE 분기 | 중복 삽입 방지 + 기존 데이터 보존 |
| **멀티턴 컨텍스트** | 슬라이딩 윈도우 (오래된 것부터 제거) | GPT 토큰 한도(128k) 초과 방지 |
| **세션 관리** | DB 영구 저장 + 30일 만료 | 앱 종료 후에도 대화 이어가기 가능 |
