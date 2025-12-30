"""Logging configuration for AudioBookSync."""

import sys

from loguru import logger


def configure_logging(log_level: str = "INFO") -> None:
    """Configure loguru with stderr and file output."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level}</level> | "
            "<level>{message}</level>"
        ),
    )
    logger.add(
        "logs/{time}.log",
        rotation="500 MB",
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level>"
        ),
    )
