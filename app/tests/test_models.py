"""모델 CRUD 테스트 - DB 테이블 생성 및 데이터 입력/수정/삭제 검증"""

from datetime import date, time
from uuid import uuid4

import pytest
from tortoise import Tortoise

from app.models.accounts import Account, AuthProvider
from app.models.challenge import Challenge
from app.models.chat_sessions import ChatSession
from app.models.drug_interaction_cache import DrugInteractionCache
from app.models.intake_log import IntakeLog
from app.models.llm_response_cache import LLMResponseCache
from app.models.medication import Medication
from app.models.messages import ChatMessage, SenderType
from app.models.profiles import Profile, RelationType


class TestDatabaseSchema:
    """DB 스키마 테스트 - 모든 테이블이 정상 생성되는지 확인"""

    @pytest.mark.asyncio
    async def test_all_tables_created(self):
        """모든 테이블이 DB에 생성되었는지 확인"""
        conn = Tortoise.get_connection("default")

        # 테이블 목록 조회
        result = await conn.execute_query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        tables = {row["table_name"] for row in result[1]}

        expected_tables = {
            "accounts",
            "profiles",
            "medications",
            "intake_logs",
            "challenges",
            "chat_sessions",
            "messages",
            "message_feedbacks",
            "refresh_tokens",
            "drug_interaction_cache",
            "llm_response_cache",
            "aerich",  # 마이그레이션 테이블
        }

        for table in expected_tables:
            assert table in tables, f"테이블 '{table}'이 생성되지 않음"


class TestAccountModel:
    """Account 모델 CRUD 테스트"""

    @pytest.mark.asyncio
    async def test_create_account(self):
        """계정 생성"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="12345678",
            nickname="테스트유저",
            is_active=True,
        )

        assert account.id is not None
        assert account.auth_provider == AuthProvider.KAKAO
        assert account.nickname == "테스트유저"

    @pytest.mark.asyncio
    async def test_update_account(self):
        """계정 수정"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="update_test",
            nickname="수정전",
            is_active=True,
        )

        account.nickname = "수정후"
        await account.save()

        updated = await Account.get(id=account.id)
        assert updated.nickname == "수정후"

    @pytest.mark.asyncio
    async def test_delete_account(self):
        """계정 삭제"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="delete_test",
            nickname="삭제테스트",
            is_active=True,
        )

        await account.delete()
        deleted = await Account.get_or_none(id=account.id)
        assert deleted is None


class TestProfileModel:
    """Profile 모델 CRUD 테스트"""

    @pytest.mark.asyncio
    async def test_create_profile_with_account(self):
        """프로필 생성 (계정 연결)"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="profile_test",
            nickname="프로필테스트",
            is_active=True,
        )

        profile = await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.SELF,
            name="본인프로필",
            health_survey={"birth_year": 1990, "gender": "MALE"},
        )

        assert profile.id is not None
        assert profile.relation_type == RelationType.SELF
        assert profile.health_survey["birth_year"] == 1990

    @pytest.mark.asyncio
    async def test_profile_account_relation(self):
        """프로필-계정 관계 조회"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="relation_test",
            nickname="관계테스트",
            is_active=True,
        )

        await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.SELF,
            name="본인",
        )
        await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.PARENT,
            name="부모님",
        )

        profiles = await Profile.filter(account=account).all()
        assert len(profiles) == 2


class TestMedicationModel:
    """Medication 모델 CRUD 테스트"""

    @pytest.mark.asyncio
    async def test_create_medication(self):
        """약품 생성"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="med_test",
            nickname="약품테스트",
            is_active=True,
        )
        profile = await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.SELF,
            name="본인",
        )

        medication = await Medication.create(
            id=uuid4(),
            profile=profile,
            medicine_name="타이레놀",
            dose_per_intake="1정",
            intake_instruction="식후 30분",
            intake_times=["08:00", "13:00", "19:00"],
            total_intake_count=21,
            remaining_intake_count=21,
            start_date=date(2026, 4, 6),
            is_active=True,
        )

        assert medication.medicine_name == "타이레놀"
        assert len(medication.intake_times) == 3

    @pytest.mark.asyncio
    async def test_update_medication_remaining_count(self):
        """약품 남은 복용 횟수 수정"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="med_update",
            nickname="수정테스트",
            is_active=True,
        )
        profile = await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.SELF,
            name="본인",
        )
        medication = await Medication.create(
            id=uuid4(),
            profile=profile,
            medicine_name="아스피린",
            intake_times=["09:00"],
            total_intake_count=10,
            remaining_intake_count=10,
            start_date=date(2026, 4, 6),
        )

        medication.remaining_intake_count -= 1
        await medication.save()

        updated = await Medication.get(id=medication.id)
        assert updated.remaining_intake_count == 9


class TestIntakeLogModel:
    """IntakeLog 모델 CRUD 테스트"""

    @pytest.mark.asyncio
    async def test_create_intake_log(self):
        """복용 기록 생성"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="log_test",
            nickname="기록테스트",
            is_active=True,
        )
        profile = await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.SELF,
            name="본인",
        )
        medication = await Medication.create(
            id=uuid4(),
            profile=profile,
            medicine_name="비타민",
            intake_times=["08:00"],
            total_intake_count=30,
            remaining_intake_count=30,
            start_date=date(2026, 4, 6),
        )

        log = await IntakeLog.create(
            id=uuid4(),
            medication=medication,
            profile=profile,
            scheduled_date=date(2026, 4, 6),
            scheduled_time=time(8, 0),
            intake_status="SCHEDULED",
        )

        assert log.intake_status == "SCHEDULED"

    @pytest.mark.asyncio
    async def test_update_intake_status(self):
        """복용 상태 업데이트"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="status_test",
            nickname="상태테스트",
            is_active=True,
        )
        profile = await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.SELF,
            name="본인",
        )
        medication = await Medication.create(
            id=uuid4(),
            profile=profile,
            medicine_name="오메가3",
            intake_times=["09:00"],
            total_intake_count=30,
            remaining_intake_count=30,
            start_date=date(2026, 4, 6),
        )
        log = await IntakeLog.create(
            id=uuid4(),
            medication=medication,
            profile=profile,
            scheduled_date=date(2026, 4, 6),
            scheduled_time=time(9, 0),
        )

        log.intake_status = "COMPLETED"
        await log.save()

        updated = await IntakeLog.get(id=log.id)
        assert updated.intake_status == "COMPLETED"


class TestChallengeModel:
    """Challenge 모델 CRUD 테스트"""

    @pytest.mark.asyncio
    async def test_create_challenge(self):
        """챌린지 생성"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="challenge_test",
            nickname="챌린지테스트",
            is_active=True,
        )
        profile = await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.SELF,
            name="본인",
        )

        challenge = await Challenge.create(
            id=uuid4(),
            profile=profile,
            title="7일 연속 복용 챌린지",
            description="일주일 동안 매일 약을 복용하세요",
            target_days=7,
            completed_dates=[],
            challenge_status="IN_PROGRESS",
            started_date=date(2026, 4, 6),
        )

        assert challenge.title == "7일 연속 복용 챌린지"
        assert challenge.target_days == 7

    @pytest.mark.asyncio
    async def test_update_challenge_progress(self):
        """챌린지 진행상황 업데이트"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="progress_test",
            nickname="진행테스트",
            is_active=True,
        )
        profile = await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.SELF,
            name="본인",
        )
        challenge = await Challenge.create(
            id=uuid4(),
            profile=profile,
            title="3일 챌린지",
            target_days=3,
            completed_dates=[],
            started_date=date(2026, 4, 6),
        )

        challenge.completed_dates = ["2026-04-06", "2026-04-07"]
        await challenge.save()

        updated = await Challenge.get(id=challenge.id)
        assert len(updated.completed_dates) == 2


class TestChatSessionModel:
    """ChatSession 모델 CRUD 테스트"""

    @pytest.mark.asyncio
    async def test_create_chat_session(self):
        """채팅 세션 생성"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="chat_test",
            nickname="채팅테스트",
            is_active=True,
        )
        profile = await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.SELF,
            name="본인",
        )

        session = await ChatSession.create(
            id=uuid4(),
            account=account,
            profile=profile,
            title="약 복용 상담",
        )

        assert session.title == "약 복용 상담"


class TestChatMessageModel:
    """ChatMessage 모델 CRUD 테스트"""

    @pytest.mark.asyncio
    async def test_create_message(self):
        """메시지 생성"""
        account = await Account.create(
            id=uuid4(),
            auth_provider=AuthProvider.KAKAO,
            provider_account_id="msg_test",
            nickname="메시지테스트",
            is_active=True,
        )
        profile = await Profile.create(
            id=uuid4(),
            account=account,
            relation_type=RelationType.SELF,
            name="본인",
        )
        session = await ChatSession.create(
            id=uuid4(),
            account=account,
            profile=profile,
        )

        await ChatMessage.create(
            id=uuid4(),
            session=session,
            sender_type=SenderType.USER,
            content="타이레놀 복용 시 주의사항이 뭔가요?",
        )
        await ChatMessage.create(
            id=uuid4(),
            session=session,
            sender_type=SenderType.ASSISTANT,
            content="타이레놀 복용 시 공복에 드시면 위장 장애가 있을 수 있습니다.",
        )

        messages = await ChatMessage.filter(session=session).all()
        assert len(messages) == 2


class TestCacheModels:
    """캐시 모델 테스트"""

    @pytest.mark.asyncio
    async def test_drug_interaction_cache(self):
        """DUR 병용금기 캐시 생성"""
        from datetime import datetime, timedelta

        cache = await DrugInteractionCache.create(
            drug_pair="아스피린::타이레놀",
            interaction={"severity": "주의", "description": "동시 복용 시 위장 출혈 위험"},
            expires_at=datetime.now() + timedelta(days=30),
        )

        assert cache.drug_pair == "아스피린::타이레놀"
        assert cache.interaction["severity"] == "주의"

    @pytest.mark.asyncio
    async def test_llm_response_cache(self):
        """LLM 응답 캐시 생성"""
        import hashlib
        from datetime import datetime, timedelta

        prompt = "타이레놀 복용 방법 알려줘"
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()

        cache = await LLMResponseCache.create(
            prompt_hash=prompt_hash,
            prompt_text=prompt,
            response={"answer": "식후 30분에 1정을 복용하세요."},
            expires_at=datetime.now() + timedelta(hours=24),
        )

        assert cache.prompt_text == prompt
        assert cache.hit_count == 0

        # 히트 카운트 증가
        cache.hit_count += 1
        await cache.save()

        updated = await LLMResponseCache.get(id=cache.id)
        assert updated.hit_count == 1
