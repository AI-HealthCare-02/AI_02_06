"""Common validator utilities.

This module provides common validation utilities for Pydantic models
including optional validators and type helpers.
"""

from collections.abc import Callable
from typing import Any, TypeVar

from pydantic import AfterValidator

T = TypeVar("T")


def optional_after_validator(func: Callable[..., Any]) -> AfterValidator:
    """Create optional after validator that skips None values.

    Args:
        func: Validation function to apply.

    Returns:
        AfterValidator: Validator that applies function only to non-None values.
    """

    def _validate(v: T | None) -> T | None:
        """Internal validation function.

        Args:
            v: Value to validate.

        Returns:
            T | None: Validated value or None.
        """
        return func(v) if v is not None else v

    return AfterValidator(_validate)
