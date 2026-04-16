from pydantic import BaseModel, Field


class DrugInteraction(BaseModel):
    drug: str = Field(description="상호작용 약품명")
    description: str = Field(description="상호작용 설명")


class DrugInfoResponse(BaseModel):
    medicine_name: str = Field(description="약품명")
    warnings: list[str] = Field(default_factory=list, description="주의사항 목록")
    side_effects: list[str] = Field(default_factory=list, description="주요 부작용 목록")
    interactions: list[DrugInteraction] = Field(default_factory=list, description="약물 상호작용 목록")
    severe_reaction_advice: str = Field(
        default="심한 부작용이 나타나면 즉시 복용을 중단하고 의사와 상담하세요.",
        description="심각한 반응 시 조언",
    )
