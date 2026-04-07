from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from tortoise.exceptions import BaseORMException, DBConnectionError

from app.apis.v1 import v1_routers
from app.core.config import Env, config
from app.db.databases import initialize_tortoise
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.security import SecurityMiddleware

app = FastAPI(
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)


# --- 전역 예외 처리기 (Global Exception Handlers) ---


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic 유효성 검사 에러 처리 (422 -> 400으로 통일하거나 상세 에러 반환)"""
    return ORJSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "error_description": "입력값 유효성 검사에 실패했습니다.",
            "details": exc.errors(),
        },
    )


@app.exception_handler(DBConnectionError)
async def db_connection_exception_handler(request: Request, exc: DBConnectionError):
    """DB 연결 실패 에러 처리 (503 Service Unavailable)"""
    return ORJSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "db_connection_failed",
            "error_description": "데이터베이스 연결에 실패했습니다. 잠시 후 다시 시도해주세요.",
        },
    )


@app.exception_handler(BaseORMException)
async def orm_exception_handler(request: Request, exc: BaseORMException):
    """기타 Tortoise ORM 에러 처리 (500 Internal Server Error)"""
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "database_error",
            "error_description": "데이터베이스 작업 중 오류가 발생했습니다.",
            "details": str(exc) if app.debug else None,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """예기치 못한 모든 에러 처리 (500 Internal Server Error)"""
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "error_description": "서버 내부에서 예상치 못한 오류가 발생했습니다.",
        },
    )


# --- 미들웨어 설정 ---

# CORS 설정 (환경별 분기)
if config.ENV == Env.PROD:
    # 운영 환경: 엄격한 설정
    cors_origins = [config.FRONTEND_URL]
    cors_methods = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
    cors_headers = ["Content-Type", "Authorization"]
else:
    # 로컬/개발 환경: 느슨한 설정
    cors_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    cors_methods = ["*"]
    cors_headers = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,  # 쿠키(refresh_token) 전송 허용
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)

# 보안 미들웨어 (입력값 검증 + 보안 헤더)
app.add_middleware(SecurityMiddleware)

# Rate Limiting 미들웨어 (IP 기반)
app.add_middleware(RateLimitMiddleware)

initialize_tortoise(app)

app.include_router(v1_routers)
