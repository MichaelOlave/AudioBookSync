"""Domain models for AudioBookSync.

This module contains core domain models and interfaces that represent
the business entities and contracts used throughout the application.
"""

from .progress import ProgressCallback, safe_progress_callback

__all__ = [
    "safe_progress_callback",
    "ProgressCallback",
]
