"""Custom Vector Field for pgvector integration with Tortoise ORM."""

from typing import Any

import numpy as np
from tortoise.fields import Field
from tortoise.models import Model


class VectorField(Field[list[float]]):
    """Custom field for storing vector embeddings using pgvector.

    Supports operations like cosine similarity, L2 distance, and inner product.
    """

    SQL_TYPE = "vector"

    def __init__(self, dimensions: int, **kwargs: Any) -> None:
        """Initialize vector field.

        Args:
            dimensions: Vector dimension size (e.g., 1536 for OpenAI embeddings)
            **kwargs: Additional field arguments passed to parent Field class
        """
        self.dimensions = dimensions
        super().__init__(**kwargs)

    def to_db_value(self, value: Any, instance: Model) -> str | None:  # noqa: ARG002
        """Convert Python list/numpy array to database vector format."""
        if value is None:
            return None

        if isinstance(value, np.ndarray):
            value = value.tolist()

        if not isinstance(value, list):
            msg = f"Vector field expects list or numpy array, got {type(value)}"
            raise TypeError(msg)

        if len(value) != self.dimensions:
            msg = f"Vector dimension mismatch: expected {self.dimensions}, got {len(value)}"
            raise ValueError(msg)

        # Convert to PostgreSQL vector format: [1.0, 2.0, 3.0]
        return f"[{','.join(map(str, value))}]"

    def to_python_value(self, value: Any) -> list[float] | None:
        """Convert database vector to Python list."""
        if value is None:
            return None

        if isinstance(value, str) and value.startswith("[") and value.endswith("]"):
            # Parse PostgreSQL vector format: [1.0, 2.0, 3.0]
            try:
                return [float(x.strip()) for x in value[1:-1].split(",")]
            except (ValueError, AttributeError):
                return None

        if isinstance(value, list):
            return [float(x) for x in value]

        return None

    @property
    def constraints(self) -> dict:
        """Return field constraints for database schema."""
        return {"dimensions": self.dimensions}


class VectorQueryMixin:
    """Mixin class providing vector similarity query methods.

    Usage:
        class MyModel(Model, VectorQueryMixin):
            embedding = VectorField(dimensions=1536)
    """

    @classmethod
    async def similarity_search(
        cls,
        query_vector: list[float] | np.ndarray,
        field_name: str = "embedding",
        limit: int = 10,
        similarity_threshold: float = 0.7,
        distance_type: str = "cosine",
    ) -> list[tuple]:
        """Perform vector similarity search.

        Args:
            query_vector: Query embedding vector
            field_name: Name of the vector field
            limit: Maximum number of results
            similarity_threshold: Minimum similarity score
            distance_type: 'cosine', 'l2', or 'inner_product'

        Returns:
            List of (model_instance, similarity_score) tuples
        """
        from tortoise import connections

        if isinstance(query_vector, np.ndarray):
            query_vector = query_vector.tolist()

        vector_str = f"[{','.join(map(str, query_vector))}]"

        # Choose distance operator based on type
        if distance_type == "cosine":
            operator = "<=>"
            order = "ASC"
        elif distance_type == "l2":
            operator = "<->"
            order = "ASC"
        elif distance_type == "inner_product":
            operator = "<#>"
            order = "DESC"
        else:
            raise ValueError(f"Unsupported distance type: {distance_type}")

        # Raw SQL query for vector similarity
        connection = connections.get("default")
        table_name = cls._meta.db_table

        # NOTE: This uses f-strings for table/field names which are controlled by the model definition
        # The actual query parameters use proper parameterization to prevent SQL injection
        sql = (
            f"SELECT *, ({field_name} {operator} %s) as distance "  # noqa: S608
            f"FROM {table_name} "
            f"WHERE ({field_name} {operator} %s) {'<' if distance_type != 'inner_product' else '>'} %s "
            f"ORDER BY distance {order} "
            "LIMIT %s"
        )

        threshold_value = 1 - similarity_threshold if distance_type == "cosine" else similarity_threshold

        results = await connection.execute_query_dict(sql, [vector_str, vector_str, threshold_value, limit])

        # Convert results back to model instances
        instances = []
        for row in results:
            distance = row.pop("distance")
            similarity = 1 - distance if distance_type == "cosine" else distance

            instance = cls(**row)
            instances.append((instance, similarity))

        return instances

    @classmethod
    async def hybrid_search(
        cls,
        query_vector: list[float] | np.ndarray,
        keyword_filters: dict | None = None,
        metadata_filters: dict | None = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        limit: int = 10,
    ) -> list[tuple]:
        """Perform hybrid search combining vector similarity and keyword matching.

        Args:
            query_vector: Query embedding vector
            keyword_filters: Dictionary of keyword search filters
            metadata_filters: Dictionary of metadata filters
            vector_weight: Weight for vector similarity score
            keyword_weight: Weight for keyword matching score
            limit: Maximum number of results

        Returns:
            List of (model_instance, combined_score) tuples
        """
        # Implementation for hybrid search
        # This would combine vector similarity with traditional text search
