"""Logging configuration module.

콘솔 (stdout) + 파일 (RotatingFileHandler + JSON 구조화) 이중 출력.
- 콘솔: 사람 읽기 형식 (`[ts] [LEVEL] [name:line] msg`) — docker logs / 개발자 직관용
- 파일: JSON line — machine-readable, jq / log 분석 도구 호환

파일 위치는 ``LOG_DIR`` 환경변수로 결정 (default ``/app/logs``). docker-compose
의 volume 마운트로 호스트에 영속화. 매 빌드 시작 시 호스트의 ``~/logs`` 는
삭제되고 (한 세대 prev 백업) 새 라이프사이클로 시작 — 본 모듈은 디렉토리만
보장하면 충분하다.

CLAUDE.md §9 의 핵심 룰 준수:
- 모듈별 logger (``getLogger(__name__)`` 호출자 측에서)
- 구조화 (JSON) — 파일 핸들러 한정
- rotating (10MB x 5)
- 보안: 호출자가 PII / token / huge payload 를 message 에 넣지 않을 책임
"""

from datetime import UTC, datetime
import json
import logging
import logging.handlers
import os
from pathlib import Path
import sys

_LOG_DIR_ENV = "LOG_DIR"
_DEFAULT_LOG_DIR = "/app/logs"
_FILE_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_FILE_BACKUP_COUNT = 5
_CONSOLE_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s"


class JsonFormatter(logging.Formatter):
    """JSON line formatter — 한 record 당 한 줄 JSON 출력.

    필드: ts (UTC ISO 8601), level, logger, msg, module, line, exception (있을 때).
    ``logger.exception()`` 호출 시 stack trace 가 ``exception`` 에 포함된다.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _resolve_log_dir() -> Path:
    """``LOG_DIR`` env 우선, 미설정 시 ``/app/logs``. 디렉토리는 idempotent 생성."""
    log_dir = Path(os.environ.get(_LOG_DIR_ENV, _DEFAULT_LOG_DIR))
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logger(
    name: str = "app",
    level: int = logging.INFO,
) -> logging.Logger:
    """Set up a logger with console + rotating-file handlers.

    Args:
        name: Logger name for identification. 같은 이름으로 두 번 호출되면
            기존 logger 를 그대로 반환 (handler 중복 방지).
        level: Logging level (default: INFO).

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False  # 루트 logger 로 중복 전달 방지

    console_formatter = logging.Formatter(_CONSOLE_FORMAT)
    json_formatter = JsonFormatter()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    try:
        log_dir = _resolve_log_dir()
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / f"{name}.log",
            maxBytes=_FILE_MAX_BYTES,
            backupCount=_FILE_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(json_formatter)
        logger.addHandler(file_handler)
    except OSError:
        # 파일 시스템 권한 문제 등으로 파일 핸들러 생성 실패 시 콘솔만 유지.
        # 정확한 원인은 콘솔 logger 가 직접 emit (logger 자기 자신에 의존하지 않음).
        logger.warning("Failed to attach RotatingFileHandler — console only", exc_info=True)

    return logger


# Global loggers for the application.
# FastAPI 프로세스가 ai_worker.* 모듈도 import 하므로 (예: RAG 응답 생성기)
# 그 namespace 도 INFO 핸들러를 미리 등록한다 — 그렇지 않으면 ai_worker.*
# INFO 가 root logger 의 default WARNING 에 걸려 누락된다.
default_logger = setup_logger()
_ai_worker_logger = setup_logger("ai_worker")
