"""
Generic request handlers for common API patterns.

Provides reusable handlers for paginated list endpoints and other common patterns.
"""

import inspect
from typing import Any, Callable, Optional, Type, TypeVar, Union

from fastapi import Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.services import book_service, user_service
from ..middleware.error_handler import AuthorizationError
from .auth_utils import get_user_id
from .pagination import calculate_pages, paginate_list, validate_page

T = TypeVar("T")
ResponseT = TypeVar("ResponseT")


def verify_book_ownership(book: Union[dict, object], user_id: str, asin: str) -> None:
    """
    Verify that a book belongs to the specified user.

    Handles both dict-like and object attribute access for user_id.

    Args:
        book: Book object (dict or ORM model)
        user_id: User ID to verify ownership against
        asin: Amazon Standard Identification Number (for logging)

    Raises:
        AuthorizationError: If the book doesn't belong to the user
    """
    # Extract user_id from book (handles both dict and object access)
    book_user_id = book.get("user_id") if isinstance(book, dict) else str(book.user_id)

    if book_user_id != user_id:
        logger.warning(f"Unauthorized access attempt to audiobook {asin} by user {user_id}")
        raise AuthorizationError("Not authorized to access this book")


async def verify_book_access(
    db: AsyncSession,
    asin: str,
    current_user: Any,
) -> tuple[Any, Any]:
    """
    Verify the current user can access a book, including shared family libraries.

    Returns (UserBook, Book) when access is allowed.
    """
    user_id = get_user_id(current_user)
    family_id = None
    if hasattr(current_user, "family_id"):
        family_id = current_user.family_id
    elif isinstance(current_user, dict):
        family_id = current_user.get("family_id")

    accessible_user_ids = await user_service.get_accessible_user_ids(
        db=db,
        user_id=user_id,
        family_id=family_id,
    )
    user_book_with_book = await book_service.get_user_book_for_user_ids(
        db,
        accessible_user_ids,
        asin,
    )
    if not user_book_with_book:
        logger.warning(f"Unauthorized access attempt to audiobook {asin} by user {user_id}")
        raise AuthorizationError("Not authorized to access this book")

    return user_book_with_book


def get_pagination_params(
    page_default: int = 1,
    page_size_default: int = 50,
    page_size_max: int = 100,
):
    """
    Create pagination Query parameters with customizable defaults and limits.

    Args:
        page_default: Default page number (default: 1)
        page_size_default: Default items per page (default: 50)
        page_size_max: Maximum items per page limit (default: 100)

    Returns:
        Tuple of (page, page_size) Query parameters

    Example:
        page, page_size = get_pagination_params(page_size_default=10, page_size_max=50)

        @router.get("/items")
        async def get_items(
            page: int = page,
            page_size: int = page_size,
        ):
            ...
    """
    page = Query(
        default=page_default,
        ge=1,
        description="Page number (starting from 1)",
    )
    page_size = Query(
        default=page_size_default,
        ge=1,
        le=page_size_max,
        description=f"Number of items per page (1-{page_size_max})",
    )
    return page, page_size


async def get_paginated_list(
    get_items_func: Callable,
    response_model: Type,
    get_items_kwargs: dict,
    user_id: str,
    page: int,
    page_size: int,
    count_func: Optional[Callable] = None,
    count_kwargs: Optional[dict] = None,
    resource_name: str = "items",
) -> dict:
    """
    Generic handler for paginated list endpoints.

    Supports both database-level pagination (using limit/offset with separate count)
    and in-memory pagination (loading all items and slicing).

    Args:
        get_items_func: Async function to fetch items. Should accept **get_items_kwargs
        response_model: Pydantic model or ORM class for item conversion
        get_items_kwargs: Kwargs to pass to get_items_func. Should include 'db', 'user_id', etc.
        user_id: User ID for logging
        page: Requested page number (1-indexed)
        page_size: Number of items per page
        count_func: Optional async function to count total items. If None, uses len(items)
        count_kwargs: Optional kwargs for count_func
        resource_name: Human-readable resource name for logging

    Returns:
        Dict with 'items', 'total', 'page', 'page_size', and 'pages' keys

    Example:
        # Database-level pagination (downloads, decryptions)
        result = await get_paginated_list(
            get_items_func=download_service.get_downloads_by_user,
            response_model=DownloadResponse,
            get_items_kwargs={
                "db": db,
                "user_id": str(current_user.user_id),
                "status": status_filter,
                "limit": page_size,
                "offset": (page - 1) * page_size,
            },
            user_id=str(current_user.user_id),
            page=page,
            page_size=page_size,
            count_func=download_service.count_downloads_by_user,
            count_kwargs={
                "db": db,
                "user_id": str(current_user.user_id),
                "status": status_filter,
            },
            resource_name="downloads",
        )

        # In-memory pagination (library, sync)
        all_items = await book_service.get_books_by_user(db, str(current_user.user_id))
        result = await get_paginated_list(
            get_items_func=lambda **kwargs: all_items,
            response_model=BookResponse,
            get_items_kwargs={},
            user_id=str(current_user.user_id),
            page=page,
            page_size=page_size,
            resource_name="books",
        )
    """
    logger.info(f"Fetching {resource_name} for user {user_id}")

    # Get items (handle both async and sync functions)
    result = get_items_func(**get_items_kwargs)
    if inspect.iscoroutine(result):
        items = await result
    else:
        items = result

    # Get total count (handle both async and sync functions)
    if count_func:
        count_result = count_func(**(count_kwargs or {}))
        if inspect.iscoroutine(count_result):
            total = await count_result
        else:
            total = count_result
    else:
        total = len(items)

    # Calculate and validate pagination
    pages = calculate_pages(total, page_size)
    validated_page = validate_page(page, pages, total)

    # If using database-level pagination, items are already sliced
    if count_func:
        response_items = items
    else:
        # In-memory pagination: slice the items
        response_items, validated_page, pages = paginate_list(items, validated_page, page_size)

    # Convert to response objects
    try:
        # Handle both ORM models (with .from_orm()) and dict models (with **)
        converted_items = []
        for item in response_items:
            if isinstance(item, dict):
                converted_items.append(response_model(**item))
            elif hasattr(response_model, "from_orm"):
                converted_items.append(response_model.from_orm(item))
            else:
                converted_items.append(item)
    except Exception as e:
        logger.error(f"Failed to convert {resource_name} to response model: {e}")
        converted_items = response_items

    logger.info(
        f"Retrieved {len(converted_items)} {resource_name} for user {user_id} "
        f"(page {validated_page}/{pages})"
    )

    return {
        "items": converted_items,
        "total": total,
        "page": validated_page,
        "page_size": page_size,
        "pages": pages,
    }
