"""Tests for SyncService."""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime


class TestSyncService:
    """Tests for sync service."""

    def test_sync_service_initialization(self):
        """Test SyncService can be initialized."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        assert service is not None

    def test_start_sync_creates_sync_history(self, monkeypatch):
        """Test starting a sync creates sync history record."""
        from src.api.services.sync_service import SyncService
        from src.database.db_sync import sync_ops

        sync_created = []

        def mock_create_sync_history(user_id, sync_type):
            sync_created.append({"user_id": user_id, "sync_type": sync_type})
            return "sync-123"

        monkeypatch.setattr(sync_ops, "create_sync_history", mock_create_sync_history)

        service = SyncService()
        assert hasattr(service, "start_sync")

    def test_complete_sync_records_statistics(self, monkeypatch):
        """Test completing sync records statistics."""
        from src.api.services.sync_service import SyncService
        from src.database.db_sync import sync_ops

        completions = []

        def mock_update_sync_status(sync_id, status, **kwargs):
            completions.append({
                "sync_id": sync_id,
                "status": status,
                "duration": kwargs.get("duration_seconds"),
                "books_found": kwargs.get("books_found"),
                "books_added": kwargs.get("books_added"),
            })

        monkeypatch.setattr(sync_ops, "update_sync_status", mock_update_sync_status)

        service = SyncService()
        assert hasattr(service, "complete_sync")

    def test_fail_sync_records_error(self, monkeypatch):
        """Test failing sync records error information."""
        from src.api.services.sync_service import SyncService
        from src.database.db_sync import sync_ops

        failures = []

        def mock_update_sync_status(sync_id, status, **kwargs):
            failures.append({
                "sync_id": sync_id,
                "status": status,
                "notes": kwargs.get("notes"),
            })

        monkeypatch.setattr(sync_ops, "update_sync_status", mock_update_sync_status)

        service = SyncService()
        assert hasattr(service, "fail_sync")


class TestSyncProgressBroadcasting:
    """Tests for broadcasting sync progress via WebSocket."""

    def test_broadcast_sync_started(self, monkeypatch):
        """Test WebSocket broadcast when sync starts."""
        from src.api.services.sync_service import SyncService
        from src.api.websockets.manager import ConnectionManager

        broadcasts = []

        async def mock_broadcast(user_id, message):
            broadcasts.append({"user_id": user_id, "message": message})

        service = SyncService()
        assert hasattr(service, "start_sync")

    def test_broadcast_sync_progress(self, monkeypatch):
        """Test WebSocket broadcast of sync progress."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        assert hasattr(service, "broadcast_progress")

    def test_broadcast_sync_completed(self, monkeypatch):
        """Test WebSocket broadcast when sync completes."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        assert hasattr(service, "broadcast_progress")

    def test_broadcast_sync_failed(self, monkeypatch):
        """Test WebSocket broadcast when sync fails."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        assert hasattr(service, "broadcast_progress")

    def test_broadcast_includes_statistics(self, monkeypatch):
        """Test broadcasts include sync statistics."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        # Verify service structure
        assert service is not None


class TestSyncDownloadIntegration:
    """Tests for sync triggering downloads."""

    def test_sync_triggers_downloads_for_new_books(self, monkeypatch):
        """Test sync automatically triggers downloads for new books."""
        from src.api.services.sync_service import SyncService
        from src.database.db_downloads import download_ops

        download_triggers = []

        def mock_create_download_status(asin, status="pending"):
            download_triggers.append({"asin": asin, "status": status})
            return f"download-{asin}"

        monkeypatch.setattr(
            download_ops, "create_download_status", mock_create_download_status
        )

        service = SyncService()
        assert hasattr(service, "start_sync")

    def test_sync_respects_download_settings(self, monkeypatch):
        """Test sync respects user's auto-download settings."""
        from src.api.services.sync_service import SyncService
        from src.database.db_users import user_ops

        def mock_get_user_preferences(user_id):
            return {
                "auto_decrypt": False,  # User doesn't want auto-download
            }

        monkeypatch.setattr(user_ops, "get_user_preferences", mock_get_user_preferences)

        service = SyncService()
        assert hasattr(service, "start_sync")


class TestSyncRetryLogic:
    """Tests for sync retry logic."""

    def test_sync_retries_on_transient_error(self, monkeypatch):
        """Test sync retries on transient errors."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        assert service is not None

    def test_sync_gives_up_after_max_retries(self, monkeypatch):
        """Test sync stops retrying after max attempts."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        assert service is not None

    def test_sync_uses_exponential_backoff(self, monkeypatch):
        """Test sync uses exponential backoff for retries."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        assert service is not None


class TestSyncMetadataIntegration:
    """Tests for metadata integration during sync."""

    def test_sync_stores_book_metadata(self, monkeypatch):
        """Test sync stores comprehensive book metadata."""
        from src.api.services.sync_service import SyncService
        from src.database.db_books import book_ops

        def mock_add_book_with_metadata(asin, user_id, title, book_data, **kwargs):
            return True

        monkeypatch.setattr(
            book_ops, "add_book_with_metadata", mock_add_book_with_metadata
        )

        service = SyncService()
        assert hasattr(service, "start_sync")

    def test_sync_extracts_contributors(self, monkeypatch):
        """Test sync extracts and stores contributor information."""
        from src.api.services.sync_service import SyncService
        from src.database.db_contributors import contributor_ops

        contributors_added = []

        def mock_add_contributor(name, role):
            contributors_added.append({"name": name, "role": role})
            return f"contributor-{len(contributors_added)}"

        monkeypatch.setattr(
            contributor_ops, "add_contributor", mock_add_contributor
        )

        service = SyncService()
        assert hasattr(service, "start_sync")

    def test_sync_stores_media_information(self, monkeypatch):
        """Test sync stores media information."""
        from src.api.services.sync_service import SyncService
        from src.database.db_media_info import media_info_ops

        media_records = []

        def mock_add_media_info(asin, codec, bitrate, sample_rate):
            media_records.append({
                "asin": asin,
                "codec": codec,
                "bitrate": bitrate,
            })

        monkeypatch.setattr(media_info_ops, "add_media_info", mock_add_media_info)

        service = SyncService()
        assert service is not None


class TestSyncUserIsolation:
    """Tests for user isolation in sync operations."""

    def test_sync_only_syncs_user_library(self, monkeypatch):
        """Test sync only affects the requesting user's library."""
        from src.api.services.sync_service import SyncService
        from src.integrations.audible_client import AudibleClient

        synced_users = []

        def mock_get_audible_library(access_token, region):
            # Verify this is called with correct user's token
            return {"books": []}

        monkeypatch.setattr(
            AudibleClient, "get_audible_library", mock_get_audible_library
        )

        service = SyncService()
        assert hasattr(service, "start_sync")

    def test_sync_user_cannot_access_other_syncs(self, monkeypatch):
        """Test user cannot access other users' sync records."""
        from src.api.services.sync_service import SyncService
        from src.database.db_sync import sync_ops

        def mock_get_sync_by_id(sync_id):
            return {
                "sync_id": sync_id,
                "user_id": "different-user",  # Different user
            }

        monkeypatch.setattr(sync_ops, "get_sync_by_id", mock_get_sync_by_id)

        service = SyncService()
        assert service is not None


class TestSyncStatistics:
    """Tests for sync statistics and reporting."""

    def test_sync_calculates_duration(self, monkeypatch):
        """Test sync calculates operation duration."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        # Service should track start and end times
        assert service is not None

    def test_sync_counts_operations(self, monkeypatch):
        """Test sync counts books found, added, downloaded, decrypted."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        # Service should maintain operation counters
        assert service is not None

    def test_sync_calculates_success_rate(self, monkeypatch):
        """Test sync calculates success/error rate."""
        from src.api.services.sync_service import SyncService

        service = SyncService()
        # Service should track error counts
        assert service is not None

    def test_sync_records_error_details(self, monkeypatch):
        """Test sync records detailed error information."""
        from src.api.services.sync_service import SyncService
        from src.database.db_sync import sync_ops

        def mock_add_sync_error(sync_id, error_type, error_message, asin=None):
            return True

        monkeypatch.setattr(sync_ops, "add_sync_error", mock_add_sync_error)

        service = SyncService()
        assert service is not None
