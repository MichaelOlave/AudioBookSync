"""Reading progress endpoints."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.engine import get_db_session
from ...database.services import book_service, metadata_service
from ..middleware.error_handler import (
    AuthenticationError,
    InternalServerError,
    ResourceNotFoundError,
    ValidationError,
    handle_route_errors,
)
from ..schemas.progress import ReadingProgressResponse, ReadingProgressUpdate
from ..security.auth import get_current_user
from ..utils.auth_utils import get_user_id
from ..utils.generic_handlers import verify_book_ownership

router = APIRouter()


def _has_update_fields(payload: ReadingProgressUpdate) -> bool:
    return any(
        value is not None
        for value in (
            payload.percent_complete,
            payload.position_ms,
            payload.is_finished,
        )
    )


async def _get_book_or_404(db: AsyncSession, user_id: str, asin: str):
    book = await book_service.get_book_by_asin(db, asin)
    if not book:
        logger.warning(f"Book not found: {asin}")
        raise ResourceNotFoundError(f"Book '{asin}' not found")

    verify_book_ownership(book, user_id, asin)
    return book


@router.get(
    "/{asin}",
    response_model=ReadingProgressResponse,
    summary="Get reading progress",
    description="Get reading progress for a specific book",
    responses={
        200: {"description": "Reading progress retrieved successfully"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this book"},
        404: {"description": "Book not found"},
    },
)
@handle_route_errors("get reading progress")
async def get_reading_progress(
    asin: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReadingProgressResponse:
    """Get reading progress for a book."""
    user_id = get_user_id(current_user)
    if not user_id:
        logger.error("User ID not found in token")
        raise AuthenticationError("Invalid authentication token")

    await _get_book_or_404(db, user_id, asin)

    progress = await metadata_service.get_reading_progress(db, asin, UUID(user_id))
    if not progress:
        progress = await metadata_service.create_reading_progress(
            db=db,
            asin=asin,
            user_id=UUID(user_id),
            percent_complete=0,
            position_ms=0,
            is_finished=False,
        )
        if not progress:
            raise InternalServerError("Failed to initialize reading progress")
        await db.commit()

    return ReadingProgressResponse.from_orm(progress)


@router.patch(
    "/{asin}",
    response_model=ReadingProgressResponse,
    summary="Update reading progress",
    description="Update reading progress for a specific book",
    responses={
        200: {"description": "Reading progress updated successfully"},
        400: {"description": "Invalid progress data"},
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this book"},
        404: {"description": "Book not found"},
    },
)
@handle_route_errors("update reading progress")
async def update_reading_progress(
    asin: str,
    payload: ReadingProgressUpdate = Body(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> ReadingProgressResponse:
    """Update reading progress for a book."""
    if not _has_update_fields(payload):
        raise ValidationError("Provide at least one progress field to update")

    user_id = get_user_id(current_user)
    if not user_id:
        logger.error("User ID not found in token")
        raise AuthenticationError("Invalid authentication token")

    await _get_book_or_404(db, user_id, asin)

    progress = await metadata_service.get_reading_progress(db, asin, UUID(user_id))
    if progress:
        updated = await metadata_service.update_reading_progress(
            db=db,
            asin=asin,
            user_id=UUID(user_id),
            percent_complete=payload.percent_complete,
            position_ms=payload.position_ms,
            is_finished=payload.is_finished,
        )
        if not updated:
            raise InternalServerError("Failed to update reading progress")
    else:
        progress = await metadata_service.create_reading_progress(
            db=db,
            asin=asin,
            user_id=UUID(user_id),
            percent_complete=payload.percent_complete or 0,
            position_ms=payload.position_ms or 0,
            is_finished=payload.is_finished,
        )
        if not progress:
            raise InternalServerError("Failed to create reading progress")

    progress = await metadata_service.get_reading_progress(db, asin, UUID(user_id))
    if not progress:
        raise InternalServerError("Failed to load reading progress")

    if progress.date_started is None and (payload.position_ms or 0) > 0:
        progress.date_started = datetime.now(timezone.utc)
        await db.flush()

    await db.commit()
    return ReadingProgressResponse.from_orm(progress)
