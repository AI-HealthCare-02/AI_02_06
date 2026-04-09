"""
AI Worker Entry Point

Phase 1: 기본 실행 및 헬스체크 지원
Phase 4: RQ 태스크 큐 통합 예정
"""

import signal
import sys
import time
from pathlib import Path

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
        import redis

        r = redis.from_url(config.REDIS_URL, socket_timeout=5)
        r.ping()
        return True
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return False


def health_check() -> dict:
    """헬스체크 상태 반환"""
    redis_ok = check_redis_connection()
    return {
        "status": "healthy" if redis_ok else "degraded",
        "redis": "connected" if redis_ok else "disconnected",
        "worker": "running",
    }


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
    logger.info("AI Worker ready - waiting for tasks...")

    # 메인 루프 (Phase 4에서 RQ 워커로 대체 예정)
    while not shutdown_requested:
        # TODO: Phase 4에서 RQ 워커 구현
        # 현재는 헬스체크용 대기 상태 유지
        time.sleep(1)

    logger.info("AI Worker shutdown complete")


if __name__ == "__main__":
    main()
