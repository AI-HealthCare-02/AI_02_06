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


# Global logger for the application
default_logger = setup_logger()
