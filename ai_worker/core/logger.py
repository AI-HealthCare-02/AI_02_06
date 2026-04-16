"""AI Worker logging configuration module.

This module provides logging setup functionality for the AI worker service.
"""

import logging
import sys


def setup_logger(
    name: str = "AI Worker",
    level: int = logging.INFO,
) -> logging.Logger:
    """Set up a logger with console output.

    Args:
        name: Logger name.
        level: Logging level.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers (important)
    if logger.handlers:
        return logger

    logger.setLevel(level)

    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s")

    # Console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.propagate = False  # Prevent duplicate forwarding to root logger

    return logger


def get_logger(name: str) -> logging.Logger:
    """Create a module-specific logger.

    Args:
        name: Module name for the logger.

    Returns:
        logging.Logger: Configured logger instance.
    """
    return setup_logger(name)
