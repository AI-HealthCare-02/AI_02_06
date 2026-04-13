import hashlib
import hmac
import secrets
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response

from app.core import config
from app.core.config import Env
from app.dependencies.security import get_current_account
from app.dtos.oauth import (
    OAuthConfigResponse,
    OAuthErrorResponse,
    OAuthLoginResponse,
    TokenRefreshResponse,
)
from app.models.accounts import Account
from app.services.oauth import OAuthService
from app.services.rate_limiter import RateLimiter, get_rate_limiter

oauth_router = APIRouter(prefix="/auth", tags=["oauth"])

# State 유효 시간 (5분)
STATE_EXPIRY_SECONDS = 300


def _generate_state() -> str:
    """HMAC 서명된 state 생성 (CSRF 방지)"""
    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(16)
    payload = f"{timestamp}.{nonce}"
    signature = hmac.new(
        config.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()[:16]
    return f"{payload}.{signature}"


def _verify_state(state: str) -> bool:
    """State 서명 및 만료 검증"""
    try:
        parts = state.split(".")
        if len(parts) != 3:
            return False
        timestamp, nonce, signature = parts

        # 서명 검증
        payload = f"{timestamp}.{nonce}"
        expected_signature = hmac.new(
            config.SECRET_KEY.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()[:16]
        if not hmac.compare_digest(signature, expected_signature):
            return False

        # 만료 검증
        if time.time() - int(timestamp) > STATE_EXPIRY_SECONDS:
            return False

        return True
    except (ValueError, TypeError):
        return False


def _get_client_ip(request: Request) -> str:
    """실제 클라이언트 IP 추출 (프록시 고려)"""
    # X-Forwarded-For 헤더 확인 (프록시/로드밸런서)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # 첫 번째 IP가 실제 클라이언트
        return forwarded_for.split(",")[0].strip()

    # X-Real-IP 헤더 확인 (Nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # 직접 연결
    return request.client.host if request.client else "unknown"


def get_oauth_service(
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> OAuthService:
    """OAuthService 의존성 팩토리"""
    return OAuthService(rate_limiter=rate_limiter)


@oauth_router.get(
    "/kakao/config",
    response_model=OAuthConfigResponse,
    summary="카카오 OAuth 설정 조회",
    description="""
FE에서 직접 카카오 로그인 페이지로 리다이렉트할 때 필요한 설정을 반환합니다.

**FE 사용 방법 (직접 리다이렉트):**
1. 이 API를 호출하여 client_id, redirect_uri, authorize_url, state를 받습니다.
2. state를 sessionStorage에 저장합니다 (BE가 생성한 서명된 state).
3. authorize_url로 직접 리다이렉트합니다:
   `{authorize_url}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&state={state}`
4. 카카오 로그인 완료 후 redirect_uri로 code, state가 전달됩니다.
5. FE에서 저장된 state와 비교 후, BE의 /auth/kakao/callback?code=xxx&state=xxx 호출합니다.
6. BE에서 state 서명 및 만료를 검증합니다.
    """,
)
async def get_kakao_oauth_config() -> OAuthConfigResponse:
    # authorize_url: 브라우저가 접근해야 하므로 외부 URL
    # - local: Mock 서버 (개발 편의)
    # - dev/prod: 실제 카카오 서버
    if config.ENV == Env.LOCAL:
        # local: Mock 서버 사용 (FRONTEND_URL -> Next.js rewrites -> FastAPI)
        authorize_url = f"{config.FRONTEND_URL}/api/v1/mock/kakao/authorize"
    else:
        # dev/prod: 실제 카카오 OAuth
        authorize_url = "https://kauth.kakao.com/oauth/authorize"

    # 서명된 state 생성 (CSRF 방지)
    state = _generate_state()

    return OAuthConfigResponse(
        client_id=config.KAKAO_CLIENT_ID,
        redirect_uri=config.KAKAO_REDIRECT_URI,
        authorize_url=authorize_url,
        state=state,
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
        200: {"description": "로그인 성공", "model": OAuthLoginResponse},
        400: {"description": "잘못된 요청 (code 누락, 카카오 에러)", "model": OAuthErrorResponse},
        401: {"description": "인증 실패 (잘못된 code, 토큰 교환 실패)", "model": OAuthErrorResponse},
        403: {"description": "비활성화된 계정", "model": OAuthErrorResponse},
        422: {"description": "유효성 검사 실패"},
        429: {"description": "요청 횟수 초과", "model": OAuthErrorResponse},
    },
)
async def kakao_callback(
    request: Request,
    oauth_service: Annotated[OAuthService, Depends(get_oauth_service)],
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

    # state 검증 (CSRF 방지) - BE에서 생성한 서명된 state 검증
    # [DEV ONLY] 개발자용 즉시 로그인 버튼 클릭 시에만 검증을 건너뜁니다.
    is_dev_login = config.ENV != Env.PROD and code == "dev_test_login"

    if not is_dev_login:
        if not state or not _verify_state(state):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "invalid_state",
                    "error_description": "유효하지 않거나 만료된 state입니다.",
                },
            )

    # 클라이언트 IP 추출 (Rate limiting용, 프록시 고려)
    client_ip = _get_client_ip(request)

    # [DEV ONLY] 개발용 즉시 로그인 처리
    if config.ENV != Env.PROD and code == "dev_test_login":
        account, is_new_user = await oauth_service.dev_test_login()
    else:
        # 콜백 처리 (토큰 교환 + 사용자 정보 조회 + 계정 처리)
        account, is_new_user = await oauth_service.kakao_callback(
            code=code,
            client_ip=client_ip,
        )

    # 서비스 JWT 토큰 발급 및 DB 저장
    tokens = await oauth_service.issue_tokens(account)

    # 응답 생성 (JSON + HttpOnly 쿠키)
    # FE에서 is_new_user 값으로 라우팅 결정 (/survey 또는 /main)
    response = JSONResponse(
        content=OAuthLoginResponse(is_new_user=is_new_user).model_dump(),
        status_code=status.HTTP_200_OK,
    )

    # Access Token을 HttpOnly 쿠키로 설정 (XSS 방지)
    response.set_cookie(
        key="access_token",
        value=str(tokens["access_token"]),
        httponly=True,
        secure=config.ENV == Env.PROD,
        samesite="lax",
        domain=config.COOKIE_DOMAIN or None,
        max_age=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
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
    "/refresh",
    response_model=TokenRefreshResponse,
    summary="토큰 갱신 (RTR)",
    description="""
Refresh Token으로 새 Access Token을 발급합니다.

**RTR (Refresh Token Rotation):**
- 기존 Refresh Token은 즉시 무효화됩니다
- 새 Refresh Token이 쿠키로 발급됩니다
- Grace Period(2초) 내 동시 요청은 허용됩니다

**탈취 감지:**
- Grace Period 초과 후 구 토큰 사용 시 403 응답
- 해당 토큰만 무효화 (다른 기기 세션 유지)
    """,
    responses={
        200: {"description": "토큰 갱신 성공", "model": TokenRefreshResponse},
        401: {"description": "유효하지 않은 토큰", "model": OAuthErrorResponse},
        403: {"description": "탈취 의심 (재로그인 필요)", "model": OAuthErrorResponse},
    },
)
async def refresh_token(
    request: Request,
    oauth_service: Annotated[OAuthService, Depends(get_oauth_service)],
) -> Response:
    # 쿠키에서 refresh token 추출
    refresh_token_str = request.cookies.get("refresh_token")

    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "missing_token",
                "error_description": "Refresh token이 없습니다.",
            },
        )

    # RTR 적용 토큰 갱신
    tokens = await oauth_service.refresh_access_token(refresh_token_str)

    # 응답 생성
    response = JSONResponse(
        content=TokenRefreshResponse(access_token=tokens["access_token"]).model_dump(),
        status_code=status.HTTP_200_OK,
    )

    # 새 Access Token을 HttpOnly 쿠키로 설정 (XSS 방지)
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=config.ENV == Env.PROD,
        samesite="lax",
        domain=config.COOKIE_DOMAIN or None,
        max_age=config.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    # 새 Refresh Token을 HttpOnly 쿠키로 설정
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=config.ENV == Env.PROD,
        samesite="lax",
        domain=config.COOKIE_DOMAIN or None,
        max_age=config.REFRESH_TOKEN_EXPIRE_MINUTES * 60,
    )

    return response


@oauth_router.delete(
    "/account",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="회원 탈퇴",
    description="계정을 소프트 삭제하고 모든 토큰을 무효화합니다.",
    responses={
        204: {"description": "회원 탈퇴 성공 (본문 없음)"},
        401: {"description": "인증 실패", "model": OAuthErrorResponse},
    },
)
async def delete_account(
    request: Request,
    current_account: Annotated[Account, Depends(get_current_account)],
    oauth_service: Annotated[OAuthService, Depends(get_oauth_service)],
) -> Response:
    await oauth_service.delete_account(current_account)

    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=config.ENV == Env.PROD,
        samesite="lax",
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=config.ENV == Env.PROD,
        samesite="lax",
    )
    return response


@oauth_router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="로그아웃",
    description="Refresh token을 무효화하고 쿠키를 삭제합니다.",
    responses={
        204: {"description": "로그아웃 성공 (본문 없음)"},
    },
)
async def logout(
    request: Request,
    oauth_service: Annotated[OAuthService, Depends(get_oauth_service)],
) -> Response:
    # 쿠키에서 refresh token 추출
    refresh_token = request.cookies.get("refresh_token")

    # DB에서 토큰 무효화
    if refresh_token:
        await oauth_service.revoke_refresh_token(refresh_token)

    # 쿠키 삭제
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=config.ENV == Env.PROD,
        samesite="lax",
    )
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        secure=config.ENV == Env.PROD,
        samesite="lax",
    )
    return response
