"""Core configuration and logging for AudioBookSync."""

from .config import Config
from .logging_config import configure_logging

__all__ = ["Config", "configure_logging"]
