"""
AI Worker Entry Point - Fixed Version
- RQ 버전 호환성 해결
- Redis 객체 누락 수정
- 아키텍처 가드레일 강화
"""

import signal
import sys
import redis # Redis 라이브러리 명시적 임포트
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
        r = redis.from_url(config.REDIS_URL, socket_timeout=5)
        r.ping()
        return True
    except Exception as e:
        logger.warning(f"Redis connection failed: {e}")
        return False


def main():
    """RQ 기반 워커 실행"""
    global shutdown_requested

    # 시그널 핸들러 등록
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("AI Worker starting...")
    logger.info(f"Timezone: {config.TIMEZONE}")

    # 1. Redis 연결 확인 (가드레일)
    if not check_redis_connection():
        logger.error("Redis connection failed. Ensure REDIS_URL is reachable.")
        sys.exit(1)

    # 2. RQ 관련 임포트 (버전 호환성을 위해 내부에서 호출)
    from rq import Queue, Worker

    # 3. Redis 연결 객체 생성
    # [수정] Redis.from_url -> redis.from_url (임포트 경로 수정)
    redis_conn = redis.from_url(config.REDIS_URL)

    # 4. 큐 및 워커 설정
    # [아키텍트 팁] Connection 클래스에 의존하지 않고 worker에 직접 주입하는 방식이 가장 안전합니다.
    queues = [Queue("ai", connection=redis_conn), Queue("default", connection=redis_conn)]

    logger.info("Redis connected successfully")
    logger.info("RQ Worker ready - waiting for tasks...")

    try:
        # [수정] Connection 컨텍스트 매니저 대신 직접 주입하여 버전 이슈 원천 차단
        worker = Worker(queues, connection=redis_conn)
        worker.work(with_scheduler=True)
    except Exception as e:
        logger.error(f"Worker crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()