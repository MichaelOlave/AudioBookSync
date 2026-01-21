"""User library endpoints."""

import audible
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from typing import Dict, Any

from ...database.services import book_service, user_service
from ...database.engine import get_db_session
from ...database.models.user import User
from ..security.auth import get_current_user
from ..schemas.book import BookResponse, BookList
from ..middleware.error_handler import ResourceNotFoundError

router = APIRouter()


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
async def get_library(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    page: int = Query(
        default=1,
        ge=1,
        description="Page number (starting from 1)",
    ),
    page_size: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Number of items per page (1-100)",
    ),
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
    try:
        logger.info(
            f"Fetching library for user: {current_user.user_id} (page {page}, size {page_size})"
        )

        # Get all books for user
        all_books = await book_service.get_books_by_user(db, str(current_user.user_id))

        # Calculate pagination
        total = len(all_books)
        pages = (total + page_size - 1) // page_size if total > 0 else 0

        # Validate page number
        if page > pages and total > 0:
            logger.warning(f"Page {page} exceeds max pages {pages} for user {current_user.user_id}")
            page = pages

        # Apply pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_books = all_books[start_idx:end_idx]

        # Convert to BookResponse objects
        items = [BookResponse.from_orm(book) for book in paginated_books]

        logger.info(
            f"Retrieved {len(items)} books for user {current_user.user_id} (page {page}/{pages})"
        )

        return BookList(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    except Exception as e:
        logger.error(
            f"Error fetching library for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve library",
        )


@router.get(
    "/audible/fetch",
    summary="Fetch library from Audible",
    description="Fetch user's audiobook library directly from Audible API",
    responses={
        200: {"description": "Library fetched successfully from Audible"},
        401: {"description": "Not authenticated"},
        403: {"description": "Audible credentials not configured"},
        500: {"description": "Failed to fetch from Audible"},
    },
)
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
        default=0,
        ge=0,
        description="Page number to fetch (starting from 0)",
    ),
) -> Dict[str, Any]:
    """
    Fetch user's audiobook library directly from Audible API.

    Uses stored Audible credentials to retrieve the complete library
    from Audible's servers.

    Args:
        current_user: Current authenticated user (from JWT token)
        db: Database session
        num_results: Number of books to fetch (default: 1000, max: 1000)

    Returns:
        Dict with library items and metadata

    Raises:
        HTTPException: If credentials not found or API call fails

    Example:
        GET /api/v1/library/audible/fetch?num_results=100
    """
    try:
        logger.info(f"Fetching Audible library for user: {current_user.user_id}")

        # Get user's Audible credentials from database
        user = await user_service.get_user_by_id(db, str(current_user.user_id))

        if not user or not user.audible_auth_json:
            logger.error(f"No Audible credentials found for user {current_user.user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Audible credentials not configured. Please authenticate with Audible first.",
            )

        auth_data = json.loads(user.audible_auth_json)

        # Create Audible client from stored credentials
        logger.info("Creating Audible authenticator from stored credentials")
        auth = audible.Authenticator.from_dict(auth_data)

        # Create async client and fetch library
        logger.info(f"Fetching library from Audible (num_results={num_results})")
        async with audible.AsyncClient(auth=auth) as client:
            library_response = await client.get(
                "library",
                num_results=num_results,
                page=page,
                response_groups=(
                    "product_desc,"
                    "product_attrs,"
                    "media,"
                    "rating"
                ),
                sort_by="-PurchaseDate",
            )

        items = library_response.get("items", [])
        logger.info(
            f"Successfully fetched {len(items)} books from Audible for user {current_user.user_id}"
        )

        return {
            "items": items,
            "total": len(items),
            "user_id": str(current_user.user_id),
            "num_results": num_results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            f"Error fetching Audible library for user {current_user.user_id}: {e}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch library from Audible: {str(e)}",
        )


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
    try:
        logger.info(f"Fetching book details: {asin} for user: {current_user.user_id}")

        # Get book by ASIN
        book = await book_service.get_book_by_asin(db, asin)

        if not book:
            logger.warning(f"Book not found: {asin}")
            raise ResourceNotFoundError(f"Book '{asin}' not found")

        # Verify ownership
        if book.user_id != current_user.user_id:
            logger.warning(
                f"Unauthorized access attempt to book {asin} by user {current_user.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this book",
            )

        logger.info(f"Retrieved book details: {asin}")
        return BookResponse.from_orm(book)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching book {asin}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve book details",
        )
