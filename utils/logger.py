"""
日志工具
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import config


def setup_logger():
    """配置日志"""

    # 移除默认handler
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=config.settings.log_level,
        colorize=True
    )

    # 文件输出 - 所有日志
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / "test_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # 每天轮转
        retention="30 days",  # 保留30天
        compression="zip",  # 压缩
        encoding="utf-8"
    )

    # 文件输出 - 错误日志
    logger.add(
        log_dir / "error_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention="60 days",
        compression="zip",
        encoding="utf-8"
    )

    return logger


# 初始化logger
log = setup_logger()