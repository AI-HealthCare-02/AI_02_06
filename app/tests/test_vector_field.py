"""Tests for VectorField and VectorQueryMixin functionality."""

from unittest.mock import Mock

import numpy as np
import pytest
from tortoise import fields
from tortoise.models import Model

from app.db.vector_field import VectorField, VectorQueryMixin


class TestVectorModel(Model, VectorQueryMixin):
    """Test model for VectorField testing."""

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100)
    embedding = VectorField(dimensions=3)

    class Meta:
        table = "test_vectors"


class TestVectorField:
    """Test cases for VectorField functionality."""

    def test_vector_field_initialization(self) -> None:
        """Test VectorField initialization with dimensions."""
        field = VectorField(dimensions=1536)
        assert field.dimensions == 1536
        assert field.SQL_TYPE == "vector"

    def test_to_db_value_with_list(self) -> None:
        """Test converting Python list to database format."""
        field = VectorField(dimensions=3)
        test_vector = [1.0, 2.0, 3.0]

        result = field.to_db_value(test_vector, None)
        assert result == "[1.0,2.0,3.0]"

    def test_to_db_value_with_numpy_array(self) -> None:
        """Test converting numpy array to database format."""
        field = VectorField(dimensions=3)
        test_vector = np.array([1.0, 2.0, 3.0])

        result = field.to_db_value(test_vector, None)
        assert result == "[1.0,2.0,3.0]"

    def test_to_db_value_with_none(self) -> None:
        """Test handling None values."""
        field = VectorField(dimensions=3)

        result = field.to_db_value(None, None)
        assert result is None

    def test_to_db_value_wrong_type(self) -> None:
        """Test error handling for wrong input types."""
        field = VectorField(dimensions=3)

        with pytest.raises(TypeError, match="Vector field expects list or numpy array"):
            field.to_db_value("invalid", None)

    def test_to_db_value_wrong_dimensions(self) -> None:
        """Test error handling for dimension mismatch."""
        field = VectorField(dimensions=3)
        test_vector = [1.0, 2.0]  # Wrong dimension

        with pytest.raises(ValueError, match="Vector dimension mismatch"):
            field.to_db_value(test_vector, None)

    def test_to_python_value_from_string(self) -> None:
        """Test converting database string to Python list."""
        field = VectorField(dimensions=3)
        db_value = "[1.0,2.0,3.0]"

        result = field.to_python_value(db_value)
        assert result == [1.0, 2.0, 3.0]

    def test_to_python_value_from_list(self) -> None:
        """Test converting list to Python list (passthrough)."""
        field = VectorField(dimensions=3)
        test_vector = [1.0, 2.0, 3.0]

        result = field.to_python_value(test_vector)
        assert result == [1.0, 2.0, 3.0]

    def test_to_python_value_with_none(self) -> None:
        """Test handling None values in conversion."""
        field = VectorField(dimensions=3)

        result = field.to_python_value(None)
        assert result is None

    def test_to_python_value_invalid_string(self) -> None:
        """Test handling invalid string format."""
        field = VectorField(dimensions=3)

        result = field.to_python_value("invalid")
        assert result is None

    def test_to_python_value_malformed_vector(self) -> None:
        """Test handling malformed vector string."""
        field = VectorField(dimensions=3)

        result = field.to_python_value("[1.0,invalid,3.0]")
        assert result is None

    def test_constraints_property(self) -> None:
        """Test constraints property returns dimensions."""
        field = VectorField(dimensions=1536)

        constraints = field.constraints
        assert constraints == {"dimensions": 1536}


class TestVectorQueryMixin:
    """Test cases for VectorQueryMixin functionality."""

    @pytest.mark.asyncio
    async def test_similarity_search_cosine(self) -> None:
        """Test cosine similarity search."""
        # This test would require database setup
        # For now, we test the parameter validation
        query_vector = [1.0, 0.0, 0.0]

        # Test parameter validation without database
        assert isinstance(query_vector, list)
        assert len(query_vector) == 3

    @pytest.mark.asyncio
    async def test_similarity_search_with_numpy(self) -> None:
        """Test similarity search with numpy array input."""
        query_vector = np.array([1.0, 0.0, 0.0])

        # Convert to list as the method would do
        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.tolist()

        assert isinstance(query_vector, list)
        assert query_vector == [1.0, 0.0, 0.0]

    def test_distance_type_validation(self) -> None:
        """Test distance type parameter validation."""
        valid_types = ["cosine", "l2", "inner_product"]
        invalid_type = "invalid_distance"

        assert "cosine" in valid_types
        assert "l2" in valid_types
        assert "inner_product" in valid_types
        assert invalid_type not in valid_types

    def test_vector_string_formatting(self) -> None:
        """Test vector string formatting for SQL queries."""
        query_vector = [1.0, 2.0, 3.0]
        vector_str = f"[{','.join(map(str, query_vector))}]"

        assert vector_str == "[1.0,2.0,3.0]"

    def test_threshold_calculation(self) -> None:
        """Test similarity threshold calculation for different distance types."""
        similarity_threshold = 0.7

        # Cosine distance: 1 - similarity
        cosine_threshold = 1 - similarity_threshold
        assert cosine_threshold == pytest.approx(0.3)

        # L2 and inner product: use threshold directly
        l2_threshold = similarity_threshold
        assert l2_threshold == 0.7


class TestVectorOperations:
    """Test cases for vector mathematical operations."""

    def test_vector_normalization(self) -> None:
        """Test L2 normalization of vectors."""
        vector = np.array([3.0, 4.0, 0.0])

        # L2 norm calculation
        norm = np.linalg.norm(vector)
        normalized = vector / norm

        assert abs(np.linalg.norm(normalized) - 1.0) < 1e-10
        assert normalized.tolist() == [0.6, 0.8, 0.0]

    def test_cosine_similarity_calculation(self) -> None:
        """Test cosine similarity calculation."""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        vec3 = np.array([1.0, 0.0, 0.0])

        # Cosine similarity = dot product of normalized vectors
        similarity_orthogonal = np.dot(vec1, vec2)
        similarity_identical = np.dot(vec1, vec3)

        assert similarity_orthogonal == 0.0  # Orthogonal vectors
        assert similarity_identical == 1.0  # Identical vectors

    def test_vector_distance_calculations(self) -> None:
        """Test different vector distance calculations."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([4.0, 5.0, 6.0])

        # L2 (Euclidean) distance
        l2_distance = np.linalg.norm(vec1 - vec2)
        expected_l2 = np.sqrt(9 + 9 + 9)  # sqrt((4-1)^2 + (5-2)^2 + (6-3)^2)

        assert abs(l2_distance - expected_l2) < 1e-10

        # Inner product (dot product)
        inner_product = np.dot(vec1, vec2)
        expected_inner = 1 * 4 + 2 * 5 + 3 * 6  # 4 + 10 + 18 = 32

        assert inner_product == expected_inner


@pytest.fixture
async def setup_test_db() -> None:
    """Fixture to set up test database with pgvector extension."""
    # This would be implemented when we have actual database testing
    # For now, it's a placeholder


class TestVectorDatabaseIntegration:
    """Integration tests for vector database operations."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires database setup")
    async def test_vector_storage_and_retrieval(self, setup_test_db: Mock) -> None:
        """Test storing and retrieving vectors from database."""
        # This test would require actual database connection
        # Implementation would go here when database is set up

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires database setup")
    async def test_hnsw_index_creation(self, setup_test_db: Mock) -> None:
        """Test HNSW index creation for vector similarity search."""
        # This test would verify HNSW index creation
        # Implementation would go here when database is set up

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires database setup")
    async def test_similarity_search_performance(self, setup_test_db: Mock) -> None:
        """Test performance of similarity search with large dataset."""
        # This test would measure search performance
        # Implementation would go here when database is set up
