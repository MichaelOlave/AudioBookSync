"""Tests for Celery task structure and configuration."""

from unittest.mock import MagicMock, patch

from src.celery_app import celery_app
from src.celery_app.config import CeleryConfig


class TestCeleryConfiguration:
    """Tests for Celery configuration."""

    def test_celery_app_created(self):
        """Test that Celery app is properly initialized."""
        assert celery_app is not None
        assert celery_app.main == "audiobooksync"

    def test_celery_config_loaded(self):
        """Test that Celery configuration is loaded."""
        config = CeleryConfig()
        assert config.task_serializer == "json"
        assert config.result_serializer == "json"
        assert config.timezone == "UTC"
        assert config.enable_utc is True

    def test_celery_tasks_registered(self):
        """Test that all required tasks are registered."""
        task_names = [
            "src.celery_app.tasks.download_tasks.execute_download_task",
            "src.celery_app.tasks.decrypt_tasks.execute_decrypt_task",
            "src.celery_app.tasks.library_tasks.execute_sync_library_task",
            "cleanup_orphaned_minio_files",
            "cleanup_old_database_records",
            "retry_failed_downloads",
            "retry_failed_decrypts",
        ]

        registered_tasks = list(celery_app.tasks.keys())
        assert registered_tasks
        for task_name in task_names:
            # Check if task is in registered tasks (may have different name format)
            assert any(task_name in t or t in task_name for t in registered_tasks)


class TestBeatSchedule:
    """Tests for Celery Beat schedule configuration."""

    def test_beat_schedule_configured(self):
        """Test that Beat schedule is properly configured."""
        config = CeleryConfig()
        assert hasattr(config, "beat_schedule")
        assert config.beat_schedule is not None

    def test_beat_schedule_has_cleanup_tasks(self):
        """Test that cleanup tasks are scheduled."""
        config = CeleryConfig()
        schedule = config.beat_schedule
        assert "cleanup-orphaned-minio-files" in schedule
        assert "cleanup-old-database-records" in schedule

    def test_beat_schedule_has_retry_tasks(self):
        """Test that retry tasks are scheduled."""
        config = CeleryConfig()
        schedule = config.beat_schedule
        assert "retry-failed-downloads" in schedule
        assert "retry-failed-decrypts" in schedule


class TestProgressPublisher:
    """Tests for Redis progress publisher."""

    @patch("src.celery_app.utils.progress.redis_client")
    def test_publish_progress(self, mock_redis):
        """Test that progress is published to Redis."""
        from src.celery_app.utils.progress import publish_progress

        mock_redis.publish = MagicMock(return_value=1)

        publish_progress(
            user_id="user123",
            event_type="download.progress",
            data={"progress": 50},
        )

        # Verify Redis publish was called
        assert mock_redis.publish.called
        call_args = mock_redis.publish.call_args
        assert "ws:user:user123" in call_args[0]

    @patch("src.celery_app.utils.progress.redis_client")
    def test_publish_progress_adds_timestamp(self, mock_redis):
        """Test that timestamp is added if not present."""
        from src.celery_app.utils.progress import publish_progress

        mock_redis.publish = MagicMock(return_value=1)

        data = {"progress": 50}
        publish_progress(user_id="user123", event_type="download.progress", data=data)

        # Verify timestamp was added
        assert "timestamp" in data


class TestTaskStructure:
    """Tests for Celery task structure."""

    def test_download_task_imports(self):
        """Test that download tasks can be imported."""
        from src.celery_app.tasks.download_tasks import execute_download_task

        assert execute_download_task is not None

    def test_decrypt_task_imports(self):
        """Test that decrypt tasks can be imported."""
        from src.celery_app.tasks.decrypt_tasks import execute_decrypt_task

        assert execute_decrypt_task is not None

    def test_library_task_imports(self):
        """Test that library tasks can be imported."""
        from src.celery_app.tasks.library_tasks import execute_sync_library_task

        assert execute_sync_library_task is not None

    def test_cleanup_task_imports(self):
        """Test that cleanup tasks can be imported."""
        from src.celery_app.tasks.cleanup_tasks import (
            cleanup_old_database_records,
            cleanup_orphaned_minio_files,
        )

        assert cleanup_orphaned_minio_files is not None
        assert cleanup_old_database_records is not None

    def test_retry_task_imports(self):
        """Test that retry tasks can be imported."""
        from src.celery_app.tasks.retry_tasks import retry_failed_decrypts, retry_failed_downloads

        assert retry_failed_downloads is not None
        assert retry_failed_decrypts is not None
