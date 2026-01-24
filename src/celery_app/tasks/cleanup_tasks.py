"""Cleanup tasks for scheduled maintenance."""

import asyncio
from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import and_, delete, select

from src.adapters.storage.minio_storage_adapter import MinIOStorageAdapter
from src.celery_app import celery_app
from src.core.config import Config
from src.database.engine import AsyncSessionLocal
from src.database.models.decryption import DecryptionStatus
from src.database.models.download import DownloadStatus
from src.database.models.error import ErrorLog
from src.database.models.sync import SyncHistory


@celery_app.task(name="cleanup_orphaned_minio_files")
def cleanup_orphaned_minio_files() -> dict:
    """Clean up orphaned files in MinIO that aren't referenced in database."""
    return asyncio.run(_async_cleanup_minio())


async def _async_cleanup_minio() -> dict:
    """Async implementation of MinIO cleanup."""
    try:
        logger.info("Starting MinIO orphaned file cleanup")

        storage_adapter = MinIOStorageAdapter()

        # Get all expected file paths from database
        async with AsyncSessionLocal() as db:
            expected_paths = set()

            # Query download_status for download paths
            result = await db.execute(
                select(DownloadStatus.file_path).where(DownloadStatus.file_path.isnot(None))
            )
            expected_paths.update(row[0] for row in result.fetchall() if row[0])

            # Query decryption_status for decrypted paths
            result = await db.execute(
                select(DecryptionStatus.file_path).where(DecryptionStatus.file_path.isnot(None))
            )
            expected_paths.update(row[0] for row in result.fetchall() if row[0])

            # Query decryption_status for encrypted file fallback paths
            result = await db.execute(
                select(DecryptionStatus.encrypted_file_object_key).where(
                    DecryptionStatus.encrypted_file_object_key.isnot(None)
                )
            )
            expected_paths.update(row[0] for row in result.fetchall() if row[0])

        # List all objects in MinIO
        all_objects = storage_adapter.minio_client.list_all_objects()
        orphaned_files = [obj for obj in all_objects if obj not in expected_paths]

        # Delete orphaned files
        deleted_count = 0
        for file_path in orphaned_files:
            try:
                storage_adapter.minio_client.delete_file(file_path)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete orphaned file {file_path}: {e}")

        logger.info(
            f"MinIO cleanup completed: {deleted_count} orphaned files deleted out of {len(all_objects)} total"
        )
        return {"deleted_count": deleted_count, "total_checked": len(all_objects)}

    except Exception as e:
        logger.error(f"MinIO cleanup failed: {e}", exc_info=True)
        return {"error": str(e)}


@celery_app.task(name="cleanup_old_database_records")
def cleanup_old_database_records() -> dict:
    """Clean up old database records based on retention policies."""
    return asyncio.run(_async_cleanup_database())


async def _async_cleanup_database() -> dict:
    """Async implementation of database cleanup."""
    try:
        logger.info("Starting database cleanup")

        async with AsyncSessionLocal() as db:
            deleted_counts = {}

            # Clean old sync_history records
            sync_cutoff = datetime.now(timezone.utc) - timedelta(
                days=Config.CLEANUP_RETENTION_SYNC_DAYS
            )
            result = await db.execute(
                delete(SyncHistory).where(SyncHistory.sync_completed_at < sync_cutoff)
            )
            await db.flush()
            deleted_counts["sync_history"] = result.rowcount

            # Clean old error_log records (resolved only)
            error_cutoff = datetime.now(timezone.utc) - timedelta(
                days=Config.CLEANUP_RETENTION_ERROR_DAYS
            )
            result = await db.execute(
                delete(ErrorLog).where(
                    and_(ErrorLog.timestamp < error_cutoff, ErrorLog.resolved.is_(True))
                )
            )
            await db.flush()
            deleted_counts["error_log"] = result.rowcount

            # Clean old completed download_status
            status_cutoff = datetime.now(timezone.utc) - timedelta(
                days=Config.CLEANUP_RETENTION_COMPLETED_DAYS
            )
            result = await db.execute(
                delete(DownloadStatus).where(
                    and_(
                        DownloadStatus.status == "completed",
                        DownloadStatus.download_completed_at < status_cutoff,
                    )
                )
            )
            await db.flush()
            deleted_counts["download_status"] = result.rowcount

            # Clean old completed decryption_status
            result = await db.execute(
                delete(DecryptionStatus).where(
                    and_(
                        DecryptionStatus.status == "completed",
                        DecryptionStatus.decryption_completed_at < status_cutoff,
                    )
                )
            )
            await db.flush()
            deleted_counts["decryption_status"] = result.rowcount

            await db.commit()

        logger.info(f"Database cleanup completed: {deleted_counts}")
        return deleted_counts

    except Exception as e:
        logger.error(f"Database cleanup failed: {e}", exc_info=True)
        return {"error": str(e)}
