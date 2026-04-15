from __future__ import annotations

import logging
import sys
from pathlib import Path

from .settings import get_settings

try:
    from loguru import logger as _loguru_logger
except ImportError:  # pragma: no cover - fallback for minimal environments
    _loguru_logger = None


class _StdLoggerAdapter:
    def __init__(self):
        self._logger = logging.getLogger("aitrader")

    def remove(self):
        self._logger.handlers.clear()

    def add(self, sink, level="INFO", format=None, **kwargs):
        handler = logging.FileHandler(sink) if isinstance(sink, (str, Path)) else logging.StreamHandler(sink)
        handler.setLevel(getattr(logging, str(level).upper(), logging.INFO))
        handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"))
        self._logger.addHandler(handler)
        self._logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))

    def info(self, message, *args, **kwargs):
        self._logger.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self._logger.error(message, *args, **kwargs)


logger = _loguru_logger or _StdLoggerAdapter()


def setup_logging(log_name: str = "aitrader.log", level: str | None = None):
    settings = get_settings()
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = Path(settings.logs_dir) / log_name
    logger.remove()
    logger.add(
        sys.stderr,
        level=level or settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    logger.add(log_path, level="DEBUG", rotation="10 MB", retention="7 days")
    return logger
