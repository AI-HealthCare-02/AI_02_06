# OCR 처방전 인식 전체 흐름

## 플로우차트

```mermaid
flowchart TD
    A([사용자: 처방전 촬영/업로드]) --> B[/ocr 페이지\n이미지 선택 및 미리보기]

    B --> C{파일 선택됨?}
    C -- 아니오 --> B
    C -- 예 --> D[SessionStorage에 파일 임시 저장\nocrFileData / ocrFileName / ocrFileType]

    D --> E[/ocr/loading 페이지\n로딩 스켈레톤 + 진행 단계 표시]

    E --> F[POST /api/v1/ocr/extract\nmultipart/form-data]

    subgraph BACKEND_PHASE1 [백엔드 - PHASE 1]
        F --> G{파일 검증\n형식: jpeg/png/webp\n크기: 5MB 이하}
        G -- 실패 --> H[400 에러 반환]
        G -- 통과 --> I[Clova OCR 호출\n이미지 → 원문 텍스트]
        I -- OCR 실패 --> H
        I -- 성공 --> J[GPT-4o-mini 호출\nStructured Outputs\n원문 → 약품 정보 JSON 파싱]
        J -- 파싱 실패\n또는 약품 없음 --> H
        J -- 성공 --> K[Redis 임시 저장\nkey: ocr_draft:{draft_id}\nTTL: 10분]
        K --> L[draft_id 반환]
    end

    H --> M[/ocr?error=... 로 리다이렉트\n오류 메시지 표시]
    L --> N[SessionStorage 파일 데이터 삭제\n분석 완료 오버레이 표시]
    N --> O[/ocr/result?draft_id={id} 로 이동]

    subgraph BACKEND_PHASE2 [백엔드 - PHASE 2]
        O --> P[GET /api/v1/ocr/draft/{draft_id}]
        P --> Q{Redis에 데이터 있음?}
        Q -- 없음\n만료 또는 미존재 --> R[404 반환]
        Q -- 있음 --> S[약품 목록 반환]
    end

    R --> T[알림 후 /ocr 페이지로 리다이렉트]
    S --> U[/ocr/result 페이지\n약품 카드 목록 표시\n사용자가 내용 수정/삭제]

    U --> V{확정 버튼 클릭}
    V --> W[POST /api/v1/ocr/confirm]

    subgraph BACKEND_PHASE3 [백엔드 - PHASE 3]
        W --> X[Redis 원자적 삭제\ndelete == 0 이면 중복 요청 차단]
        X --> Y[medications 테이블 DB 저장\ntotal_intake_count = daily × total_days]
        Y --> Z[즉시 201 응답 반환]
        Z --> AA[[BackgroundTasks\nGPT-4o-mini 복약 가이드 생성\n5~15초 소요]]
    end

    Z --> AB[저장 완료\n/main 페이지로 이동]

    style BACKEND_PHASE1 fill:#f0f4ff,stroke:#9ab
    style BACKEND_PHASE2 fill:#f0fff4,stroke:#9ba
    style BACKEND_PHASE3 fill:#fff8f0,stroke:#ba9
    style AA fill:#fffbe6,stroke:#d4a
```

## 단계별 요약

| 단계 | 페이지/엔드포인트 | 역할 |
|------|-----------------|------|
| PHASE 1 | `POST /ocr/extract` | 이미지 → OCR → LLM 파싱 → Redis 임시 저장 |
| PHASE 2 | `GET /ocr/draft/{id}` | Redis에서 임시 데이터 조회 → 사용자 수정 |
| PHASE 3 | `POST /ocr/confirm` | DB 영구 저장 + 복약 가이드 백그라운드 생성 |

## 핵심 설계 포인트

- **Redis 임시 저장 (TTL 10분)**: OCR 결과를 세션 대신 서버 측에서 관리해 보안 강화
- **원자적 삭제로 중복 방지**: `redis.delete()` 반환값이 0이면 이미 처리된 요청으로 차단
- **BackgroundTasks 분리**: 복약 가이드 생성(5~15초)을 응답 이후 처리해 UX 개선
- **SessionStorage 활용**: 페이지 이동 시 파일 데이터를 임시 보관 후 즉시 삭제
