import re
from uuid import UUID

from fastapi import HTTPException, status
from tortoise.models import Model


def normalize_phone_number(phone_number: str) -> str:
    if phone_number.startswith("+82"):
        phone_number = "0" + phone_number[3:]
    phone_number = re.sub(r"\D", "", phone_number)

    return phone_number


async def get_object_or_404[T: Model](model: type[T], id: UUID, detail: str | None = None) -> T:
    """
    Tortoise 모델에서 ID로 객체를 조회하고, 없으면 404 에러를 발생시킵니다.
    """
    obj = await model.get_or_none(id=id)
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail or f"{model.__name__} not found",
        )
    return obj
