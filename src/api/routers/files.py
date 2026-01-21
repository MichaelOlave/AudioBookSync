"""Audiobook file serving and streaming endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.engine import get_db_session
from ...database.services import book_service, decryption_service
from ...infrastructure.storage_service import StorageService
from ..middleware.error_handler import (
    AuthenticationError,
    InternalServerError,
    ResourceNotFoundError,
    handle_route_errors,
)
from ..security.auth import get_current_user
from ..utils.auth_utils import get_user_id
from ..utils.generic_handlers import verify_book_ownership

router = APIRouter()


async def _get_object_key_for_asin(
    db: AsyncSession,
    user_id: str,
    asin: str,
) -> Optional[str]:
    """Get MinIO object_key for a specific ASIN from decryption status using ORM.

    Args:
        db: Database session
        user_id: User ID
        asin: Amazon Standard Identification Number

    Returns:
        object_key if found and not None, None otherwise
    """
    try:
        # Get user's decryptions and find matching ASIN using ORM
        decryptions = await decryption_service.get_decryptions_by_user(
            db=db,
            user_id=UUID(user_id),
            limit=100,
        )
        for decryption in decryptions:
            if decryption.asin == asin:
                return decryption.object_key
        return None
    except Exception as e:
        logger.warning(f"Failed to get object_key for {asin}: {e}")
        return None


@router.get(
    "/audiobook/{asin}",
    summary="Stream audiobook file",
    description="Stream decrypted audiobook with Range request support for seeking",
    response_model=None,
    responses={
        200: {
            "description": "Audio stream",
            "content": {"audio/mp4": {}},
        },
        206: {
            "description": "Partial content with Range support",
            "content": {"audio/mp4": {}},
        },
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this book"},
        404: {"description": "Book or file not found"},
    },
)
@handle_route_errors("stream audiobook")
async def stream_audiobook(
    asin: str,
    current_user: dict = Depends(get_current_user),
    range_header: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Stream an audiobook file from MinIO with Range request support.

    Streams the decrypted audiobook file with support for HTTP Range requests,
    which allows audio players to seek through the file without downloading
    the entire file.

    Args:
        asin: Amazon Standard Identification Number
        current_user: Current authenticated user (from JWT token)
        range_header: HTTP Range header (e.g., "bytes=0-1023")
        db: Database session

    Returns:
        StreamingResponse with audio file

    Raises:
        ResourceNotFoundError: If book or file not found
        AuthorizationError: If book belongs to another user

    Example:
        GET /api/v1/files/audiobook/B084L6Z6M3
        GET /api/v1/files/audiobook/B084L6Z6M3 HTTP/1.1
        Range: bytes=0-1023
    """
    user_id = get_user_id(current_user)
    if not user_id:
        logger.error("User ID not found in token")
        raise AuthenticationError("Invalid authentication token")

    logger.info(f"Audio stream requested for {asin} by user {user_id}")

    # Verify book exists and belongs to user using ORM
    book = await book_service.get_book_by_asin(db, asin)
    if not book:
        logger.warning(f"Book not found: {asin}")
        raise ResourceNotFoundError(f"Book '{asin}' not found")

    verify_book_ownership(book, user_id, asin)

    # Get MinIO object_key from decryption status (required) using ORM
    object_key = await _get_object_key_for_asin(db, user_id, asin)
    if not object_key:
        logger.warning(f"MinIO object_key not available for {asin}")
        raise ResourceNotFoundError("Decrypted audiobook file not available")

    # Initialize storage service
    storage_service = StorageService()
    logger.debug(f"Retrieved object_key for {asin}: {object_key}")

    # Parse Range header if present (HTTP 206 Partial Content)
    start = 0
    content_length = None

    if range_header:
        try:
            # Parse Range header: "bytes=start-end"
            range_str = range_header.replace("bytes=", "")

            if "-" not in range_str:
                raise ValueError("Invalid range format")

            start_str, end_str = range_str.split("-", 1)
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else None

            if end is not None:
                content_length = end - start + 1

            logger.info(f"Streaming range {start}-{end} for {asin}")

        except (ValueError, IndexError) as e:
            logger.warning(f"Invalid range header: {range_header}: {e}")
            # Fall through to return full file
            start = 0
            content_length = None

    # Stream from MinIO
    logger.info(
        f"Streaming from MinIO: {asin}, object_key={object_key}, "
        f"offset={start}, length={content_length}"
    )

    data = storage_service.stream_file(
        user_id=user_id,
        object_key=object_key,
        offset=start,
        length=content_length,
    )

    if not data:
        logger.error(f"Failed to stream from MinIO: {asin}")
        raise InternalServerError("Failed to stream audiobook")

    def stream_generator():
        yield data

    # Return with proper headers for Range requests
    headers = {
        "Content-Length": str(len(data)),
        "Accept-Ranges": "bytes",
    }

    status_code = 200
    if content_length is not None:
        headers["Content-Range"] = f"bytes {start}-{start + len(data) - 1}/*"
        status_code = 206

    return StreamingResponse(
        stream_generator(),
        media_type="audio/mp4",
        headers=headers,
        status_code=status_code,
    )
