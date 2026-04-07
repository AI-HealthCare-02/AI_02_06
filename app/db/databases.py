from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from app.core import config

TORTOISE_APP_MODELS = [
    "aerich.models",
    "app.models.accounts",
    "app.models.refresh_tokens",
    "app.models.profiles",
    "app.models.medication",
    "app.models.challenge",
    "app.models.chat_sessions",
    "app.models.messages",
    "app.models.message_feedbacks",
    "app.models.intake_log",
    "app.models.drug_interaction_cache",
    "app.models.llm_response_cache",
]

TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": config.DB_HOST,
                "port": config.DB_PORT,
                "user": config.DB_USER,
                "password": config.DB_PASSWORD,
                "database": config.DB_NAME,
                "timeout": config.DB_CONNECT_TIMEOUT,
                "maxsize": config.DB_CONNECTION_POOL_MAXSIZE,
            },
        },
    },
    "apps": {
        "models": {
            "models": TORTOISE_APP_MODELS,
        },
    },
    "timezone": "Asia/Seoul",
}


def initialize_tortoise(app: FastAPI) -> None:
    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
    register_tortoise(app, config=TORTOISE_ORM)
