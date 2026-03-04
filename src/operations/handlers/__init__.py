"""Operation handlers for complex workflows.

This module provides handler classes that orchestrate multi-step operations
and encapsulate business logic that would otherwise be spread across multiple
functions.
"""

from .book_processor import BookProcessingHandler, book_processor

__all__ = [
    "BookProcessingHandler",
    "book_processor",
]
