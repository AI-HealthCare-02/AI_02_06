from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.apis.v1 import v1_routers
from app.db.databases import initialize_tortoise
from app.middlewares.security import SecurityMiddleware

app = FastAPI(
    default_response_class=ORJSONResponse, docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json"
)

# CORS 설정 (운영 도메인 없이 localhost 사용)
origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # 쿠키(refresh_token) 전송 허용
    allow_methods=["*"],
    allow_headers=["*"],
)

# 보안 미들웨어 (입력값 검증 + CSP 헤더)
app.add_middleware(SecurityMiddleware)

initialize_tortoise(app)

app.include_router(v1_routers)
