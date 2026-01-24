"""Celery task modules."""

# Import all tasks to ensure they're registered with Celery
from src.celery_app.tasks.cleanup_tasks import (
    cleanup_old_database_records,
    cleanup_orphaned_minio_files,
)
from src.celery_app.tasks.decrypt_tasks import execute_decrypt_task
from src.celery_app.tasks.download_tasks import execute_download_task
from src.celery_app.tasks.library_tasks import execute_sync_library_task
from src.celery_app.tasks.retry_tasks import (
    retry_failed_decrypts,
    retry_failed_downloads,
)
from src.celery_app.tasks.scheduled_sync_tasks import (
    execute_scheduled_sync_task,
    run_scheduled_syncs,
)

__all__ = [
    "execute_download_task",
    "execute_decrypt_task",
    "execute_sync_library_task",
    "execute_scheduled_sync_task",
    "run_scheduled_syncs",
    "cleanup_orphaned_minio_files",
    "cleanup_old_database_records",
    "retry_failed_downloads",
    "retry_failed_decrypts",
]
