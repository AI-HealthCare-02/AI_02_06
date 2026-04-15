from tortoise import fields, models

class MedicineInfo(models.Model):
    """
    RAG를 위한 약학 정보 지식 베이스 테이블
    """
    id = fields.IntField(pk=True)
    medicine_name = fields.CharField(max_length=128, unique=True, note="약품명")
    category = fields.CharField(max_length=64, null=True, note="약품 분류")
    efficacy = fields.TextField(null=True, note="효능/효과")
    side_effects = fields.TextField(null=True, note="부작용")
    precautions = fields.TextField(null=True, note="주의사항")
    
    # pgvector 전용: 실제 DB에는 'vector(1536)' 타입으로 수동 생성 필요 (OpenAI Embedding 기준)
    # Tortoise에서는 TextField로 선언하되, Raw SQL로 처리하거나 가상 필드로 활용
    embedding = fields.TextField(null=True, note="OpenAI 텍스트 임베딩 데이터 (JSON 형태 저장 또는 Raw SQL 처리)")

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "medicine_info"
        table_description = "RAG 검색을 위한 표준 약학 정보"
