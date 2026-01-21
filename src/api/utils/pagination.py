"""
Pagination utilities for API responses.

Provides helper functions for calculating pagination metadata and slicing items.
"""

import logging
from typing import List, Tuple, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


def calculate_pagination(total: int, page: int, page_size: int) -> Tuple[int, int, int]:
    """
    Calculate pagination parameters.

    Args:
        total: Total number of items
        page: Requested page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Tuple of (validated_page, total_pages, calculated_pages_value)
    """
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    # Validate page number
    if page > pages and total > 0:
        logger.warning(f"Page {page} exceeds max pages {pages}")
        page = pages

    return page, pages, pages


def paginate_list(items: List[T], page: int, page_size: int) -> Tuple[List[T], int, int]:
    """
    Paginate an in-memory list of items.

    Args:
        items: List of items to paginate
        page: Requested page number (1-indexed)
        page_size: Number of items per page

    Returns:
        Tuple of (paginated_items, validated_page, total_pages)
    """
    total = len(items)
    validated_page, pages, _ = calculate_pagination(total, page, page_size)

    # Apply pagination slicing
    start_idx = (validated_page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_items = items[start_idx:end_idx]

    return paginated_items, validated_page, pages


def calculate_pages(total: int, page_size: int) -> int:
    """
    Calculate total number of pages.

    Args:
        total: Total number of items
        page_size: Number of items per page

    Returns:
        Total number of pages
    """
    return (total + page_size - 1) // page_size if total > 0 else 1


def validate_page(page: int, pages: int, total: int) -> int:
    """
    Validate and adjust page number if it exceeds available pages.

    Args:
        page: Requested page number (1-indexed)
        pages: Total number of pages
        total: Total number of items

    Returns:
        Validated page number
    """
    if page > pages and total > 0:
        logger.warning(f"Page {page} exceeds max pages {pages}")
        return pages
    return page
