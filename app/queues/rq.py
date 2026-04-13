import os

from redis import Redis
from rq import Queue


def get_redis_url() -> str:
    # Prefer explicit env var; fallback to common local default
    return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def get_redis_connection() -> Redis:
    return Redis.from_url(get_redis_url())


def get_queue(name: str = "default") -> Queue:
    return Queue(name=name, connection=get_redis_connection())

