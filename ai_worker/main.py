"""AI Worker Entry Point - Final Merged Version.

This module contains the main entry point for the AI worker service.
Includes Redis connection retry logic and RQ version compatibility handling.
"""

import asyncio
from pathlib import Path
import signal
import sys
import time

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_worker.core.config import config
from ai_worker.core.logger import get_logger
from ai_worker.core.redis_client import make_sync_redis

logger = get_logger(__name__)


def warmup_embedding_model() -> None:
    """Pre-load ko-sroberta into memory and run a dummy encode.

    첫 사용자 요청이 cold-start 비용(~30초)을 뒤집어쓰지 않도록 RQ 워커
    루프가 돌기 전에 모델을 메모리에 올리고 dummy encode 한 번을 돌린다.
    ``_ensure_model`` 내부에서 warmup encode 까지 수행한다.
    """
    try:
        from ai_worker.domains.rag.embedding_provider import _ensure_model

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
        redis_client = make_sync_redis(config.REDIS_URL, socket_timeout=5)
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

    # ── Redis 연결 옵션 (BLPOP 자연 반환 후 reconnect 안정화) ──────────
    # SimpleWorker.work() 은 BLPOP 타임아웃(=worker_ttl-15s) 이 풀릴 때마다
    # 다시 BLPOP 을 호출하는데, 이 사이에 Redis 연결이 끊긴 상태라면
    # ``Redis connection timeout, quitting...`` 으로 워커 자체가 종료된다.
    # ``make_sync_redis`` 가 keepalive + retry 옵션을 일괄 적용한다.
    redis_conn = make_sync_redis(config.REDIS_URL)

    # Setup queues and worker
    # Direct injection instead of Connection context manager to prevent version issues
    queues: list[Queue] = [Queue("ai", connection=redis_conn), Queue("default", connection=redis_conn)]

    logger.info("AI Worker ready - waiting for tasks...")

    # ── SimpleWorker 사용 이유 + 재시작 supervision 루프 ─────────────────
    # SimpleWorker = no fork, single-process job execution.
    # 일반 Worker 는 매 job 마다 child 프로세스를 fork 하는데, PyTorch 의
    # 내부 스레드와 fork() 조합은 알려진 deadlock 을 유발해 embed_text_job
    # 이 30 초 안에 끝나지 않는 timeout 을 일으킨다. SimpleWorker 로
    # 부모 프로세스의 warmed 모델 + AsyncOpenAI 싱글톤 + ThreadPool 을
    # 그대로 재사용하면서 결정적으로 실행되게 한다.
    #
    # worker_ttl=180: BLPOP 타임아웃 = ttl - 15 = 165s.
    # 기본 420 이면 BLPOP 이 ~7분 블로킹하는데 Docker bridge / WSL2 NAT 가
    # 그 이상 idle TCP 세션을 유지해주지 않아 "Redis connection timeout,
    # quitting..." 로 워커 자체 종료. TTL 을 180s 로 낮추면 매 ~165s 마다
    # BLPOP 이 자연 반환 → 재호출로 연결을 실질적으로 idle 상태에 두지 않음.
    #
    # 재시작 supervision 루프:
    # BLPOP 가 ``redis.TimeoutError`` 를 raise 하면 RQ 메인 loop
    # (``rq/worker/base.py:625``) 가 **예외를 swallow 하고 break + return** 한다.
    # 즉 ``worker.work()`` 는 예외를 던지지 않고 정상 return 처럼 빠져나오므로
    # 우리는 ``except redis.TimeoutError`` 로 catch 할 수 없다. 대신 work()
    # return 후 ``worker._stop_requested`` 플래그로 진짜 종료(SIGTERM) 와
    # 비정상 종료(TimeoutError 로 인한 RQ 내부 break) 를 구분한다.
    while True:
        worker = SimpleWorker(queues, connection=redis_conn, worker_ttl=180)
        try:
            worker.work(with_scheduler=True)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Termination signal received, exiting supervision loop")
            break
        except Exception:
            logger.exception("Worker crashed unexpectedly")
            sys.exit(1)

        if worker._stop_requested:  # noqa: SLF001 — RQ public API 부재, 종료 신호 구분 위해 직접 참조
            logger.info("Stop requested, exiting supervision loop")
            break

        logger.warning("Worker exited unexpectedly (likely Redis timeout); restarting in 2s")
        time.sleep(2)


if __name__ == "__main__":
    main()
