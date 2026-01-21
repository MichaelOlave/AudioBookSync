"""Book management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ...database.services import book_service
from ...database.engine import get_db_session
from ...database.models.user import User
from ..security.auth import get_current_user
from ..schemas.book import BookBase, BookResponse
from ..schemas.common import MessageResponse
from ..middleware.error_handler import ResourceNotFoundError

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
    try:
        logger.info(f"Adding book {book_data.asin} for user {current_user.user_id}")

        # Add/update book in database
        success = await book_service.add_book(
            db=db,
            asin=book_data.asin,
            user_id=str(current_user.user_id),
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
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add book",
            )

        # Fetch and return the added book
        book = await book_service.get_book_by_asin(db, book_data.asin)
        if not book:
            logger.error(f"Added book not found: {book_data.asin}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve added book",
            )

        await db.commit()
        logger.info(f"Book added successfully: {book_data.asin} for user {current_user.user_id}")
        return BookResponse.from_orm(book)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding book {book_data.asin}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add book",
        )


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
    try:
        logger.info(f"Deleting book {asin} for user {current_user.user_id}")

        # Verify book exists and belongs to user
        book = await book_service.get_book_by_asin(db, asin)
        if not book:
            logger.warning(f"Book not found: {asin}")
            raise ResourceNotFoundError(f"Book '{asin}' not found")

        # Verify ownership
        if book.user_id != current_user.user_id:
            logger.warning(
                f"Unauthorized delete attempt for book {asin} by user {current_user.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this book",
            )

        # Delete the book
        success = await book_service.delete_book(db, asin)
        if not success:
            logger.error(f"Failed to delete book {asin}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete book",
            )

        await db.commit()
        logger.info(f"Book deleted successfully: {asin}")
        return MessageResponse(
            message=f"Book '{asin}' deleted successfully",
            success=True,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting book {asin}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete book",
        )
