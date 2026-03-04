"""Decrypt tasks for Celery."""

import asyncio
from uuid import UUID

from celery import Task
from loguru import logger

from src.celery_app import celery_app
from src.celery_app.utils.progress import publish_progress
from src.database.engine import AsyncSessionLocal
from src.database.services import book_service, decryption_service, error_service, user_service
from src.infrastructure.file_utils import normalize_filename
from src.operations.decryptor import decrypt_book


@celery_app.task(bind=True, name="decrypt_task")
def execute_decrypt_task(self: Task, user_id: str, decryption_id: str, book: dict) -> bool:
    """Execute decrypt operation in Celery worker.

    Args:
        self: Celery task instance
        user_id: User ID
        decryption_id: Decryption status record ID
        book: Book dictionary with 'asin' and 'title'

    Returns:
        True if decryption completed successfully, False otherwise
    """
    try:
        return asyncio.run(_async_decrypt(self, user_id, decryption_id, book))
    except Exception as e:
        logger.error(f"Decrypt task failed: {e}", exc_info=True)
        return False


async def _async_decrypt(task: Task, user_id: str, decryption_id: str, book: dict) -> bool:
    """Async implementation of decrypt task.

    Args:
        task: Celery task instance
        user_id: User ID
        decryption_id: Decryption status record ID
        book: Book dictionary with 'asin' and 'title'

    Returns:
        True if successful, False otherwise
    """
    asin = book.get("asin", "")
    title = book.get("title", "")

    try:
        logger.info(f"[Decrypt {decryption_id}] Starting decryption for {title} ({asin})")

        # Update status to in_progress
        async with AsyncSessionLocal() as db:
            await decryption_service.update_decryption_status(
                db=db,
                entity_id=UUID(decryption_id),
                status="decrypting",
            )
            await db.commit()

        # Create progress callback that publishes to Redis
        async def progress_callback(event_type: str, **data):
            data["decryption_id"] = decryption_id
            publish_progress(user_id=user_id, event_type=event_type, data=data)

        async with AsyncSessionLocal() as db:
            user = await user_service.get_user_by_id(db, user_id)
            activation_bytes = user.activation_bytes if user else None

        if not activation_bytes:
            raise Exception("Activation bytes not configured for user")

        # Execute decrypt
        book_list = [asin, title]
        success = await decrypt_book(
            book_list,
            user_id=user_id,
            progress_callback=progress_callback,
            activation_bytes=activation_bytes,
        )

        if success:
            # Update to completed
            async with AsyncSessionLocal() as db:
                await decryption_service.complete_decryption(
                    db=db,
                    entity_id=UUID(decryption_id),
                )
                normalized_title = normalize_filename(title)
                if normalized_title:
                    object_key = f"decrypted/{normalized_title}.m4b"
                    await book_service.update_book_decryption_status(
                        db=db,
                        asin=asin,
                        is_decrypted=True,
                        user_id=user_id,
                        decrypted_path=object_key,
                    )
                await book_service.update_book_download_status(
                    db=db,
                    asin=asin,
                    is_downloaded=True,
                    user_id=user_id,
                )
                await db.commit()

            publish_progress(
                user_id=user_id,
                event_type="decrypt.completed",
                data={
                    "decryption_id": decryption_id,
                    "asin": asin,
                    "title": title,
                    "status": "completed",
                },
            )
            return True
        else:
            raise Exception("Decrypt operation returned false")

    except Exception as e:
        logger.error(f"[Decrypt {decryption_id}] Failed: {e}", exc_info=True)

        # Update to failed
        async with AsyncSessionLocal() as db:
            await decryption_service.fail_decryption(
                db=db,
                entity_id=UUID(decryption_id),
                error_message=str(e),
            )
            await db.commit()

            # Log error
            await error_service.log_error(
                db=db,
                error_type="decryption_error",
                error_message=str(e),
                user_id=UUID(user_id),
                asin=asin,
                severity="error",
                error_details={"decryption_id": decryption_id},
            )
            await db.commit()

        publish_progress(
            user_id=user_id,
            event_type="decrypt.failed",
            data={
                "decryption_id": decryption_id,
                "asin": asin,
                "title": title,
                "error": str(e),
            },
        )
        return False
