"""Download tasks for Celery."""

import asyncio
from uuid import UUID

from celery import Task
from loguru import logger

from src.celery_app import celery_app
from src.celery_app.utils.progress import publish_progress
from src.database.engine import AsyncSessionLocal
from src.database.services import download_service, error_service
from src.operations.downloader import download_book


@celery_app.task(bind=True, name="download_task")
def execute_download_task(
    self: Task, user_id: str, download_id: str, book: dict
) -> bool:
    """
    Execute download operation in Celery worker.

    Args:
        self: Celery task instance
        user_id: User ID
        download_id: Download status record ID
        book: Book dictionary with 'asin' and 'title'

    Returns:
        True if download completed successfully, False otherwise
    """
    try:
        return asyncio.run(_async_download(self, user_id, download_id, book))
    except Exception as e:
        logger.error(f"Download task failed: {e}", exc_info=True)
        return False


async def _async_download(
    task: Task, user_id: str, download_id: str, book: dict
) -> bool:
    """
    Async implementation of download task.

    Args:
        task: Celery task instance
        user_id: User ID
        download_id: Download status record ID
        book: Book dictionary with 'asin' and 'title'

    Returns:
        True if successful, False otherwise
    """
    asin = book.get("asin", "")
    title = book.get("title", "")

    try:
        logger.info(f"[Download {download_id}] Starting download for {title} ({asin})")

        # Update status to in_progress
        async with AsyncSessionLocal() as db:
            await download_service.update_download_status(
                db=db,
                download_id=UUID(download_id),
                status="downloading",
            )
            await db.commit()

        # Create progress callback that publishes to Redis
        def progress_callback(event_type: str, **data):
            data["download_id"] = download_id
            publish_progress(user_id=user_id, event_type=event_type, data=data)

        # Execute download
        book_list = [asin, title]
        success = await download_book(
            book_list, user_id=user_id, progress_callback=progress_callback
        )

        if success:
            # Update to completed
            async with AsyncSessionLocal() as db:
                await download_service.complete_download(
                    db=db,
                    download_id=UUID(download_id),
                )
                await db.commit()

            publish_progress(
                user_id=user_id,
                event_type="download.completed",
                data={
                    "download_id": download_id,
                    "asin": asin,
                    "title": title,
                    "status": "completed",
                },
            )
            return True
        else:
            raise Exception("Download operation returned false")

    except Exception as e:
        logger.error(f"[Download {download_id}] Failed: {e}", exc_info=True)

        # Update to failed
        async with AsyncSessionLocal() as db:
            await download_service.fail_download(
                db=db,
                download_id=UUID(download_id),
                error_message=str(e),
            )
            await db.commit()

            # Log error
            await error_service.log_error(
                db=db,
                error_type="download_error",
                error_message=str(e),
                user_id=UUID(user_id),
                asin=asin,
                severity="error",
                error_details={"download_id": download_id},
            )
            await db.commit()

        publish_progress(
            user_id=user_id,
            event_type="download.failed",
            data={
                "download_id": download_id,
                "asin": asin,
                "title": title,
                "error": str(e),
            },
        )
        return False
