"""Loguru logging setup.

业务功能: 统一 appapi 控制台日志和滚动文件日志。
算法要点: 使用 enqueue=True 让多线程请求日志先进入队列，减少同步写入对
HTTP 请求路径的影响。
"""

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
    """业务功能: 初始化 stdout 和 appapi.log 两个日志 sink。"""
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
