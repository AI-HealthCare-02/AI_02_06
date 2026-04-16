"""AI Worker Entry Point - Final Merged Version.

This module contains the main entry point for the AI worker service.
Includes Redis connection retry logic and RQ version compatibility handling.
"""

from pathlib import Path
import signal
import sys
import time

import redis

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_worker.core.config import config
from ai_worker.core.logger import get_logger

logger = get_logger(__name__)

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

    # Import RQ components (inside function for version compatibility)
    from rq import Queue, Worker

    # Create Redis connection object
    redis_conn = redis.from_url(config.REDIS_URL)

    # Setup queues and worker
    # Direct injection instead of Connection context manager to prevent version issues
    queues: list[Queue] = [Queue("ai", connection=redis_conn), Queue("default", connection=redis_conn)]

    logger.info("AI Worker ready - waiting for tasks...")

    try:
        # Enable scheduler functionality with with_scheduler=True
        worker = Worker(queues, connection=redis_conn)
        worker.work(with_scheduler=True)
    except Exception as e:
        logger.error("Worker crashed: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
