"""Download tasks for Celery."""

import asyncio
from uuid import UUID

from celery import Task
from loguru import logger

from src.celery_app import celery_app
from src.celery_app.utils.progress import publish_progress
from src.database.engine import AsyncSessionLocal
from src.database.services import book_service, download_service, error_service, user_service
from src.infrastructure.file_utils import normalize_filename
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
                entity_id=UUID(download_id),
                status="downloading",
            )
            await db.commit()

        # Create progress callback that publishes to Redis
        async def progress_callback(event_type: str, **data):
            data["download_id"] = download_id
            publish_progress(user_id=user_id, event_type=event_type, data=data)

        # Fetch Audible auth from database
        async with AsyncSessionLocal() as db:
            audible_auth = await user_service.get_audible_auth_json(
                db,
                user_id,
                redact_secrets=False,
            )
            user = await user_service.get_user_by_id(db, user_id)
            activation_bytes = user.activation_bytes if user else None

        if not audible_auth:
            raise Exception("Audible credentials not configured for user")
        if not activation_bytes:
            raise Exception("Activation bytes not configured for user")

        # Execute download
        book_list = [asin, title]
        success = await download_book(
            book_list,
            user_id=user_id,
            progress_callback=progress_callback,
            audible_auth=audible_auth,
            activation_bytes=activation_bytes,
        )

        if success:
            # Update to completed
            async with AsyncSessionLocal() as db:
                await download_service.complete_download(
                    db=db,
                    entity_id=UUID(download_id),
                )

                normalized_title = normalize_filename(title)
                if normalized_title:
                    object_key = f"decrypted/{normalized_title}.m4b"
                    await book_service.update_book_decryption_status(
                        db=db,
                        asin=asin,
                        is_decrypted=True,
                        decrypted_path=object_key,
                    )
                await book_service.update_book_download_status(
                    db=db,
                    asin=asin,
                    is_downloaded=True,
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
                entity_id=UUID(download_id),
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
