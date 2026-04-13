from tortoise import fields, models


class Challenge(models.Model):
    id = fields.UUIDField(pk=True)

    profile = fields.ForeignKeyField("models.Profile", related_name="challenges")

    title = fields.CharField(max_length=64, description="챌린지 제목")
    description = fields.CharField(max_length=256, null=True, description="상세 설명")
    target_days = fields.IntField(description="목표 달성 일수")

    # 기존 ChallengeLog 테이블을 없애고, 달성 날짜들을 JSON 배열 형식으로 한 번에 관리합니다.
    completed_dates = fields.JSONField(default=list, description="달성 완료 날짜 목록")

    challenge_status = fields.CharField(max_length=16, default="IN_PROGRESS", description="진행 상태")
    started_date = fields.DateField(description="챌린지 시작 날짜")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "challenges"
        indexes = (("profile_id", "challenge_status"),)


class UserChallenge(models.Model):
    id = fields.UUIDField(pk=True)

    profile = fields.ForeignKeyField("models.Profile", related_name="user_challenges")
    challenge = fields.ForeignKeyField("models.Challenge", related_name="user_participants")

    is_active = fields.BooleanField(default=True, description="챌린지 참여 활성화 여부")
    progress_rate = fields.IntField(default=0, description="진행률 (0-100)")
    completed_at = fields.DatetimeField(null=True, description="챌린지 최종 달성 일시")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "user_challenges"
        indexes = (("profile_id", "challenge_id", "is_active"),)
