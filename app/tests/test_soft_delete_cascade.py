"""Soft-delete cascade 통합 테스트 (mock 기반).

검증 범위:
- ``ChatSessionService.delete_session`` 가 messages 도 같이 soft-delete 하는지
- ``ProfileService.delete_profile`` 가 모든 자식 (medication / challenge /
  chat_session / messages soft + intake / daily / lifestyle / ocr hard) 을 처리
- ``OAuthService.delete_account`` 가 refresh_tokens hard + 모든 profiles
  cascade + 계정 직접 sessions/messages soft + account.deactivate + deleted_at
- ``LifestyleGuideService._cascade_delete_guide`` 가 챌린지 보존 정책
  (활성 보존 / 미시작 soft-delete) 을 따르는지
- ``MedicationService.delete_prescription_group_with_owner_check`` 가 처방전
  그룹 + 가이드/챌린지 cascade 를 트랜잭션으로 처리하는지

DB 연결 없이 repository 메서드를 모두 ``AsyncMock`` 으로 패치하고 호출 여부 +
인자만 검증한다. ``in_transaction()`` 은 ``contextlib.asynccontextmanager`` 로
no-op 대체.
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException
import pytest

from app.models.profiles import RelationType
from app.services.chat_session_service import ChatSessionService
from app.services.lifestyle_guide_service import LifestyleGuideService
from app.services.medication_service import MedicationService
from app.services.oauth import OAuthService
from app.services.profile_service import ProfileService


@asynccontextmanager
async def _fake_transaction():
    """in_transaction() 의 no-op stub — DB 연결 없이 동작."""
    yield None


# ── ChatSessionService.delete_session cascade ─────────────────────────────


class TestChatSessionCascade:
    """세션 삭제 시 자식 메시지가 함께 soft-delete 되는지 검증."""

    @pytest.mark.asyncio
    async def test_delete_session_cascades_messages(self) -> None:
        session_id = uuid4()
        fake_session = MagicMock(id=session_id)

        service = ChatSessionService()
        service.repository = MagicMock()
        service.repository.get_by_id = AsyncMock(return_value=fake_session)
        service.repository.soft_delete = AsyncMock(return_value=fake_session)
        service.message_repository = MagicMock()
        service.message_repository.bulk_soft_delete_by_session = AsyncMock(return_value=3)

        with patch("app.services.chat_session_service.in_transaction", _fake_transaction):
            await service.delete_session(session_id)

        service.repository.soft_delete.assert_awaited_once_with(fake_session)
        service.message_repository.bulk_soft_delete_by_session.assert_awaited_once_with(session_id)

    @pytest.mark.asyncio
    async def test_delete_session_with_owner_check_cascades_messages(self) -> None:
        account_id = uuid4()
        session_id = uuid4()
        profile_id = uuid4()
        fake_session = MagicMock(id=session_id, profile_id=profile_id, account_id=account_id)

        service = ChatSessionService()
        service.repository = MagicMock()
        service.repository.get_by_id = AsyncMock(return_value=fake_session)
        service.repository.soft_delete = AsyncMock(return_value=fake_session)
        service.message_repository = MagicMock()
        service.message_repository.bulk_soft_delete_by_session = AsyncMock(return_value=2)
        service.profile_repository = MagicMock()
        service.profile_repository.get_by_id = AsyncMock(
            return_value=MagicMock(account_id=account_id),
        )

        with patch("app.services.chat_session_service.in_transaction", _fake_transaction):
            await service.delete_session_with_owner_check(session_id, account_id)

        service.repository.soft_delete.assert_awaited_once_with(fake_session)
        service.message_repository.bulk_soft_delete_by_session.assert_awaited_once_with(session_id)


# ── ProfileService.delete_profile cascade ─────────────────────────────────


def _build_profile_service_with_mocks(profile, sessions=None):
    """ProfileService + 모든 repository AsyncMock 으로 채운 fixture."""
    service = ProfileService()
    service.repository = MagicMock()
    service.repository.get_by_id = AsyncMock(return_value=profile)
    service.repository.soft_delete = AsyncMock(return_value=profile)

    service.medication_repository = MagicMock()
    service.medication_repository.bulk_soft_delete_by_profile = AsyncMock(return_value=2)

    service.challenge_repository = MagicMock()
    service.challenge_repository.bulk_soft_delete_by_profile = AsyncMock(return_value=1)

    service.chat_session_repository = MagicMock()
    service.chat_session_repository.bulk_soft_delete_by_profile = AsyncMock(return_value=1)
    service.chat_session_repository.get_by_profile = AsyncMock(return_value=sessions or [])

    service.message_repository = MagicMock()
    service.message_repository.bulk_soft_delete_by_session = AsyncMock(return_value=4)

    service.intake_log_repository = MagicMock()
    service.intake_log_repository.bulk_delete_by_profile = AsyncMock(return_value=10)

    service.daily_symptom_log_repository = MagicMock()
    service.daily_symptom_log_repository.bulk_delete_by_profile = AsyncMock(return_value=5)

    service.lifestyle_guide_repository = MagicMock()
    service.lifestyle_guide_repository.bulk_delete_by_profile = AsyncMock(return_value=3)

    service.ocr_draft_repository = MagicMock()
    service.ocr_draft_repository.bulk_delete_by_profile = AsyncMock(return_value=2)

    return service


class TestProfileCascade:
    """프로필 삭제 시 7개 자식 테이블 모두 cascade 되는지 검증."""

    @pytest.mark.asyncio
    async def test_delete_profile_cascades_all_children(self) -> None:
        profile_id = uuid4()
        account_id = uuid4()
        profile = MagicMock(id=profile_id, account_id=account_id, relation_type=RelationType.SELF)
        session1 = MagicMock(id=uuid4())
        session2 = MagicMock(id=uuid4())

        service = _build_profile_service_with_mocks(profile, [session1, session2])

        with patch("app.services.profile_service.in_transaction", _fake_transaction):
            await service.delete_profile(profile_id)

        # 부모
        service.repository.soft_delete.assert_awaited_once_with(profile)
        # 자식 (deleted_at 보유 → soft)
        service.medication_repository.bulk_soft_delete_by_profile.assert_awaited_once_with(profile_id)
        service.challenge_repository.bulk_soft_delete_by_profile.assert_awaited_once_with(profile_id)
        service.chat_session_repository.bulk_soft_delete_by_profile.assert_awaited_once_with(profile_id)
        # session 별 message cascade — 2개 세션 모두
        assert service.message_repository.bulk_soft_delete_by_session.await_count == 2
        service.message_repository.bulk_soft_delete_by_session.assert_any_await(session1.id)
        service.message_repository.bulk_soft_delete_by_session.assert_any_await(session2.id)
        # 자식 (deleted_at 미보유 → hard)
        service.intake_log_repository.bulk_delete_by_profile.assert_awaited_once_with(profile_id)
        service.daily_symptom_log_repository.bulk_delete_by_profile.assert_awaited_once_with(profile_id)
        service.lifestyle_guide_repository.bulk_delete_by_profile.assert_awaited_once_with(profile_id)
        service.ocr_draft_repository.bulk_delete_by_profile.assert_awaited_once_with(profile_id)

    @pytest.mark.asyncio
    async def test_delete_profile_with_owner_check_self_guard_blocks(self) -> None:
        """SELF 프로필은 router 진입점에서 차단 — cascade 호출 X."""
        profile_id = uuid4()
        account_id = uuid4()
        profile = MagicMock(id=profile_id, account_id=account_id, relation_type=RelationType.SELF)

        service = _build_profile_service_with_mocks(profile)

        with pytest.raises(HTTPException) as exc:
            await service.delete_profile_with_owner_check(profile_id, account_id)

        assert exc.value.status_code == 403
        # 가드 통과 X — 어떤 cascade 도 호출되지 않아야
        service.repository.soft_delete.assert_not_awaited()
        service.medication_repository.bulk_soft_delete_by_profile.assert_not_awaited()
        service.intake_log_repository.bulk_delete_by_profile.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_profile_with_owner_check_non_self_cascades(self) -> None:
        """비-SELF 프로필은 owner check 통과 후 자식 모두 cascade."""
        profile_id = uuid4()
        account_id = uuid4()
        profile = MagicMock(id=profile_id, account_id=account_id, relation_type=RelationType.PARENT)

        service = _build_profile_service_with_mocks(profile)

        with patch("app.services.profile_service.in_transaction", _fake_transaction):
            await service.delete_profile_with_owner_check(profile_id, account_id)

        service.repository.soft_delete.assert_awaited_once_with(profile)
        service.medication_repository.bulk_soft_delete_by_profile.assert_awaited_once_with(profile_id)
        service.intake_log_repository.bulk_delete_by_profile.assert_awaited_once_with(profile_id)


# ── OAuthService.delete_account cascade ───────────────────────────────────


class TestAccountWithdrawalCascade:
    """회원탈퇴 시 모든 자식 (profiles 까지 재귀 cascade) 정리되는지 검증."""

    def _build_oauth_service(self, account, profiles, account_sessions):
        service = OAuthService()
        service.refresh_token_repo = MagicMock()
        service.refresh_token_repo.revoke_all_for_account = AsyncMock(return_value=2)

        service.profile_repo = MagicMock()
        service.profile_repo.get_all_by_account = AsyncMock(return_value=profiles)

        service.profile_service = MagicMock()
        service.profile_service.cascade_delete_profile = AsyncMock()

        service.chat_session_repo = MagicMock()
        service.chat_session_repo.get_all_by_account = AsyncMock(return_value=account_sessions)
        service.chat_session_repo.bulk_soft_delete_by_account = AsyncMock(return_value=len(account_sessions))

        service.message_repo = MagicMock()
        service.message_repo.bulk_soft_delete_by_session = AsyncMock(return_value=3)

        service.account_repo = MagicMock()
        service.account_repo.deactivate = AsyncMock(return_value=account)

        return service

    @pytest.mark.asyncio
    async def test_delete_account_cascades_all_profiles_including_self(self) -> None:
        """SELF 포함 모든 프로필이 cascade — guard 우회 확인."""
        account_id = uuid4()
        account = MagicMock(id=account_id, deleted_at=None)
        account.save = AsyncMock()
        self_profile = MagicMock(id=uuid4(), relation_type=RelationType.SELF)
        family_profile = MagicMock(id=uuid4(), relation_type=RelationType.PARENT)

        service = self._build_oauth_service(account, [self_profile, family_profile], [])

        with patch("app.services.oauth.in_transaction", _fake_transaction):
            result = await service.delete_account(account)

        assert result is True
        # SELF 프로필도 cascade 호출됨 (guard 우회)
        assert service.profile_service.cascade_delete_profile.await_count == 2
        service.profile_service.cascade_delete_profile.assert_any_await(self_profile)
        service.profile_service.cascade_delete_profile.assert_any_await(family_profile)

    @pytest.mark.asyncio
    async def test_delete_account_revokes_refresh_tokens_first(self) -> None:
        """refresh_tokens 가 cascade 시작 단계에서 hard-delete 되어야 (보안)."""
        account = MagicMock(id=uuid4(), deleted_at=None)
        account.save = AsyncMock()
        service = self._build_oauth_service(account, [], [])

        with patch("app.services.oauth.in_transaction", _fake_transaction):
            await service.delete_account(account)

        service.refresh_token_repo.revoke_all_for_account.assert_awaited_once_with(account.id)

    @pytest.mark.asyncio
    async def test_delete_account_cascades_account_chat_sessions_with_messages(self) -> None:
        """account 의 직접 chat_sessions 도 soft + 그 messages 까지 cascade."""
        account = MagicMock(id=uuid4(), deleted_at=None)
        account.save = AsyncMock()
        session1 = MagicMock(id=uuid4())
        session2 = MagicMock(id=uuid4())
        service = self._build_oauth_service(account, [], [session1, session2])

        with patch("app.services.oauth.in_transaction", _fake_transaction):
            await service.delete_account(account)

        service.chat_session_repo.bulk_soft_delete_by_account.assert_awaited_once_with(account.id)
        assert service.message_repo.bulk_soft_delete_by_session.await_count == 2
        service.message_repo.bulk_soft_delete_by_session.assert_any_await(session1.id)
        service.message_repo.bulk_soft_delete_by_session.assert_any_await(session2.id)

    @pytest.mark.asyncio
    async def test_delete_account_marks_deactivate_and_deleted_at(self) -> None:
        """account.deactivate 호출 + deleted_at timestamp set."""
        account = MagicMock(id=uuid4(), deleted_at=None)
        # hasattr(account, "deleted_at") 가 True 가 되도록 spec 명시
        account.save = AsyncMock()

        service = self._build_oauth_service(account, [], [])

        with patch("app.services.oauth.in_transaction", _fake_transaction):
            await service.delete_account(account)

        service.account_repo.deactivate.assert_awaited_once_with(account)
        # MagicMock 은 hasattr True — deleted_at set 코드 진입함
        assert account.deleted_at is not None
        account.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_account_raises_500_on_failure(self) -> None:
        """cascade 도중 예외 → HTTPException 500 으로 변환."""
        account = MagicMock(id=uuid4(), deleted_at=None)
        service = self._build_oauth_service(account, [], [])
        service.refresh_token_repo.revoke_all_for_account = AsyncMock(side_effect=RuntimeError("boom"))

        with (
            patch("app.services.oauth.in_transaction", _fake_transaction),
            pytest.raises(HTTPException) as exc,
        ):
            await service.delete_account(account)

        assert exc.value.status_code == 500
        assert exc.value.detail["error"] == "delete_failed"


# ── LifestyleGuideService 챌린지 보존 정책 cascade ────────────────────────


class TestLifestyleGuideCascade:
    """가이드 삭제 시 챌린지 정책 — 활성 보존 / 미시작 soft-delete."""

    @pytest.mark.asyncio
    async def test_cascade_delete_guide_soft_deletes_inactive_challenges(self) -> None:
        """미시작(is_active=False) 챌린지는 soft-delete."""
        guide_id = uuid4()
        guide = MagicMock(id=guide_id)
        inactive_challenge = MagicMock(id=uuid4(), is_active=False)

        service = LifestyleGuideService()
        service.challenge_repo = MagicMock()
        service.challenge_repo.get_by_guide_id = AsyncMock(return_value=[inactive_challenge])
        service.challenge_repo.soft_delete = AsyncMock()
        service.guide_repo = MagicMock()
        service.guide_repo.delete_by_id = AsyncMock()

        await service._cascade_delete_guide(guide)

        service.challenge_repo.soft_delete.assert_awaited_once_with(inactive_challenge)
        service.guide_repo.delete_by_id.assert_awaited_once_with(guide_id)

    @pytest.mark.asyncio
    async def test_cascade_delete_guide_preserves_active_challenges(self) -> None:
        """활성 챌린지는 guide_id=None 으로 분리만 — 사용자 진행분 보존."""
        guide_id = uuid4()
        guide = MagicMock(id=guide_id)
        active_challenge = MagicMock(id=uuid4(), is_active=True)

        service = LifestyleGuideService()
        service.challenge_repo = MagicMock()
        service.challenge_repo.get_by_guide_id = AsyncMock(return_value=[active_challenge])
        service.challenge_repo.soft_delete = AsyncMock()
        service.guide_repo = MagicMock()
        service.guide_repo.delete_by_id = AsyncMock()

        # Challenge.filter(...).update(...) 호출 mock
        with patch("app.services.lifestyle_guide_service.Challenge") as mock_challenge_cls:
            mock_filter = MagicMock()
            mock_filter.update = AsyncMock()
            mock_challenge_cls.filter.return_value = mock_filter

            await service._cascade_delete_guide(guide)

        # 활성 챌린지는 soft-delete 안 됨 — guide_id 분리만
        service.challenge_repo.soft_delete.assert_not_awaited()
        mock_challenge_cls.filter.assert_called_once_with(id=active_challenge.id)
        mock_filter.update.assert_awaited_once_with(guide_id=None)
        service.guide_repo.delete_by_id.assert_awaited_once_with(guide_id)

    @pytest.mark.asyncio
    async def test_cascade_delete_active_guides_by_profile_iterates_all(self) -> None:
        """프로필의 active 가이드 모두에 cascade 정책 적용."""
        profile_id = uuid4()
        guide1 = MagicMock(id=uuid4())
        guide2 = MagicMock(id=uuid4())

        service = LifestyleGuideService()
        service.guide_repo = MagicMock()
        service.guide_repo.get_all_by_profile = AsyncMock(return_value=[guide1, guide2])
        service.guide_repo.delete_by_id = AsyncMock()
        service.challenge_repo = MagicMock()
        service.challenge_repo.get_by_guide_id = AsyncMock(return_value=[])

        result = await service.cascade_delete_active_guides_by_profile(profile_id)

        assert result == 2
        service.guide_repo.get_all_by_profile.assert_awaited_once_with(profile_id)
        assert service.guide_repo.delete_by_id.await_count == 2


# ── MedicationService 처방전 그룹 cascade ─────────────────────────────────


class TestPrescriptionGroupCascade:
    """처방전 그룹 삭제 시 medication + 가이드 + 챌린지 cascade."""

    def _build_medication_service(self, profile, deleted_count=3):
        service = MedicationService()
        service.profile_repository = MagicMock()
        service.profile_repository.get_by_id = AsyncMock(return_value=profile)

        service.repository = MagicMock()
        service.repository.bulk_soft_delete = AsyncMock(return_value=deleted_count)

        service.lifestyle_guide_service = MagicMock()
        service.lifestyle_guide_service.cascade_delete_active_guides_by_profile = AsyncMock(return_value=2)

        # _collect_skipped_ids — 본 테스트에선 skip 없음 가정
        service._collect_skipped_ids = AsyncMock(return_value=[])
        return service

    @pytest.mark.asyncio
    async def test_delete_prescription_group_cascades_guides(self) -> None:
        """처방전 그룹 삭제 시 medication + 그 프로필의 가이드 cascade."""
        profile_id = uuid4()
        account_id = uuid4()
        ids = [uuid4(), uuid4(), uuid4()]
        profile = MagicMock(id=profile_id, account_id=account_id)

        service = self._build_medication_service(profile)

        with patch("app.services.medication_service.in_transaction", _fake_transaction):
            response = await service.delete_prescription_group_with_owner_check(
                ids,
                profile_id,
                account_id,
            )

        assert response.deleted_count == 3
        # medication soft delete — profile scope
        service.repository.bulk_soft_delete.assert_awaited_once_with(ids, [profile_id])
        # 가이드 cascade — 같은 profile_id
        service.lifestyle_guide_service.cascade_delete_active_guides_by_profile.assert_awaited_once_with(profile_id)

    @pytest.mark.asyncio
    async def test_delete_prescription_group_blocks_foreign_profile(self) -> None:
        """다른 계정의 프로필이면 403 — cascade 호출되지 않아야."""
        profile_id = uuid4()
        owner_account_id = uuid4()
        attacker_account_id = uuid4()
        profile = MagicMock(id=profile_id, account_id=owner_account_id)

        service = self._build_medication_service(profile)

        with (
            patch("app.services.medication_service.in_transaction", _fake_transaction),
            pytest.raises(HTTPException) as exc,
        ):
            await service.delete_prescription_group_with_owner_check(
                [uuid4()],
                profile_id,
                attacker_account_id,
            )

        assert exc.value.status_code == 403
        # 가드 통과 X — cascade 안 호출됨
        service.repository.bulk_soft_delete.assert_not_awaited()
        service.lifestyle_guide_service.cascade_delete_active_guides_by_profile.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_prescription_group_404_when_profile_missing(self) -> None:
        """프로필 자체가 없으면 404 — cascade 호출 X."""
        profile_id = uuid4()
        account_id = uuid4()

        service = MedicationService()
        service.profile_repository = MagicMock()
        service.profile_repository.get_by_id = AsyncMock(return_value=None)
        service.repository = MagicMock()
        service.repository.bulk_soft_delete = AsyncMock()
        service.lifestyle_guide_service = MagicMock()
        service.lifestyle_guide_service.cascade_delete_active_guides_by_profile = AsyncMock()

        with (
            patch("app.services.medication_service.in_transaction", _fake_transaction),
            pytest.raises(HTTPException) as exc,
        ):
            await service.delete_prescription_group_with_owner_check(
                [uuid4()],
                profile_id,
                account_id,
            )

        assert exc.value.status_code == 404
        service.repository.bulk_soft_delete.assert_not_awaited()
        service.lifestyle_guide_service.cascade_delete_active_guides_by_profile.assert_not_awaited()
