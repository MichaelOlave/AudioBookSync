"""Celery configuration for AudioBookSync."""

from celery.schedules import crontab

from src.core.config import Config


class CeleryConfig:
    """Celery configuration class."""

    # Broker and backend settings
    broker_url = Config.CELERY_BROKER_URL
    result_backend = Config.CELERY_RESULT_BACKEND

    # Serialization settings
    task_serializer = "json"
    result_serializer = "json"
    accept_content = ["json"]
    timezone = "UTC"
    enable_utc = True

    # Task execution settings
    task_acks_late = True
    task_reject_on_worker_lost = True
    task_time_limit = Config.CELERY_TASK_TIME_LIMIT  # 2 hours
    task_soft_time_limit = Config.CELERY_TASK_TIME_LIMIT - 600  # 10 min before hard limit
    worker_prefetch_multiplier = 1  # One task at a time (long-running tasks)

    # Result backend settings
    result_expires = 86400  # 24 hours
    task_track_started = True

    # Beat schedule for periodic tasks
    beat_schedule = {
        "cleanup-orphaned-minio-files": {
            "task": "src.celery_app.tasks.cleanup_tasks.cleanup_orphaned_minio_files",
            "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
        },
        "retry-failed-downloads": {
            "task": "src.celery_app.tasks.retry_tasks.retry_failed_downloads",
            "schedule": crontab(hour="*/6", minute=0),  # Every 6 hours
        },
        "retry-failed-decrypts": {
            "task": "src.celery_app.tasks.retry_tasks.retry_failed_decrypts",
            "schedule": crontab(hour="*/6", minute=0),  # Every 6 hours
        },
        "cleanup-old-database-records": {
            "task": "src.celery_app.tasks.cleanup_tasks.cleanup_old_database_records",
            "schedule": crontab(hour=3, minute=0, day_of_week=0),  # Weekly Sunday 3 AM
        },
    }
