"""DTOs for the tool-calling subsystem (Phase Y).

These models cross layer boundaries (router → service → external API →
LLM), so they must stay decoupled from Tortoise ORM and framework-
specific types. Keep them to plain Pydantic models.

The module starts with ``KakaoPlace`` (Y-1). Additional DTOs used by
later Y phases — ``ToolCall``, ``PendingTurn``, ``ToolResultRequest``,
``RequestGeolocationResponse``, ``RouteResult`` — are added in their
respective phases and will live here alongside ``KakaoPlace``.
"""

from pydantic import BaseModel, Field


class KakaoPlace(BaseModel):
    """Normalized view of one Kakao Local API ``documents[i]`` entry.

    Carries only the fields downstream code (LLM prompt, frontend map
    cards, message metadata) actually consumes. Raw distance strings,
    URLs, and region metadata are dropped on purpose — re-add if a
    concrete use case appears.
    """

    id: str = Field(description="Kakao-issued place id")
    place_name: str = Field(description="Display name of the place")
    address: str = Field(description="Jibun address (address_name)")
    road_address: str | None = Field(default=None, description="Road address (road_address_name)")
    phone: str | None = Field(default=None, description="Phone number")
    category_name: str | None = Field(default=None, description="Full category path, e.g. '의료,건강 > 약국'")
    category_group_code: str | None = Field(
        default=None,
        description="Kakao category group code: PM9 (약국), HP8 (병원), etc.",
    )
    lat: float = Field(description="Latitude (WGS84), mapped from Kakao 'y'")
    lng: float = Field(description="Longitude (WGS84), mapped from Kakao 'x'")
