"""
AI Worker Entry Point - Fixed Version
- RQ 버전 호환성 해결
- Redis 객체 누락 수정
- 아키텍처 가드레일 강화
"""

import signal
import sys
import time
from pathlib import Path

import redis

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai_worker.core.config import config
from ai_worker.core.logger import get_logger

logger = get_logger(__name__)

# Graceful shutdown 플래그
shutdown_requested = False


def signal_handler(signum, frame):
    """시그널 핸들러: SIGTERM, SIGINT 처리"""
    global shutdown_requested
    sig_name = signal.Signals(signum).name
    logger.info(f"Received {sig_name}, initiating graceful shutdown...")
    shutdown_requested = True


def check_redis_connection() -> bool:
    """Redis 연결 상태 확인"""
    try:
        r = redis.from_url(config.REDIS_URL, socket_timeout=5)
        r.ping()
        return True
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return False


def main():
    """메인 워커 루프"""
    global shutdown_requested

    # 시그널 핸들러 등록
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("AI Worker starting...")
    logger.info(f"Timezone: {config.TIMEZONE}")

    # Redis 연결 대기
    retry_count = 0
    max_retries = 30
    while not check_redis_connection() and retry_count < max_retries:
        retry_count += 1
        logger.info(f"Waiting for Redis... ({retry_count}/{max_retries})")
        time.sleep(2)

    if retry_count >= max_retries:
        logger.error("Failed to connect to Redis after max retries")
        sys.exit(1)
    logger.info("Redis connected successfully")

    # RQ 관련 임포트 (버전 호환성을 위해 내부에서 호출)
    from rq import Queue, Worker

    # Redis 연결 객체 생성
    redis_conn = redis.from_url(config.REDIS_URL)

    # 큐 및 워커 설정
    queues = [Queue("ai", connection=redis_conn), Queue("default", connection=redis_conn)]

    logger.info("AI Worker ready - waiting for tasks...")

    try:
        worker = Worker(queues, connection=redis_conn)
        worker.work(with_scheduler=True)
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
