from fastapi import APIRouter

from app.apis.v1.auth_routers import auth_router
from app.apis.v1.mock_oauth_routers import mock_router
from app.apis.v1.oauth_routers import oauth_router
from app.apis.v1.user_routers import user_router

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(mock_router)
v1_routers.include_router(oauth_router)
v1_routers.include_router(user_router)
