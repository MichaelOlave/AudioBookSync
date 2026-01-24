"""Library sync tasks for Celery."""

import asyncio
from uuid import UUID

from celery import Task
from loguru import logger

from src.celery_app import celery_app
from src.celery_app.utils.progress import publish_progress
from src.database.engine import AsyncSessionLocal
from src.database.services import error_service, sync_service
from src.operations.library_sync import sync_library


@celery_app.task(bind=True, name="sync_library_task")
def execute_sync_library_task(self: Task, user_id: str, sync_type: str = "full") -> bool:
    """
    Execute library sync operation in Celery worker.

    Args:
        self: Celery task instance
        user_id: User ID
        sync_type: Type of sync (full, incremental, manual)

    Returns:
        True if sync completed successfully, False otherwise
    """
    try:
        return asyncio.run(_async_sync_library(self, user_id, sync_type))
    except Exception as e:
        logger.error(f"Sync library task failed: {e}", exc_info=True)
        return False


async def _async_sync_library(task: Task, user_id: str, sync_type: str) -> bool:
    """
    Async implementation of library sync task.

    Args:
        task: Celery task instance
        user_id: User ID
        sync_type: Type of sync

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"[Sync {sync_type}] Starting library sync for user {user_id}")

        # Create sync history record
        async with AsyncSessionLocal() as db:
            sync_record = await sync_service.create_sync_history(
                db=db, user_id=UUID(user_id), sync_type=sync_type
            )
            await db.commit()

        if not sync_record:
            raise Exception("Failed to create sync history record")

        sync_id = str(sync_record.sync_id)

        # Create progress callback that publishes to Redis
        async def progress_callback(event_type: str, **data):
            data["sync_id"] = sync_id
            publish_progress(user_id=user_id, event_type=event_type, data=data)

        # Execute library sync
        await sync_library(
            user_id=user_id,
            ws_broadcast_fn=progress_callback,
        )

        # Publish completion event
        publish_progress(
            user_id=user_id,
            event_type="sync.completed",
            data={
                "sync_id": sync_id,
                "sync_type": sync_type,
                "status": "completed",
            },
        )

        logger.info(f"[Sync {sync_id}] Library sync completed successfully")
        return True

    except Exception as e:
        logger.error(f"[Sync] Library sync failed: {e}", exc_info=True)

        # Log error
        async with AsyncSessionLocal() as db:
            await error_service.log_error(
                db=db,
                error_type="sync_error",
                error_message=str(e),
                user_id=UUID(user_id),
                severity="error",
                error_details={"sync_type": sync_type},
            )
            await db.commit()

        # Publish failure event
        publish_progress(
            user_id=user_id,
            event_type="sync.failed",
            data={
                "sync_type": sync_type,
                "error": str(e),
            },
        )
        return False
