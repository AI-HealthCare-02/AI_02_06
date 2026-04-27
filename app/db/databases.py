"""Database configuration module.

This module contains Tortoise ORM configuration and initialization
for the FastAPI application with modern Python patterns.
"""

from typing import Any

from fastapi import FastAPI
from tortoise import Tortoise
from tortoise.contrib.fastapi import register_tortoise

from app.core import config

# Tortoise ORM model modules
TORTOISE_APP_MODELS: list[str] = [
    "aerich.models",
    "app.models.accounts",
    "app.models.refresh_tokens",
    "app.models.profiles",
    "app.models.medication",
    "app.models.medicine_info",
    "app.models.medicine_chunk",
    "app.models.medicine_ingredient",
    "app.models.lifestyle_guide",
    "app.models.daily_symptom_log",
    "app.models.challenge",
    "app.models.chat_sessions",
    "app.models.messages",
    "app.models.message_feedbacks",
    "app.models.intake_log",
    "app.models.data_sync_log",
    "app.models.ocr_draft",
]

# Tortoise ORM configuration
TORTOISE_ORM: dict[str, Any] = {
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
    """Initialize Tortoise ORM with FastAPI application.

    Sets up database models and registers Tortoise ORM with the FastAPI app
    for automatic connection management and lifecycle handling.

    Args:
        app: FastAPI application instance to register with.
    """
    Tortoise.init_models(TORTOISE_APP_MODELS, "models")
    register_tortoise(app, config=TORTOISE_ORM)
