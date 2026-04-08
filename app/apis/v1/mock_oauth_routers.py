import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Form, Header, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.core import config

mock_router = APIRouter(prefix="/mock/kakao", tags=["mock"])
MOCK_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "tests" / "mock_data"


@mock_router.get("/authorize")
async def mock_authorize(
    client_id: str,
    redirect_uri: str,
    response_type: str = "code",
    state: str | None = None,
    scenario: str = Query(
        "existing_user", description="테스트 시나리오 (예: existing_user, new_user, no_email_user 등)"
    ),
):
    """
    [Mock] 카카오 로그인 인증 페이지 역할
    JSON 파일에서 scenario 파라미터에 맞는 trigger_code를 동적으로 찾아 리다이렉트합니다.
    """
    token_file = MOCK_DATA_DIR / "kakao_token_responses.json"

    if not token_file.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Mock 데이터 파일을 찾을 수 없습니다.",
        )

    # JSON 데이터 로드
    data = json.loads(token_file.read_text(encoding="utf-8"))

    # 요청된 시나리오에 맞는 trigger_code 찾기
    trigger_code = None
    for resp in data.get("responses", []):
        if resp.get("scenario") == scenario:
            trigger_code = resp.get("trigger_code")
            break

    # 유효하지 않은 시나리오를 요청한 경우
    if not trigger_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"정의되지 않은 Mock 시나리오입니다: {scenario}",
        )

    # [원복] 추출한 코드로 리다이렉트 URL 조립 (브라우저가 직접 이동하도록)
    redirect_url = f"{redirect_uri}?code={trigger_code}"
    if state:
        redirect_url += f"&state={state}"

    return RedirectResponse(url=redirect_url)


@mock_router.post("/oauth/token")
async def mock_token(
    grant_type: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    code: Annotated[str, Form()],
    client_secret: Annotated[str, Form(description="보안을 위한 클라이언트 시크릿")],
):
    """
    [Mock] 카카오 토큰 발급 API (POST https://kauth.kakao.com/oauth/token 역할)
    """
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")

    # [핵심] Client Secret 검증 (Mock 환경 변수와 일치하는지 확인)
    # config.KAKAO_CLIENT_SECRET 은 환경변수(.env)에서 읽어온 값
    if client_secret != config.KAKAO_CLIENT_SECRET:
        raise HTTPException(
            status_code=401,
            detail={"error": "KOE010", "error_description": "Bad client credentials", "error_code": "KOE010"},
        )

    token_file = MOCK_DATA_DIR / "kakao_token_responses.json"
    data = json.loads(token_file.read_text(encoding="utf-8")) if token_file.exists() else {}

    # JSON에서 trigger_code와 일치하는 응답 찾기
    for resp in data.get("responses", []):
        if resp.get("trigger_code") == code:
            if resp.get("http_status") != 200:
                raise HTTPException(status_code=resp.get("http_status"), detail=resp.get("body"))
            return resp.get("body")

    # 매칭되는 코드가 없을 경우
    raise HTTPException(
        status_code=400,
        detail={
            "error": "KOE320",
            "error_description": "authorization code not found for the given value",
            "error_code": "KOE320",
        },
    )


@mock_router.get("/v2/user/me")
async def mock_user_info(
    authorization: Annotated[str, Header(description="Bearer {access_token}")],
):
    """
    [Mock] 카카오 사용자 정보 조회 API (GET https://kapi.kakao.com/v2/user/me 역할)
    """
    # "Bearer mock_access_token_..." 형태에서 토큰만 추출
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid_token_format")

    access_token = authorization.split(" ")[1]

    userinfo_file = MOCK_DATA_DIR / "kakao_userinfo_responses.json"
    data = json.loads(userinfo_file.read_text(encoding="utf-8")) if userinfo_file.exists() else {}

    # JSON에서 trigger_access_token과 일치하는 응답 찾기
    for resp in data.get("responses", []):
        if resp.get("trigger_access_token") == access_token:
            if resp.get("http_status") != 200:
                raise HTTPException(status_code=resp.get("http_status"), detail=resp.get("body"))
            return resp.get("body")

    # 매칭되는 토큰이 없을 경우
    raise HTTPException(status_code=401, detail={"msg": "this access token does not exist", "code": -401})
