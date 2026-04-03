from fastapi import APIRouter

from app.apis.v1.auth_routers import auth_router
from app.apis.v1.challenge_routers import router as challenge_router
from app.apis.v1.intake_log_routers import router as intake_log_router
from app.apis.v1.medication_routers import router as medication_router
from app.apis.v1.mock_oauth_routers import mock_router
from app.apis.v1.oauth_routers import oauth_router
from app.apis.v1.user_routers import user_router

v1_routers = APIRouter(prefix="/api/v1")
v1_routers.include_router(auth_router)
v1_routers.include_router(challenge_router)
v1_routers.include_router(intake_log_router)
v1_routers.include_router(medication_router)
v1_routers.include_router(mock_router)
v1_routers.include_router(oauth_router)
v1_routers.include_router(user_router)
