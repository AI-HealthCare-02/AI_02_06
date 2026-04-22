"""Tests for the MedicineInfo model schema.

Verifies that the MedicineInfo Tortoise ORM model reflects the redesigned
schema (name, ingredient, usage, disclaimer, contraindicated_drugs/foods,
and a vector(768) embedding column) driven by medicines.json.
"""

# ruff: noqa: SLF001
from tortoise import fields

from app.db.vector_field import VectorField
from app.models.medicine_info import MedicineInfo
from app.services.rag.config import EMBEDDING_DIMENSIONS


class TestMedicineInfoSchema:
    """Tests for MedicineInfo field definitions."""

    def test_table_name(self) -> None:
        """Table name should be the agreed `medicine_info`."""
        assert MedicineInfo._meta.db_table == "medicine_info"

    def test_has_required_fields(self) -> None:
        """Model must expose all redesigned fields."""
        field_map = MedicineInfo._meta.fields_map
        required = {
            "id",
            "name",
            "ingredient",
            "usage",
            "disclaimer",
            "contraindicated_drugs",
            "contraindicated_foods",
            "embedding",
            "embedding_normalized",
            "created_at",
            "updated_at",
        }
        assert required.issubset(field_map.keys())

    def test_name_is_unique_charfield(self) -> None:
        """`name` must be a unique CharField(max_length>=128)."""
        field = MedicineInfo._meta.fields_map["name"]
        assert isinstance(field, fields.CharField)
        assert field.unique is True
        assert field.max_length >= 128

    def test_contraindicated_drugs_is_jsonfield(self) -> None:
        """`contraindicated_drugs` must be a JSONField."""
        field = MedicineInfo._meta.fields_map["contraindicated_drugs"]
        assert isinstance(field, fields.JSONField)

    def test_contraindicated_foods_is_jsonfield(self) -> None:
        """`contraindicated_foods` must be a JSONField."""
        field = MedicineInfo._meta.fields_map["contraindicated_foods"]
        assert isinstance(field, fields.JSONField)

    def test_embedding_is_vector_field_with_configured_dimensions(self) -> None:
        """`embedding` must be VectorField with EMBEDDING_DIMENSIONS."""
        field = MedicineInfo._meta.fields_map["embedding"]
        assert isinstance(field, VectorField)
        assert field.dimensions == EMBEDDING_DIMENSIONS

    def test_embedding_normalized_is_bool(self) -> None:
        """`embedding_normalized` must be a BooleanField."""
        field = MedicineInfo._meta.fields_map["embedding_normalized"]
        assert isinstance(field, fields.BooleanField)
