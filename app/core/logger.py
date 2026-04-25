"""Logging configuration module.

This module provides logging setup functionality for the application
with modern Python logging patterns and type safety.
"""

import logging
import sys


def setup_logger(
    name: str = "app",
    level: int = logging.INFO,
) -> logging.Logger:
    """Set up a logger with console output.

    Args:
        name: Logger name for identification.
        level: Logging level (default: INFO).

    Returns:
        logging.Logger: Configured logger instance with console handler.
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers (important for multiple imports)
    if logger.handlers:
        return logger

    logger.setLevel(level)

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")

    # Console output handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.propagate = False  # Prevent duplicate forwarding to root logger

    return logger


# Global loggers for the application.
# The FastAPI process also imports modules from `ai_worker/*` (e.g. the
# RAG response generator at `ai_worker.domains.rag.response_generator`),
# so we register an INFO-level handler for that namespace as well.
# Without this, `ai_worker.*` INFO
# logs propagate to the Python root logger (default level WARNING) and
# get filtered out, while WARNING/ERROR still show with a bare format.
default_logger = setup_logger()
_ai_worker_logger = setup_logger("ai_worker")
