"""Unit tests for app.services.chat.ingredient_mapper."""

from __future__ import annotations

import pytest

from app.services.chat.ingredient_mapper import (
    _normalize_brand,
    format_ingredient_mapping_section,
)


class TestNormalizeBrand:
    """_normalize_brand - OCR 노이즈 제거."""

    def test_strips_known_noise_suffix(self) -> None:
        assert _normalize_brand("타이레놀(이럴때퍼지매칭을하지)") == "타이레놀"

    def test_keeps_first_part_before_paren(self) -> None:
        assert _normalize_brand("아이리스점안액(수출명 : 블루아이점안액)(1회용)") == "아이리스점안액"

    def test_keeps_first_part_before_comma(self) -> None:
        assert _normalize_brand("나조린점안액(1회용),나조린점안액") == "나조린점안액"

    def test_trims_whitespace(self) -> None:
        assert _normalize_brand("  타이레놀  ") == "타이레놀"

    def test_plain_name_unchanged(self) -> None:
        assert _normalize_brand("타이레놀") == "타이레놀"


class TestFormatIngredientMappingSection:
    """format_ingredient_mapping_section - LLM context markdown 조립."""

    def test_empty_mapping_returns_empty(self) -> None:
        assert format_ingredient_mapping_section({}) == ""

    def test_single_brand_with_one_ingredient(self) -> None:
        section = format_ingredient_mapping_section({"타이레놀": ["아세트아미노펜"]})
        assert section == "[용어 매핑]\n- 타이레놀 → 성분: 아세트아미노펜"

    def test_single_brand_with_multiple_ingredients(self) -> None:
        section = format_ingredient_mapping_section({"낙소졸정": ["나프록센", "에스오메프라졸"]})
        assert "[용어 매핑]" in section
        assert "낙소졸정 → 성분: 나프록센, 에스오메프라졸" in section

    def test_brand_without_ingredient_marked_failed(self) -> None:
        section = format_ingredient_mapping_section({"미등록약": []})
        assert "미등록약 → 성분 매핑 실패" in section

    def test_mixed_mapped_and_unmapped(self) -> None:
        section = format_ingredient_mapping_section({"타이레놀": ["아세트아미노펜"], "이상한약": []})
        assert "타이레놀 → 성분: 아세트아미노펜" in section
        assert "이상한약 → 성분 매핑 실패" in section


@pytest.fixture
def stub_connection(monkeypatch: pytest.MonkeyPatch):
    """tortoise.connections 의 execute_query_dict 를 stub."""
    captured: dict[str, object] = {"sql": None, "params": None}
    rows: list[dict[str, str]] = []

    class _FakeConn:
        async def execute_query_dict(self, sql: str, params):
            captured["sql"] = sql
            captured["params"] = params
            return rows

    def _set_rows(new_rows: list[dict[str, str]]) -> None:
        rows.clear()
        rows.extend(new_rows)

    from app.services.chat import ingredient_mapper

    monkeypatch.setattr(
        ingredient_mapper.connections,
        "get",
        lambda _name: _FakeConn(),
    )
    return captured, _set_rows


class TestMapBrandsToIngredients:
    """map_brands_to_ingredients - SQL lookup."""

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty(self) -> None:
        from app.services.chat.ingredient_mapper import map_brands_to_ingredients

        assert await map_brands_to_ingredients([]) == {}

    @pytest.mark.asyncio
    async def test_blank_strings_filtered(self) -> None:
        from app.services.chat.ingredient_mapper import map_brands_to_ingredients

        assert await map_brands_to_ingredients(["", " ", None]) == {}  # type: ignore[list-item]

    @pytest.mark.asyncio
    async def test_brand_to_ingredient_mapping(
        self,
        stub_connection: tuple[dict[str, object], object],
    ) -> None:
        from app.services.chat.ingredient_mapper import map_brands_to_ingredients

        _captured, set_rows = stub_connection
        set_rows([
            {"brand": "타이레놀", "mtral_name": "아세트아미노펜"},
            {"brand": "낙소졸정500/20밀리그램", "mtral_name": "나프록센"},
            {"brand": "낙소졸정500/20밀리그램", "mtral_name": "에스오메프라졸"},
        ])

        result = await map_brands_to_ingredients(["타이레놀", "낙소졸정500/20밀리그램(나프록센,에스오메프라졸)"])
        # 원본 brand 키 보존 (정규화 전 이름)
        assert "타이레놀" in result
        assert "낙소졸정500/20밀리그램(나프록센,에스오메프라졸)" in result
        assert result["타이레놀"] == ["아세트아미노펜"]
        # 정규화로 '낙소졸정500/20밀리그램' 매칭됨
        assert "나프록센" in result["낙소졸정500/20밀리그램(나프록센,에스오메프라졸)"]

    @pytest.mark.asyncio
    async def test_unmatched_brand_returns_empty_list(
        self,
        stub_connection: tuple[dict[str, object], object],
    ) -> None:
        from app.services.chat.ingredient_mapper import map_brands_to_ingredients

        _captured, set_rows = stub_connection
        set_rows([])  # SQL 매칭 실패

        result = await map_brands_to_ingredients(["미등록약"])
        assert result == {"미등록약": []}
