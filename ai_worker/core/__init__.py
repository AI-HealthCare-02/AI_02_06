"""AI Worker core module.

This module provides core functionality for the AI worker including
configuration management and logging setup.
"""

from ai_worker.core.config import Config, config
from ai_worker.core.logger import get_logger, setup_logger

__all__ = ["Config", "config", "get_logger", "setup_logger"]
