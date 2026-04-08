import asyncio
import os
import sys

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tortoise import Tortoise
from app.db.databases import TORTOISE_ORM
from app.models.accounts import Account, AuthProvider
from app.models.profiles import Profile, RelationType

async def run():
    # DB 연결
    await Tortoise.init(config=TORTOISE_ORM)
    
    # 1. 가짜 계정 생성
    # Mock 카카오 로그인에서 사용될 법한 ID로 생성
    account, created = await Account.get_or_create(
        auth_provider=AuthProvider.KAKAO,
        provider_account_id="mock_user_1234",
        defaults={
            "nickname": "테스트유저",
            "is_active": True,
            "profile_image_url": "https://via.placeholder.com/150"
        }
    )
    
    if created:
        print(f"✅ 새 계정 생성 완료: {account.nickname}")
    else:
        print(f"ℹ️ 기존 계정 사용: {account.nickname}")

    # 2. 해당 계정의 프로필 생성
    profile, p_created = await Profile.get_or_create(
        account=account,
        relation_type=RelationType.SELF,
        defaults={
            "name": "테스트유저(본인)",
            "health_survey": {"age": 25, "gender": "MALE"}
        }
    )
    
    if p_created:
        print(f"✅ 새 프로필 생성 완료: {profile.name}")
    else:
        print(f"ℹ️ 기존 프로필 사용: {profile.name}")

    await Tortoise.close_connections()

if __name__ == "__main__":
    async def main():
        try:
            await run()
        except Exception as e:
            print(f"❌ 에러 발생: {e}")
    
    asyncio.run(main())
