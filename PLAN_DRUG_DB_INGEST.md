# PLAN — 식약처 ingest 파이프라인 재정비 + 컬럼 재구성 (P5-B)

## 0. 결정된 정책

| Q | 결정 |
|---|---|
| Q1 | **B (JSONB)** — `precautions` / `side_effects` 컬럼을 JSONB 로 변경 |
| Q2 | **식약처 10 카테고리 JSONB 로 raw 보존** + RAG 6 섹션 매핑은 medicine_chunk 청킹 레이어 (별도) |
| Q3 | **b** — `getDrugPrdtPrmsnDtlInq06` (현행) + `getDrugPrdtMcpnDtlInq07` (신규, 성분) |
| Q4 | **`dosage` 컬럼 신규 추가** + UD_DOC_DATA 평문화 + DTO 확장 |
| Q5 | **재파싱만** 테스트 (raw XML 이미 저장됨 — API 재호출 없이 파싱) |

## 1. 데이터 모델 변경

### 1.1 컬럼 변경 (`MedicineInfo`)
| 컬럼 | 변경 전 | 변경 후 |
|---|---|---|
| `precautions` | `TEXT` (NULL) | **`JSONField`** — 식약처 10 카테고리 dict (key 9개, "이상반응" 제외) |
| `side_effects` | `TEXT` (NULL) | **`JSONField`** — `list[str]` (이상반응 PARAGRAPH 들) |
| `dosage` | (없음) | **신규** `TEXT` — UD_DOC_DATA 평문화 결과 |

### 1.2 `precautions` JSONB 구조
```json
{
  "경고": ["...", "..."],
  "금기": ["...", "..."],
  "신중 투여": ["...", "..."],
  "일반적 주의": ["...", "..."],
  "임부에 대한 투여": ["...", "..."],
  "소아에 대한 투여": ["...", "..."],
  "고령자에 대한 투여": ["...", "..."],
  "과량투여시의 처치": ["...", "..."],
  "적용상의 주의": ["...", "..."]
}
```
- 키는 식약처 ARTICLE.title 의 숫자/공백 prefix 제거 후 정규화 (예: `"3. 신중히 투여할 것."` → `"신중 투여"`)
- "이상반응" 은 `precautions` 에 포함하지 않고 `side_effects` 로 분리
- 카테고리가 없으면 키 자체가 누락 (UI 가 빈 카테고리 표시 X)

### 1.3 aerich migration
- `precautions`: `TEXT → JSONB USING (precautions::jsonb)` (현재 NULL 이라 위험 없음)
- `side_effects`: 동일
- `dosage`: `ADD COLUMN ... TEXT NULL`

## 2. 파서 확장 (`app/services/medicine_doc_parser.py`)

### 2.1 신규 함수
```python
def parse_nb_categories(xml: str | None) -> tuple[dict[str, list[str]], list[str]]:
    """NB_DOC_DATA XML → (precautions dict, side_effects list).

    Returns:
        precautions: 식약처 카테고리(이상반응 제외) → PARAGRAPH list 매핑
        side_effects: 이상반응 PARAGRAPH list

    빈 입력 / 파싱 실패 → ({}, []).
    """

def parse_ud_plaintext(xml: str | None) -> str:
    """UD_DOC_DATA XML → 평문 문자열 (개행 결합).

    빈 입력 → ''.
    """

def normalize_nb_article_title(title: str) -> str | None:
    """'1. 경고' / '2.다음 환자에는 투여하지 말 것.' / '4. 이상반응' →
    '경고' / '금기' / '이상반응' 등 정규화. 매칭 실패 시 None.
    """
```

### 2.2 식약처 카테고리 정규화 매핑 (확정 표)
| Raw title 패턴 (regex) | 정규화 키 |
|---|---|
| `^\d+\.?\s*경고` | `경고` |
| `^\d+\.?\s*다음 환자에는 투여하지 말 것` | `금기` |
| `^\d+\.?\s*다음 환자에는 신중히 투여할 것` / `신중히 투여` | `신중 투여` |
| `^\d+\.?\s*이상반응` / `^\d+\.?\s*부작용` | (이상반응 — side_effects 로 분리) |
| `^\d+\.?\s*일반적 주의` | `일반적 주의` |
| `^\d+\.?\s*임부` | `임부에 대한 투여` |
| `^\d+\.?\s*소아` | `소아에 대한 투여` |
| `^\d+\.?\s*고령자` | `고령자에 대한 투여` |
| `^\d+\.?\s*과량` | `과량투여시의 처치` |
| `^\d+\.?\s*적용상` | `적용상의 주의` |
| (그 외 매칭 실패) | `None` — 무시 (로그) |

### 2.3 RAG 청킹용 6 섹션 매핑은 별도
`classify_article_section` 은 그대로 유지 (medicine_chunk 청크 분류용). 이번 작업과 무관.

## 3. ingest 변경 (`app/services/medicine_data_service.py`)

### 3.1 `_transform_item` 확장
```python
# Before
"efficacy": flatten_doc_plaintext(item.get("EE_DOC_DATA")),

# After
ee_text = flatten_doc_plaintext(item.get("EE_DOC_DATA"))
ud_text = parse_ud_plaintext(item.get("UD_DOC_DATA"))
precautions, side_effects = parse_nb_categories(item.get("NB_DOC_DATA"))

return {
    ...
    "efficacy": ee_text,
    "dosage": ud_text,
    "precautions": precautions,  # dict
    "side_effects": side_effects,  # list[str]
    ...
}
```

### 3.2 Mcpn07 (성분) ingest 신규
- 새 서비스 메서드 `sync_ingredients(full_sync: bool)` 또는 기존 `sync()` 안에 단계 추가
- API: `getDrugPrdtMcpnDtlInq07`
- 응답 → `MedicineIngredient` 1:N upsert (key: `(item_seq, mtral_sn)`)
- CLI: `python -m scripts.crawling.sync_medicine_data --include-ingredients` (또는 default 포함)

## 4. DTO 확장 (`app/dtos/drug_info.py`)

```python
class PrecautionSection(BaseModel):
    category: str  # "경고", "금기", "신중 투여", ...
    items: list[str]

class DrugInfoResponse(BaseModel):
    medicine_name: str
    warnings: list[PrecautionSection] = Field(default_factory=list)  # 식약처 카테고리별
    side_effects: list[str] = Field(default_factory=list)  # 이상반응
    dosage: str = ""  # 신규
    interactions: list[DrugInteraction] = Field(default_factory=list)  # 항상 [] (P5-B 범위 외)
    severe_reaction_advice: str = "심한 부작용이 나타나면 즉시 복용을 중단하고 의사와 상담하세요."
```

`warnings` 가 list 인 이유 — dict 보다 FE 가 순서·iteration 다루기 쉽고, JSON 응답에서도 카테고리 순서 보장.

## 5. drug-info 서비스 매핑 변경

```python
async def _get_drug_info(self, medicine_name: str) -> DrugInfoResponse:
    repo = MedicineInfoRepository()
    info = await repo.get_by_name(medicine_name) or _first_or_none(
        await repo.search_by_name(medicine_name, limit=1)
    )
    if info is None:
        return DrugInfoResponse(medicine_name=medicine_name)

    return DrugInfoResponse(
        medicine_name=info.medicine_name,
        warnings=[
            PrecautionSection(category=cat, items=items)
            for cat, items in (info.precautions or {}).items()
        ],
        side_effects=info.side_effects or [],
        dosage=info.dosage or "",
        interactions=[],
    )
```

## 6. FE 변경 (`medication-frontend/src/app/medication/[id]/page.jsx`)

### 6.1 "주의사항" 탭 — 카테고리별 그룹
```jsx
{drugInfo?.warnings?.length > 0 ? (
  drugInfo.warnings.map((section) => (
    <div key={section.category}>
      <h3 className="text-sm font-bold mb-2">{section.category}</h3>
      {section.items.map((item, i) => (
        <div key={i} className="flex gap-3 p-4 bg-yellow-50 rounded-xl">
          <AlertTriangle .../><p>{item}</p>
        </div>
      ))}
    </div>
  ))
) : (...)}
```

### 6.2 "용법" 탭 — dosage 텍스트 추가
기존 medication 의 dose_per_intake 등은 그대로 유지. 그 아래 `drugInfo.dosage` 평문 표시 (식약처 표준 용법) — 처방전 용법 + 식약처 표준 용법 이중 표시.

### 6.3 "부작용" / "상호작용" 탭
- 부작용: `drugInfo.side_effects` 그대로 (변경 없음 — list[str])
- 상호작용: 그대로 빈 배열 (P5-B 범위 외)

## 7. 재파싱 스크립트

`scripts/crawling/reparse_medicine_docs.py` (신규):

```python
async def reparse_all() -> None:
    """모든 medicine_info row 의 nb_doc_data / ud_doc_data 를 재파싱해
    precautions / side_effects / dosage 컬럼을 채운다 (raw XML 보존).

    멱등 — 재실행해도 결과 동일.
    """
    rows = await MedicineInfo.filter(
        nb_doc_data__isnull=False,  # raw 가 있는 row 만
    ).all()
    for row in rows:
        precautions, side_effects = parse_nb_categories(row.nb_doc_data)
        dosage = parse_ud_plaintext(row.ud_doc_data)
        await MedicineInfo.filter(id=row.id).update(
            precautions=precautions,
            side_effects=side_effects,
            dosage=dosage,
        )
```

CLI: `python -m scripts.crawling.reparse_medicine_docs`

## 8. 영향받는 파일 (Affected Files)

| 영역 | 파일 | 변경 |
|---|---|---|
| 모델 | `app/models/medicine_info.py` | precautions/side_effects → JSONField, dosage 추가 |
| 마이그레이션 | `migrations/models/<n>_*.py` | aerich generate |
| 파서 | `app/services/medicine_doc_parser.py` | parse_nb_categories / parse_ud_plaintext / normalize_nb_article_title 신규 |
| ingest | `app/services/medicine_data_service.py` | _transform_item 확장, sync_ingredients 신규 |
| ingest | `scripts/crawling/sync_medicine_data.py` | --include-ingredients 옵션 추가 (default 포함) |
| 재파싱 | `scripts/crawling/reparse_medicine_docs.py` | 신규 |
| DTO | `app/dtos/drug_info.py` | PrecautionSection 추가, DrugInfoResponse 확장 |
| 서비스 | `app/services/medication_service.py` | _get_drug_info 매핑 변경 |
| FE 페이지 | `medication-frontend/src/app/medication/[id]/page.jsx` | 주의사항 탭 카테고리 그룹 + 용법 탭 dosage |
| DBML | `docs/db_schema.dbml` | 컬럼 type 변경 반영 |

## 9. TDD 계획

### Step 1 — Tidy First (필요 시만)
- `medicine_doc_parser.py` 의 기존 함수 docstring/시그니처 정돈

### Step 2 — Test First (Red)
파일: `tests/unit/test_medicine_doc_parser.py` (신규)
1. `test_parse_nb_categories_classifies_10_articles` — 식약처 sample XML → dict + side_effects list 정확
2. `test_parse_nb_categories_excludes_adverse_from_precautions` — "4. 이상반응" 은 precautions 에 없고 side_effects 에만
3. `test_parse_nb_categories_normalizes_titles` — "1. 경고" / "2.다음 환자에는 투여하지 말 것." 정규화 확인
4. `test_parse_nb_categories_empty_input_returns_empty` — None / "" 입력
5. `test_parse_ud_plaintext_joins_paragraphs` — UD sample → 줄바꿈 결합
6. `test_normalize_nb_article_title_unknown_returns_none` — 매칭 실패 처리

파일: `tests/unit/test_medicine_data_service.py` (확장)
7. `test_transform_item_fills_precautions_and_side_effects` — sample item dict 입력 → transformed dict 검증

파일: `tests/unit/test_drug_info_service.py` (확장 — P5-A 후속)
8. `test_warnings_use_precaution_section_format` — info.precautions dict 가 list[PrecautionSection] 으로 응답
9. `test_dosage_passed_through` — info.dosage 가 응답에 그대로

### Step 3 — Implement (Green)
- aerich migration 생성·적용
- parser 확장
- service 확장
- DTO 확장
- _get_drug_info 매핑
- FE 카테고리 그룹 렌더링

### Step 4 — 재파싱 실행 (검증)
- `uv run python -m scripts.crawling.reparse_medicine_docs`
- 일부 row 샘플 확인 (DB query 로 precautions JSONB / side_effects / dosage 채워졌는지)

### Step 5 — Mcpn07 ingest 추가
- 새 메서드 + CLI 옵션
- 통합 테스트는 어려움 → unit test (transform 함수만)

## 10. Commit 분리 전략 (Single Responsibility)

| # | Commit | 내용 |
|---|---|---|
| 1 | `feat(medicine-info): NB/UD 파싱으로 precautions/side_effects/dosage 채움 + JSONB migration` | 모델 + migration + parser + service + tests |
| 2 | `feat(drug-info): PrecautionSection 카테고리별 응답 + dosage 추가` | DTO + medication_service 매핑 + tests |
| 3 | `feat(medication-detail): 주의사항 카테고리 그룹 UI + 용법 식약처 표준 추가` | FE 페이지 |
| 4 | `chore(data): medicine_info raw XML 재파싱 스크립트` | reparse_medicine_docs.py |
| 5 | `feat(medicine-ingredient): Mcpn07 ingest 추가` | sync 확장 |
| 6 | `chore(lint): test_medication_repository ASCII 변수명 정정` | P6 분리 작업 |

## 11. 트레이드오프

| 결정 | 장점 | 비용 |
|---|---|---|
| TEXT → JSONB | UI 카테고리 그룹 자연. 추가 컬럼 X. 식약처 raw 보존 | aerich migration 필요. JSONField 인덱스 만들려면 추가 작업 |
| `warnings: list[PrecautionSection]` (vs dict) | iteration 순서 보장. FE map 자연 | 클라이언트가 카테고리로 바로 lookup 어려움 (필요 시 reduce) |
| 신규 dosage 컬럼 | 향후 UI/RAG 재사용 | TEXT 1개 추가, 평문화 비용 |
| Mcpn07 추가 | medicine_ingredient 채움. 성분 검색·필터 가능 | API 호출 추가, ingest 시간 ↑ |

## 12. 검증 시나리오 (수동)

### 시나리오 A — 재파싱 후 응답
1. 재파싱 스크립트 실행
2. DB query: `SELECT precautions, side_effects, dosage FROM medicine_info WHERE medicine_name LIKE '대한포도당주사액%' LIMIT 1;` → JSONB / list / TEXT 모두 채워짐
3. drug-info GET 호출 → response 의 warnings 가 카테고리별 list, side_effects 가 이상반응 list, dosage 가 평문

### 시나리오 B — FE 표시
1. 약품 상세 진입 → 주의사항 탭
2. 카테고리별 헤딩 (경고/금기/신중 투여/...) 와 그 아래 박스들 그룹 표시
3. 용법 탭에 처방전 용법 + 식약처 표준 용법 이중 표시
4. 부작용 탭에 이상반응 list

### 시나리오 C — DB miss (FE 회귀)
1. 매칭 실패 약품 — 모든 탭이 "정보 없음" 표시 (변경 없음, 빈 배열 그대로)

### 시나리오 D — Mcpn07
1. `--include-ingredients` 로 sync 실행
2. `SELECT * FROM medicine_ingredient WHERE item_seq = '195700004';` → 성분 row 들 채워짐

## 13. Goal & 완료 기준
- [ ] `precautions` JSONB / `side_effects` JSONB list / `dosage` TEXT 채워짐
- [ ] 재파싱 스크립트로 기존 raw row 처리 (API quota 0)
- [ ] DTO `warnings: list[PrecautionSection]` + `dosage: str` 응답
- [ ] FE 주의사항 탭 카테고리 그룹 렌더링
- [ ] `medicine_ingredient` 테이블 채워짐 (Mcpn07 ingest)
- [ ] tests 모두 GREEN / Ruff PASS / ESLint 0 errors
- [ ] aerich migration apply 정상

---

**다음 단계**: 사용자 `go` 후 Step 2 (Test First) 부터 시작. Commit 6개 분리.
