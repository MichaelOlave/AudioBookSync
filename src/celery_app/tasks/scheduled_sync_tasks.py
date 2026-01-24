"""Scheduled sync tasks for Celery."""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import UUID

from celery import Task
from loguru import logger

from src.api.services.audible_library_service import fetch_audible_library_to_db
from src.celery_app import celery_app
from src.database.engine import AsyncSessionLocal
from src.database.services import book_service, download_service, sync_schedule_service


@celery_app.task(bind=True, name="execute_scheduled_sync_task")
def execute_scheduled_sync_task(self: Task, schedule_id: str) -> dict:
    """Execute a single scheduled sync."""
    try:
        return asyncio.run(_async_execute_scheduled_sync(schedule_id))
    except Exception as e:
        logger.error(f"Scheduled sync task failed: {e}", exc_info=True)
        return {"success": False, "schedule_id": schedule_id, "error": str(e)}


async def _async_execute_scheduled_sync(schedule_id: str) -> dict:
    try:
        async with AsyncSessionLocal() as db:
            schedule = await sync_schedule_service.get_sync_schedule_by_id(db, UUID(schedule_id))
            if not schedule or not schedule.enabled:
                return {
                    "success": False,
                    "schedule_id": schedule_id,
                    "status": "skipped",
                }

            user_id = str(schedule.user_id)
            action = schedule.action
            result = await fetch_audible_library_to_db(db=db, user_id=user_id)

        downloads_result = {}
        if action == "download":
            downloads_result = await _enqueue_missing_downloads(user_id)

        return {
            "success": True,
            "schedule_id": schedule_id,
            "action": action,
            **result,
            **downloads_result,
        }
    except Exception as e:
        logger.error(f"Scheduled sync execution failed: {e}", exc_info=True)
        return {"success": False, "schedule_id": schedule_id, "error": str(e)}


async def _enqueue_missing_downloads(user_id: str) -> dict:
    download_requests: list[tuple[str, dict]] = []
    skipped = 0

    async with AsyncSessionLocal() as db:
        missing_books = await book_service.get_not_downloaded_books(db, user_id)
        for book in missing_books:
            latest = await download_service.get_latest_download(
                db,
                book.asin,
                user_id=user_id,
            )
            if latest and latest.status in ("pending", "downloading"):
                skipped += 1
                continue

            download_status = await download_service.create_download_status(
                db=db,
                asin=book.asin,
                status="pending",
                user_id=user_id,
            )
            if not download_status:
                continue

            download_requests.append(
                (
                    str(download_status.download_id),
                    {"asin": book.asin, "title": book.title},
                )
            )

        await db.commit()

    if download_requests:
        from src.celery_app.tasks.download_tasks import execute_download_task

        for download_id, book in download_requests:
            execute_download_task.delay(  # type: ignore[attr-defined]
                user_id=user_id,
                download_id=download_id,
                book=book,
            )

    return {
        "downloads_enqueued": len(download_requests),
        "downloads_skipped": skipped,
    }


@celery_app.task(bind=True, name="run_scheduled_syncs")
def run_scheduled_syncs(self: Task) -> dict:
    """Find and enqueue due sync schedules."""
    try:
        return asyncio.run(_async_run_scheduled_syncs())
    except Exception as e:
        logger.error(f"Scheduled sync scan failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def _async_run_scheduled_syncs() -> dict:
    now = datetime.now(timezone.utc)
    schedule_ids: list[str] = []

    async with AsyncSessionLocal() as db:
        schedules = await sync_schedule_service.get_due_sync_schedules(db, now)
        for schedule in schedules:
            next_run_at = now + timedelta(minutes=schedule.interval_minutes)
            updated = await sync_schedule_service.update_schedule_run(
                db=db,
                schedule_id=schedule.schedule_id,
                last_run_at=now,
                next_run_at=next_run_at,
            )
            if updated:
                schedule_ids.append(str(schedule.schedule_id))

        await db.commit()

    for schedule_id in schedule_ids:
        execute_scheduled_sync_task.delay(schedule_id)  # type: ignore[attr-defined]

    return {"success": True, "scheduled": len(schedule_ids)}
