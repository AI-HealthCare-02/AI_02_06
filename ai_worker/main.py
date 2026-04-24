"""AI Worker Entry Point - Final Merged Version.

This module contains the main entry point for the AI worker service.
Includes Redis connection retry logic and RQ version compatibility handling.
"""

import asyncio
from pathlib import Path
import signal
import socket
import sys
import time

import redis

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_worker.core.config import config
from ai_worker.core.logger import get_logger

logger = get_logger(__name__)


def warmup_embedding_model() -> None:
    """Pre-load ko-sroberta into memory and run a dummy encode.

    첫 사용자 요청이 cold-start 비용(~30초)을 뒤집어쓰지 않도록 RQ 워커
    루프가 돌기 전에 모델을 메모리에 올리고 dummy encode 한 번을 돌린다.
    ``_ensure_model`` 내부에서 warmup encode 까지 수행한다.
    """
    try:
        from ai_worker.providers.embedding import _ensure_model

        logger.info("Pre-warming embedding model...")
        t0 = time.perf_counter()
        asyncio.run(_ensure_model())
        elapsed = time.perf_counter() - t0
        logger.info("Embedding model warmed up in %.2fs", elapsed)
    except Exception:
        # 비정상이면 로그만 남기고 워커 기동은 계속한다. 첫 요청이 느려질 뿐이다.
        logger.exception("Embedding warmup failed (non-fatal)")


# Graceful shutdown flag
shutdown_requested = False


def signal_handler(signum: int, _frame: object) -> None:
    """Signal handler for SIGTERM and SIGINT.

    Args:
        signum: Signal number.
        _frame: Current stack frame (unused).
    """
    global shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info("Received %s, initiating graceful shutdown...", sig_name)
    shutdown_requested = True


def check_redis_connection() -> bool:
    """Check Redis connection status.

    Returns:
        bool: True if Redis is connected, False otherwise.
    """
    try:
        redis_client = redis.from_url(config.REDIS_URL, socket_timeout=5)
        redis_client.ping()
        return True
    except Exception as e:
        logger.warning("Redis connection failed: %s", e)
        return False


def main() -> None:
    """Main worker loop.

    Initializes the AI worker, connects to Redis, and starts processing tasks.
    """
    global shutdown_requested

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("AI Worker starting...")
    logger.info("Timezone: %s", config.TIMEZONE)

    # Wait for Redis connection (with retry logic)
    retry_count = 0
    max_retries = 30

    while not check_redis_connection() and retry_count < max_retries:
        retry_count += 1
        logger.info("Waiting for Redis... (%d/%d)", retry_count, max_retries)
        time.sleep(2)

    if retry_count >= max_retries:
        logger.error("Failed to connect to Redis after max retries. Exiting.")
        sys.exit(1)

    logger.info("Redis connected successfully")

    # Warm up the embedding model before accepting jobs so the first
    # user-facing request does not pay the cold-start cost.
    warmup_embedding_model()

    # Import RQ components (inside function for version compatibility)
    from rq import Queue, SimpleWorker

    # Create Redis connection object.
    # RQ 2.x worker 는 pubsub subscribe 를 dedicated 연결로 유지한다. 이 연결이
    # idle 상태로 오래 남으면 Docker bridge / WSL2 가상 네트워크가 TCP 세션을
    # silent drop → worker 가 "Redis connection timeout, quitting..." 로 자체 종료.
    # health_check_interval 은 command connection pool 에만 작동하므로 pubsub
    # 용까지 커버하려면 OS 레벨 TCP keepalive 를 명시해야 한다.
    # TCP_KEEPIDLE=60  : 60초 idle 후 keepalive probe 시작
    # TCP_KEEPINTVL=10 : probe 실패 시 10초 간격 재시도
    # TCP_KEEPCNT=3    : 3회 실패 시 연결 끊김 감지
    # 즉 최대 60 + 10*3 = 90초 내로 dead connection 이 감지되어 복구된다.
    redis_conn = redis.from_url(
        config.REDIS_URL,
        health_check_interval=30,
        socket_keepalive=True,
        socket_keepalive_options={
            socket.TCP_KEEPIDLE: 60,
            socket.TCP_KEEPINTVL: 10,
            socket.TCP_KEEPCNT: 3,
        },
        socket_connect_timeout=10,
    )

    # Setup queues and worker
    # Direct injection instead of Connection context manager to prevent version issues
    queues: list[Queue] = [Queue("ai", connection=redis_conn), Queue("default", connection=redis_conn)]

    logger.info("AI Worker ready - waiting for tasks...")

    try:
        # SimpleWorker = no fork, single-process job execution.
        # 일반 Worker 는 매 job 마다 child 프로세스를 fork 하는데, PyTorch 의
        # 내부 스레드와 fork() 조합은 알려진 deadlock 을 유발해 embed_text_job
        # 이 30 초 안에 끝나지 않는 timeout 을 일으킨다. SimpleWorker 로
        # 부모 프로세스의 warmed 모델 + AsyncOpenAI 싱글톤 + ThreadPool 을
        # 그대로 재사용하면서 결정적으로 실행되게 한다.
        worker = SimpleWorker(queues, connection=redis_conn)
        worker.work(with_scheduler=True)
    except Exception as e:
        logger.error("Worker crashed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
