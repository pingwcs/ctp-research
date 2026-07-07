"""Loguru logging setup."""

import sys

from loguru import logger

from appapi.core.config import settings


LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logging() -> None:
    settings.log_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stdout, format=LOG_FORMAT, level="INFO", enqueue=True)
    logger.add(
        settings.log_dir / "appapi.log",
        format=LOG_FORMAT,
        level="INFO",
        rotation="20 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
        encoding="utf-8",
    )
