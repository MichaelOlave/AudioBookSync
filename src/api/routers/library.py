"""User library endpoints."""

import json
from decimal import Decimal
from typing import Any, Dict

import audible
from fastapi import APIRouter, Depends, Query
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.engine import get_db_session
from ...database.models.user import User
from ...database.services import book_service, user_service
from ..middleware.error_handler import (
    AuthorizationError,
    ResourceNotFoundError,
    handle_route_errors,
)
from ..schemas.book import BookList, BookResponse
from ..security.auth import get_current_user
from ..utils.auth_utils import get_user_id
from ..utils.generic_handlers import (
    get_paginated_list,
    get_pagination_params,
    verify_book_ownership,
)

router = APIRouter()

# Pagination parameters for library endpoint
_lib_page, _lib_page_size = get_pagination_params(page_size_default=50, page_size_max=100)


@router.get(
    "/",
    response_model=BookList,
    summary="Get user's library",
    description="Get paginated list of books in user's library",
    responses={
        200: {"description": "Library retrieved successfully"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("get library")
async def get_library(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    page: int = _lib_page,
    page_size: int = _lib_page_size,
) -> BookList:
    """
    Get user's audiobook library with pagination.

    Retrieves all books owned by the current user, ordered by purchase date.

    Args:
        current_user: Current authenticated user (from JWT token)
        db: Database session
        page: Page number for pagination (default: 1)
        page_size: Items per page (default: 50, max: 100)

    Returns:
        BookList: Paginated list of user's books with metadata

    Example:
        GET /api/v1/library?page=1&page_size=50
    """

    async def get_books(**kwargs):
        return await book_service.get_books_by_user(kwargs["db"], kwargs["user_id"])

    result = await get_paginated_list(
        get_items_func=get_books,
        response_model=BookResponse,
        get_items_kwargs={
            "db": db,
            "user_id": get_user_id(current_user),
        },
        user_id=get_user_id(current_user),
        page=page,
        page_size=page_size,
        resource_name="books",
    )

    return BookList(**result)


@router.get(
    "/audible/fetch",
    summary="Fetch library from Audible and save to database",
    description="Fetch user's audiobook library from Audible API and save books to database",
    responses={
        200: {"description": "Library fetched and saved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Audible credentials not configured"},
        500: {"description": "Failed to fetch from Audible"},
    },
)
@handle_route_errors("fetch Audible library")
async def fetch_audible_library(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    num_results: int = Query(
        default=1000,
        ge=1,
        le=1000,
        description="Number of results to fetch (1-1000)",
    ),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number to fetch (starting from 1)",
    ),
) -> Dict[str, Any]:
    """
    Fetch user's audiobook library from Audible API and save to database.

    Uses stored Audible credentials to retrieve the complete library
    from Audible's servers and saves book data to the database without
    downloading the audiobook files.

    Args:
        current_user: Current authenticated user (from JWT token)
        db: Database session
        num_results: Number of books to fetch (default: 1000, max: 1000)
        page: Page number to fetch (default: 1)

    Returns:
        Dict with save statistics including number of books saved

    Raises:
        HTTPException: If credentials not found or API call fails

    Example:
        GET /api/v1/library/audible/fetch?num_results=100
    """
    user_id = get_user_id(current_user)
    logger.info(f"Fetching Audible library for user: {user_id}")

    # Get user's Audible credentials from database
    user = await user_service.get_user_by_id(db, user_id)

    if not user or user.audible_auth_json is None:
        logger.error(f"No Audible credentials found for user {user_id}")
        raise AuthorizationError(
            "Audible credentials not configured. Please authenticate with Audible first."
        )

    auth_data = json.loads(str(user.audible_auth_json))

    # Create Audible client from stored credentials
    logger.info("Creating Audible authenticator from stored credentials")
    auth = audible.Authenticator.from_dict(auth_data)

    # Create async client and fetch library
    logger.info(f"Fetching library from Audible (num_results={num_results}, page={page})")
    async with audible.AsyncClient(auth=auth) as client:
        library_response = await client.get(
            "library",
            num_results=num_results,
            page=page,
            response_groups=("product_desc," "product_attrs," "media," "rating"),
            sort_by="-PurchaseDate",
        )

    items = library_response.get("items", [])
    logger.info(f"Successfully fetched {len(items)} books from Audible for user {user_id}")

    # Save books to database
    books_saved = 0
    books_failed = 0

    for item in items:
        try:
            asin = item.get("asin")
            if not asin:
                logger.warning("Item missing ASIN, skipping")
                books_failed += 1
                continue

            # Extract book metadata from Audible API response
            title = item.get("title", "Unknown Title")
            product_images = item.get("product_images", {})
            cover_art_url = product_images.get("500") if product_images else None

            # Extract runtime in minutes (Audible provides runtime_length_ms)
            runtime_ms = item.get("runtime_length_ms")
            runtime_min = int(runtime_ms / 60000) if runtime_ms else None

            # Extract rating
            rating_obj = item.get("rating", {})
            rating_float = rating_obj.get("overall_distribution", {}).get("average_rating") if rating_obj else None
            rating = Decimal(str(rating_float)) if rating_float is not None else None

            # Extract purchase date
            purchase_date = item.get("purchase_date")

            # Extract authors
            authors = item.get("authors", [])
            author = ", ".join([a.get("name", "") for a in authors]) if authors else None

            # Extract narrators
            narrators = item.get("narrators", [])
            narrator = ", ".join([n.get("name", "") for n in narrators]) if narrators else None

            # Extract description
            description = item.get("description")

            # Extract series information
            series_obj = item.get("series", {})
            series_name = series_obj.get("title") if series_obj else None

            # Extract publisher
            publisher = item.get("publisher_name")

            # Extract publication date
            publication_date = item.get("publication_date_string")

            # Extract language
            language = item.get("language", "en-US")

            # Extract review count
            review_count = rating_obj.get("num_reviews") if rating_obj else 0

            # Save book to database
            success = await book_service.add_book(
                db=db,
                asin=asin,
                user_id=user_id,
                title=title,
                purchase_date=purchase_date,
                runtime_min=runtime_min,
                author=author,
                narrator=narrator,
                series_name=series_name,
                description=description,
                rating=rating,
                publisher=publisher,
                publication_date=publication_date,
                language=language,
                review_count=review_count,
                cover_art_url=cover_art_url,
            )

            if success:
                books_saved += 1
                logger.info(f"Saved book: {title} (ASIN: {asin})")
            else:
                books_failed += 1
                logger.warning(f"Failed to save book: {title} (ASIN: {asin})")

        except Exception as e:
            books_failed += 1
            logger.error(f"Error processing book item: {e}")

    # Commit database changes
    await db.commit()

    logger.info(
        f"Audible library fetch complete for user {user_id}: "
        f"{books_saved} saved, {books_failed} failed"
    )

    return {
        "books_saved": books_saved,
        "books_failed": books_failed,
        "total_fetched": len(items),
        "user_id": user_id,
    }


@router.get(
    "/{asin}",
    response_model=BookResponse,
    summary="Get book details",
    description="Get detailed information about a specific book",
    responses={
        200: {"description": "Book details retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this book"},
        404: {"description": "Book not found"},
    },
)
@handle_route_errors("get book details")
async def get_book_details(
    asin: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BookResponse:
    """
    Get detailed information about a specific audiobook.

    Retrieves book details by ASIN (Amazon Standard Identification Number).
    User can only access their own books.

    Args:
        asin: Amazon Standard Identification Number (10-character code)
        current_user: Current authenticated user (from JWT token)
        db: Database session

    Returns:
        BookResponse: Complete book details with metadata

    Raises:
        ResourceNotFoundError: If book not found
        AuthorizationError: If book belongs to another user

    Example:
        GET /api/v1/library/B084L6Z6M3
    """
    user_id = get_user_id(current_user)
    logger.info(f"Fetching book details: {asin} for user: {user_id}")

    # Get book by ASIN
    book = await book_service.get_book_by_asin(db, asin)

    if not book:
        logger.warning(f"Book not found: {asin}")
        raise ResourceNotFoundError(f"Book '{asin}' not found")

    verify_book_ownership(book, user_id, asin)

    logger.info(f"Retrieved book details: {asin}")
    return BookResponse.from_orm(book)
