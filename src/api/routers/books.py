"""Book management endpoints."""

from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.engine import get_db_session
from ...database.models.user import User
from ...database.services import book_service, metadata_service
from ..middleware.error_handler import (
    AuthorizationError,
    InternalServerError,
    ResourceNotFoundError,
    handle_route_errors,
)
from ..schemas.book import BookBase, BookResponse, ChapterResponse
from ..schemas.common import MessageResponse
from ..security.auth import get_current_user
from ..utils.auth_utils import get_user_id
from ..utils.generic_handlers import verify_book_access

router = APIRouter()


@router.post(
    "/",
    response_model=BookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add book to library",
    description="Add a new book to user's library or update existing book",
    responses={
        201: {"description": "Book added successfully"},
        400: {"description": "Invalid book data"},
        401: {"description": "Not authenticated"},
    },
)
@handle_route_errors("add book")
async def create_book(
    book_data: BookBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BookResponse:
    """
    Add a new book to user's library.

    Adds a book with metadata. If book already exists (by ASIN), updates it.

    Args:
        book_data: Book details (asin, title, author, etc.)
        current_user: Current authenticated user (from JWT token)
        db: Database session

    Returns:
        BookResponse: Added/updated book details

    Raises:
        ValidationError: If required fields are missing

    Example:
        POST /api/v1/books/
        {
            "asin": "B084L6Z6M3",
            "title": "Becoming",
            "author": "Michelle Obama",
            "narrator": "Michelle Obama",
            "runtime_min": 1440,
            "rating": 4.8
        }
    """
    user_id = get_user_id(current_user)
    logger.info(f"Adding book {book_data.asin} for user {user_id}")

    # Add/update book in database
    success = await book_service.add_book(
        db=db,
        asin=book_data.asin,
        user_id=user_id,
        title=book_data.title,
        runtime_min=book_data.runtime_min,
        author=book_data.author,
        narrator=book_data.narrator,
        series_name=book_data.series_name,
        description=book_data.description,
        rating=book_data.rating,
    )

    if not success:
        logger.error(f"Failed to add book {book_data.asin}")
        raise ResourceNotFoundError(f"Failed to add book {book_data.asin}")

    user_book_with_book = await book_service.get_user_book_with_book(
        db,
        user_id,
        book_data.asin,
    )
    if not user_book_with_book:
        logger.error(f"Added book not found: {book_data.asin}")
        raise ResourceNotFoundError(f"Added book not found: {book_data.asin}")
    user_book, book = user_book_with_book

    await db.commit()
    logger.info(f"Book added successfully: {book_data.asin} for user {user_id}")
    return BookResponse(**book_service.build_book_response_data(book, user_book))


@router.delete(
    "/{asin}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete book from library",
    description="Remove a book from user's library",
    responses={
        200: {"description": "Book deleted successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to delete this book"},
        404: {"description": "Book not found"},
    },
)
@handle_route_errors("delete book")
async def delete_book(
    asin: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Delete a book from user's library.

    Removes the book with the specified ASIN. User can only delete their own books.

    Args:
        asin: Amazon Standard Identification Number (10-character code)
        current_user: Current authenticated user (from JWT token)
        db: Database session

    Returns:
        MessageResponse: Confirmation of deletion

    Raises:
        ResourceNotFoundError: If book not found
        AuthorizationError: If book belongs to another user

    Example:
        DELETE /api/v1/books/B084L6Z6M3
    """
    user_id = get_user_id(current_user)
    logger.info(f"Deleting book {asin} for user {user_id}")

    # Verify book exists and belongs to user
    book = await book_service.get_book_by_asin(db, asin)
    if not book:
        logger.warning(f"Book not found: {asin}")
        raise ResourceNotFoundError(f"Book '{asin}' not found")

    user_book = await book_service.get_user_book(db, user_id, asin)
    if not user_book:
        logger.warning(f"Unauthorized delete attempt for book {asin} by user {user_id}")
        raise AuthorizationError("Not authorized to delete this book")

    # Delete the book
    success = await book_service.delete_book(db, asin, user_id)
    if not success:
        logger.error(f"Failed to delete book {asin}")
        raise InternalServerError(f"Failed to delete book {asin}")

    await db.commit()
    logger.info(f"Book deleted successfully: {asin}")
    return MessageResponse(
        message=f"Book '{asin}' deleted successfully",
        success=True,
    )


@router.get(
    "/{asin}/chapters",
    response_model=list[ChapterResponse],
    summary="Get chapter metadata for a book",
    description="Get chapter metadata for a book owned by the current user or shared by family",
    responses={
        200: {"description": "Chapters retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this book"},
        404: {"description": "Book not found"},
    },
)
@handle_route_errors("get chapters")
async def get_book_chapters(
    asin: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[ChapterResponse]:
    """Get chapter metadata for a book."""
    user_id = get_user_id(current_user)
    logger.info(f"Fetching chapters for book {asin} (user {user_id})")

    book = await book_service.get_book_by_asin(db, asin)
    if not book:
        logger.warning(f"Book not found for chapters: {asin}")
        raise ResourceNotFoundError(f"Book '{asin}' not found")
    await verify_book_access(db, asin, current_user)

    chapters = await metadata_service.get_chapters_by_asin(db, asin)
    return chapters
