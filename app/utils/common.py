"""Common utility functions.

This module provides common utility functions used across the application
including phone number normalization and database object retrieval.
"""

import re
from uuid import UUID

from fastapi import HTTPException, status
from tortoise.models import Model


def normalize_phone_number(phone_number: str) -> str:
    """Normalize phone number format.

    Converts international format (+82) to domestic format (0)
    and removes all non-digit characters.

    Args:
        phone_number: Phone number string to normalize.

    Returns:
        str: Normalized phone number with digits only.
    """
    if phone_number.startswith("+82"):
        phone_number = "0" + phone_number[3:]
    phone_number = re.sub(r"\D", "", phone_number)

    return phone_number


async def get_object_or_404[T: Model](model: type[T], object_id: UUID, detail: str | None = None) -> T:
    """Get object by ID from Tortoise model or raise 404 error.

    Args:
        model: Tortoise model class.
        object_id: Object UUID to retrieve.
        detail: Optional custom error message.

    Returns:
        T: Model instance if found.

    Raises:
        HTTPException: 404 error if object not found.
    """
    obj = await model.get_or_none(id=object_id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail or f"{model.__name__} not found",
        )
    return obj
