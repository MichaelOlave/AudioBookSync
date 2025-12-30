"""Audiobook file serving and streaming endpoints."""

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import FileResponse
from loguru import logger

from ...database.db_books import book_ops
from ...core.config import Config
from ..security.auth import get_current_user
from ..middleware.error_handler import ResourceNotFoundError

router = APIRouter()


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
async def stream_audiobook(
    asin: str,
    current_user: dict = Depends(get_current_user),
    range_header: Optional[str] = Header(default=None),
):
    """
    Stream an audiobook file with Range request support.

    Streams the decrypted audiobook file with support for HTTP Range requests,
    which allows audio players to seek through the file without downloading
    the entire file.

    Args:
        asin: Amazon Standard Identification Number
        current_user: Current authenticated user (from JWT token)
        range_header: HTTP Range header (e.g., "bytes=0-1023")

    Returns:
        StreamingResponse or FileResponse with audio file

    Raises:
        ResourceNotFoundError: If book or file not found
        AuthorizationError: If book belongs to another user

    Example:
        GET /api/v1/files/audiobook/B084L6Z6M3
        GET /api/v1/files/audiobook/B084L6Z6M3 HTTP/1.1
        Range: bytes=0-1023
    """
    try:
        user_id = current_user.get("user_id")
        logger.info(f"Audio stream requested for {asin} by user {user_id}")

        # Verify book exists and belongs to user
        book = book_ops.get_book_by_asin(asin)
        if not book:
            logger.warning(f"Book not found: {asin}")
            raise ResourceNotFoundError(f"Book '{asin}' not found")

        # Verify ownership
        if book.get("user_id") != user_id:
            logger.warning(
                f"Unauthorized access attempt to audiobook {asin} by user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this book",
            )

        # Get decrypted file path
        decrypted_path = book.get("decrypted_path")
        if not decrypted_path:
            logger.warning(f"Decrypted file path not available for {asin}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Decrypted audiobook file not available",
            )

        # Verify file exists and prevent path traversal
        file_path = Path(decrypted_path).resolve()
        decrypted_dir = Path(Config.DECRYPTED_DIR).resolve()

        # Security: ensure file is within decrypted directory
        if not str(file_path).startswith(str(decrypted_dir)):
            logger.warning(f"Path traversal attempt detected for {asin}: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        if not file_path.exists():
            logger.warning(f"Decrypted file not found: {file_path}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Decrypted audiobook file not found on disk",
            )

        # Get file size
        file_size = file_path.stat().st_size

        # Handle Range requests (HTTP 206 Partial Content)
        if range_header:
            try:
                # Parse Range header: "bytes=start-end"
                range_str = range_header.replace("bytes=", "")

                if "-" not in range_str:
                    raise ValueError("Invalid range format")

                start_str, end_str = range_str.split("-", 1)
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1

                # Validate range
                if start < 0 or end >= file_size or start > end:
                    raise ValueError("Invalid range values")

                content_length = end - start + 1

                logger.info(f"Streaming range {start}-{end}/{file_size} for {asin}")

                # Return partial content with proper headers
                return FileResponse(
                    path=file_path,
                    media_type="audio/mp4",
                    headers={
                        "Content-Range": f"bytes {start}-{end}/{file_size}",
                        "Content-Length": str(content_length),
                        "Accept-Ranges": "bytes",
                    },
                    status_code=206,
                )

            except (ValueError, IndexError) as e:
                logger.warning(f"Invalid range header: {range_header}: {e}")
                # Fall through to return full file
                pass

        # Return full file
        logger.info(f"Streaming full file for {asin} (size: {file_size} bytes)")

        return FileResponse(
            path=file_path,
            media_type="audio/mp4",
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming audiobook {asin}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to stream audiobook",
        )
