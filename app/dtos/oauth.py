from pydantic import BaseModel, Field


class OAuthConfigResponse(BaseModel):
    """OAuth 설정 정보 (FE 직접 리다이렉트용)"""

    client_id: str = Field(description="카카오 앱 Client ID")
    redirect_uri: str = Field(description="인가 코드를 받을 콜백 URL")
    authorize_url: str = Field(description="카카오 인증 페이지 URL")


class OAuthCallbackRequest(BaseModel):
    """OAuth 콜백 요청 (Query Parameter)"""

    code: str = Field(description="인가 코드")
    state: str | None = Field(default=None, description="CSRF 방지용 상태값")
    error: str | None = Field(default=None, description="에러 코드")
    error_description: str | None = Field(default=None, description="에러 설명")


class OAuthLoginResponse(BaseModel):
    """소셜 로그인 성공 응답"""

    access_token: str = Field(description="JWT Access Token")
    token_type: str = Field(default="Bearer", description="토큰 타입")
    is_new_user: bool = Field(description="신규 가입 여부")


class OAuthUserInfo(BaseModel):
    """카카오에서 받아온 사용자 정보"""

    provider_account_id: str = Field(description="카카오 사용자 고유 ID")
    nickname: str = Field(description="닉네임")
    profile_image_url: str | None = Field(default=None, description="프로필 이미지 URL")


class OAuthErrorResponse(BaseModel):
    """OAuth 에러 응답"""

    error: str = Field(description="에러 코드")
    error_description: str = Field(description="에러 상세 설명")
