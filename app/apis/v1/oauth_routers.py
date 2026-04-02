from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.dtos.oauth import OAuthConfigResponse, OAuthLoginResponse
from app.services.oauth import OAuthService

oauth_router = APIRouter(prefix="/auth", tags=["oauth"])


@oauth_router.get(
    "/kakao/config",
    response_model=OAuthConfigResponse,
    summary="카카오 OAuth 설정 조회",
    description="""
FE에서 직접 카카오 로그인 페이지로 리다이렉트할 때 필요한 설정을 반환합니다.

**FE 사용 방법 (직접 리다이렉트):**
1. 이 API를 호출하여 client_id, redirect_uri, authorize_url을 받습니다.
2. FE에서 state(랜덤 문자열)를 생성하고 sessionStorage에 저장합니다.
3. authorize_url로 직접 리다이렉트합니다:
   `{authorize_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&state={state}`
4. 카카오 로그인 완료 후 redirect_uri로 code, state가 전달됩니다.
5. FE에서 state 검증 후, BE의 /auth/kakao/callback?code=xxx 호출합니다.
    """,
)
async def get_kakao_oauth_config() -> OAuthConfigResponse:
    # 개발환경: Mock 서버, 운영환경: 실제 카카오
    if config.ENV == Env.PROD:
        authorize_url = "https://kauth.kakao.com/oauth/authorize"
    else:
        authorize_url = f"{config.API_BASE_URL}/api/v1/mock/kakao/authorize"

    return OAuthConfigResponse(
        client_id=config.KAKAO_CLIENT_ID,
        redirect_uri=config.KAKAO_REDIRECT_URI,
        authorize_url=authorize_url,
    )


@oauth_router.get(
    "/kakao/callback",
    response_model=OAuthLoginResponse,
    summary="카카오 로그인 콜백",
    description="""
카카오 인증 후 콜백을 처리하고 JWT 토큰을 발급합니다.

**처리 과정:**
1. 인가 코드(code)를 카카오 서버에 전달하여 액세스 토큰 교환
2. 액세스 토큰으로 카카오 사용자 정보 조회
3. 신규 사용자면 계정 생성, 기존 사용자면 정보 업데이트
4. 서비스 자체 JWT 토큰 발급
    """,
    responses={
        200: {"description": "로그인 성공"},
        400: {"description": "잘못된 요청 (code 누락, 카카오 에러)"},
        401: {"description": "인증 실패 (잘못된 code, 토큰 교환 실패)"},
        403: {"description": "비활성화된 계정"},
        422: {"description": "유효성 검사 실패"},
        429: {"description": "요청 횟수 초과"},
    },
)
async def kakao_callback(
    request: Request,
    oauth_service: Annotated[OAuthService, Depends(OAuthService)],
    code: Annotated[str | None, Query(description="카카오 인가 코드")] = None,
    state: Annotated[str | None, Query(description="CSRF 방지용 상태값")] = None,
    error: Annotated[str | None, Query(description="에러 코드")] = None,
    error_description: Annotated[str | None, Query(description="에러 설명")] = None,
) -> Response:
    # 카카오에서 에러 응답이 온 경우
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": error,
                "error_description": error_description or "카카오 인증 중 오류가 발생했습니다.",
            },
        )

    # code 파라미터 필수 체크
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "invalid_request",
                "error_description": "인가 코드(code)가 필요합니다.",
            },
        )

    # 클라이언트 IP 추출 (Rate limiting용)
    client_ip = request.client.host if request.client else "unknown"

    # 콜백 처리 (토큰 교환 + 사용자 정보 조회 + 계정 처리)
    account, is_new_user = await oauth_service.kakao_callback(
        code=code,
        client_ip=client_ip,
    )

    # 서비스 JWT 토큰 발급
    tokens = oauth_service.issue_tokens(account)

    # 응답 생성
    response = Response(
        content=OAuthLoginResponse(
            access_token=str(tokens["access_token"]),
            is_new_user=is_new_user,
        ).model_dump(),
        status_code=status.HTTP_200_OK,
    )

    # Refresh token을 HttpOnly 쿠키로 설정
    response.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=config.ENV == Env.PROD,
        samesite="lax",
        domain=config.COOKIE_DOMAIN or None,
        max_age=config.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
    )

    return response


@oauth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
    description="Refresh token 쿠키를 삭제하여 로그아웃합니다.",
)
async def logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=config.ENV == Env.PROD,
        samesite="lax",
    )
    return response
