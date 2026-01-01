"""Domain models for AudioBookSync.

This module contains core domain models and interfaces that represent
the business entities and contracts used throughout the application.
"""

from .book import Book
from .progress import safe_progress_callback, ProgressCallback

__all__ = [
    "Book",
    "safe_progress_callback",
    "ProgressCallback",
]
