"""Celery application initialization for AudioBookSync."""

from celery import Celery

from src.core.config import Config

# Create Celery app instance
celery_app = Celery(
    "audiobooksync",
    broker=Config.CELERY_BROKER_URL,
    backend=Config.CELERY_RESULT_BACKEND,
)

# Load Celery configuration
celery_app.config_from_object("src.celery_app.config:CeleryConfig")

# Auto-discover tasks from task modules
celery_app.autodiscover_tasks(
    [
        "src.celery_app.tasks.download_tasks",
        "src.celery_app.tasks.decrypt_tasks",
        "src.celery_app.tasks.library_tasks",
        "src.celery_app.tasks.cleanup_tasks",
        "src.celery_app.tasks.retry_tasks",
    ]
)
