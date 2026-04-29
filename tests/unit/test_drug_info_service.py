"""Unit tests for MedicationService._get_drug_info — DB 검색 기반 (LLM 호출 없음).

PLAN_DRUG_INFO_DB.md — drug-info 응답이 더 이상 LLM 호출이 아니라 MedicineInfo
테이블 검색으로 채워져야 한다. NULL/miss 시 빈 배열, interactions 항상 빈 배열
(컬럼 없음).
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.services.medication_service import MedicationService


@pytest.fixture
def service() -> MedicationService:
    return MedicationService()


def _mock_medicine_info(
    *,
    medicine_name: str = "타이레놀정500mg",
    precautions: str | None = None,
    side_effects: str | None = None,
) -> MagicMock:
    info = MagicMock()
    info.medicine_name = medicine_name
    info.precautions = precautions
    info.side_effects = side_effects
    return info


# ── DB hit 케이스 ────────────────────────────────────────────────────────────


async def test_db_exact_match_splits_precautions_into_warnings(
    service: MedicationService,
) -> None:
    """precautions TEXT 의 줄바꿈을 list[str] 로 분할해 warnings 에 채운다."""
    info = _mock_medicine_info(
        precautions="임산부는 신중히 투여\n간 기능 저하 환자 주의\n공복 복용 금지",
    )
    with patch(
        "app.services.medication_service.MedicineInfoRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_name = AsyncMock(return_value=info)
        mock_repo.search_by_name = AsyncMock()

        result = await service._get_drug_info("타이레놀정500mg")

    assert result.warnings == [
        "임산부는 신중히 투여",
        "간 기능 저하 환자 주의",
        "공복 복용 금지",
    ]
    mock_repo.search_by_name.assert_not_awaited()


async def test_db_exact_match_splits_side_effects(
    service: MedicationService,
) -> None:
    info = _mock_medicine_info(side_effects="두통\n어지러움\n구역")
    with patch(
        "app.services.medication_service.MedicineInfoRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_name = AsyncMock(return_value=info)

        result = await service._get_drug_info("타이레놀정500mg")

    assert result.side_effects == ["두통", "어지러움", "구역"]


async def test_db_hit_with_null_columns_returns_empty_lists(
    service: MedicationService,
) -> None:
    """precautions/side_effects 가 NULL 이어도 응답 자체는 정상 (빈 list)."""
    info = _mock_medicine_info(precautions=None, side_effects=None)
    with patch(
        "app.services.medication_service.MedicineInfoRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_name = AsyncMock(return_value=info)

        result = await service._get_drug_info("타이레놀정500mg")

    assert result.warnings == []
    assert result.side_effects == []
    assert result.medicine_name == "타이레놀정500mg"


async def test_db_hit_with_blank_lines_filtered(
    service: MedicationService,
) -> None:
    """줄바꿈 split 시 빈 줄/공백만 있는 줄은 제외."""
    info = _mock_medicine_info(precautions="A\n\n  \nB\n\n")
    with patch(
        "app.services.medication_service.MedicineInfoRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_name = AsyncMock(return_value=info)

        result = await service._get_drug_info("타이레놀정500mg")

    assert result.warnings == ["A", "B"]


# ── ILIKE fallback ──────────────────────────────────────────────────────────


async def test_falls_back_to_search_by_name_when_exact_miss(
    service: MedicationService,
) -> None:
    """정확 매칭 실패 시 ILIKE search_by_name 의 첫 결과 사용."""
    fuzzy_hit = _mock_medicine_info(
        medicine_name="타이레놀정500밀리그람",
        precautions="공복 복용 금지",
    )
    with patch(
        "app.services.medication_service.MedicineInfoRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo.search_by_name = AsyncMock(return_value=[fuzzy_hit])

        result = await service._get_drug_info("타이레놀")

    mock_repo.get_by_name.assert_awaited_once_with("타이레놀")
    mock_repo.search_by_name.assert_awaited_once()
    assert result.warnings == ["공복 복용 금지"]


# ── 매칭 실패 케이스 ─────────────────────────────────────────────────────────


async def test_no_match_returns_empty_response(
    service: MedicationService,
) -> None:
    """get_by_name / search_by_name 모두 미일치 → 빈 응답 (HTTPException 아님)."""
    with patch(
        "app.services.medication_service.MedicineInfoRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo.search_by_name = AsyncMock(return_value=[])

        result = await service._get_drug_info("존재하지않는약")

    assert result.medicine_name == "존재하지않는약"
    assert result.warnings == []
    assert result.side_effects == []
    assert result.interactions == []


# ── interactions 정책 ────────────────────────────────────────────────────────


async def test_interactions_always_empty(
    service: MedicationService,
) -> None:
    """DB 에 interactions 컬럼이 없으므로 응답은 항상 빈 배열."""
    info = _mock_medicine_info(precautions="A", side_effects="B")
    with patch(
        "app.services.medication_service.MedicineInfoRepository",
    ) as mock_repo_cls:
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_name = AsyncMock(return_value=info)

        result = await service._get_drug_info("타이레놀정500mg")

    assert result.interactions == []


# ── LLM 코드 의존성 제거 검증 ────────────────────────────────────────────────


def test_module_no_longer_imports_openai() -> None:
    """medication_service 모듈이 더 이상 openai/json/os 를 LLM 용도로 import 하지 않음."""
    import app.services.medication_service as svc_module

    assert not hasattr(svc_module, "AsyncOpenAI"), "AsyncOpenAI 가 여전히 import 됨 — LLM 호출 코드가 남아있을 가능성"


async def test_does_not_call_llm_even_when_db_miss(
    service: MedicationService,
) -> None:
    """DB miss 시에도 LLM fallback 없음 — 그냥 빈 응답."""
    with (
        patch("app.services.medication_service.MedicineInfoRepository") as mock_repo_cls,
        patch.dict("os.environ", {"OPENAI_API_KEY": "sk-fake"}),
    ):
        mock_repo = mock_repo_cls.return_value
        mock_repo.get_by_name = AsyncMock(return_value=None)
        mock_repo.search_by_name = AsyncMock(return_value=[])

        # OpenAI client 가 import 되어 있다면 이 시점에 호출되어야 했지만,
        # 우리 변경 후엔 import 자체가 없어야 함
        result = await service._get_drug_info(f"randomdrug-{uuid4()}")

    assert result.warnings == []
