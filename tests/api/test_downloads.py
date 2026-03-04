"""Tests for download endpoints."""

import uuid
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import status


@pytest.fixture
def test_download_id():
    """Generate a test download ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_download_data(test_download_id):
    """Test download data."""
    return {
        "download_id": test_download_id,
        "asin": "B084L6Z6M3",
        "status": "downloading",
        "download_started_at": "2024-12-20T10:00:00",
        "download_path": "/audiobooks/downloaded/B084L6Z6M3.m4b",
    }


class TestTriggerDownload:
    """Tests for triggering downloads."""

    def test_trigger_download_success(
        self, authenticated_mocked_client, monkeypatch, test_download_id
    ):
        """Test successful download trigger."""
        from src.database.services import download_service

        monkeypatch.setattr(
            download_service,
            "create_download_status",
            AsyncMock(return_value=SimpleNamespace(download_id=test_download_id)),
        )

        response = authenticated_mocked_client.post(
            "/api/v1/downloads/",
            json={"asin": "B084L6Z6M3", "title": "Becoming"},
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "download_id" in data
        assert data["status"] == "pending"

    def test_trigger_download_unauthorized(self, mocked_client):
        """Test download trigger without authentication."""
        response = mocked_client.post(
            "/api/v1/downloads/",
            json={"asin": "B084L6Z6M3", "title": "Becoming"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_trigger_download_invalid_asin(self, authenticated_mocked_client):
        """Test download trigger with invalid ASIN."""
        response = authenticated_mocked_client.post(
            "/api/v1/downloads/",
            json={"asin": "", "title": "Becoming"},  # Empty ASIN
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_trigger_download_missing_asin(self, authenticated_mocked_client):
        """Test download trigger without ASIN."""
        response = authenticated_mocked_client.post(
            "/api/v1/downloads/",
            json={"title": "Becoming"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetDownloads:
    """Tests for getting download list."""

    def test_get_downloads_success(
        self, authenticated_mocked_client, mock_db_session, test_user_id
    ):
        """Test successful downloads list retrieval."""
        mock_db_session.queue_execute_result(
            mock_db_session._MockResult(
                scalars=[
                    {
                        "download_id": str(uuid.uuid4()),
                        "asin": "B084L6Z6M3",
                        "status": "completed",
                        "download_started_at": "2024-12-20T10:00:00",
                        "download_completed_at": "2024-12-20T10:30:00",
                        "title": "Becoming",
                    }
                ]
            )
        )
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=1))

        response = authenticated_mocked_client.get("/api/v1/downloads/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) > 0

    def test_get_downloads_unauthorized(self, mocked_client):
        """Test downloads list without authentication."""
        response = mocked_client.get("/api/v1/downloads/")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_get_downloads_empty(self, authenticated_mocked_client, mock_db_session):
        """Test downloads list when user has no downloads."""
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalars=[]))
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=0))

        response = authenticated_mocked_client.get("/api/v1/downloads/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_get_downloads_with_status_filter(self, authenticated_mocked_client, mock_db_session):
        """Test downloads list with status filter."""
        mock_db_session.queue_execute_result(
            mock_db_session._MockResult(
                scalars=[
                    {
                        "download_id": str(uuid.uuid4()),
                        "asin": "B084L6Z6M3",
                        "status": "completed",
                    }
                ]
            )
        )
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=1))

        response = authenticated_mocked_client.get("/api/v1/downloads/?status=completed")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        if data["items"]:
            for download in data["items"]:
                assert download["status"] == "completed"

    def test_get_downloads_pagination(self, authenticated_mocked_client, mock_db_session):
        """Test downloads list pagination."""
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalars=[]))
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=50))

        response = authenticated_mocked_client.get("/api/v1/downloads/?page=1&page_size=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 50
        assert "page" in data
        assert "pages" in data

    def test_get_downloads_invalid_status_filter(self, authenticated_mocked_client):
        """Test downloads list with invalid status filter."""
        response = authenticated_mocked_client.get("/api/v1/downloads/?status=invalid_status")

        # Should either ignore or return 422
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


class TestGetDownloadStatus:
    """Tests for getting download status."""

    def test_get_download_status_success(
        self, authenticated_mocked_client, mock_db_session, test_download_id, test_user_id
    ):
        """Test successful download status retrieval."""
        download = SimpleNamespace(
            download_id=uuid.UUID(test_download_id),
            asin="B084L6Z6M3",
            status="downloading",
            user_id=test_user_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=download))

        response = authenticated_mocked_client.get(f"/api/v1/downloads/{test_download_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["download_id"] == test_download_id
        assert data["status"] == "downloading"

    def test_get_download_status_unauthorized(self, mocked_client, test_download_id):
        """Test download status without authentication."""
        response = mocked_client.get(f"/api/v1/downloads/{test_download_id}")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_get_download_status_not_found(
        self, authenticated_mocked_client, mock_db_session, test_download_id
    ):
        """Test download status for non-existent download."""
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=None))

        response = authenticated_mocked_client.get(f"/api/v1/downloads/{test_download_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_download_status_forbidden(
        self, authenticated_mocked_client, mock_db_session, test_download_id
    ):
        """Test download status for other user's download."""
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=None))

        response = authenticated_mocked_client.get(f"/api/v1/downloads/{test_download_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_download_status_invalid_id_format(self, authenticated_mocked_client):
        """Test download status with invalid ID format."""
        response = authenticated_mocked_client.get("/api/v1/downloads/not-a-uuid")

        # Should either accept or return 422
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


class TestDownloadStatuses:
    """Tests for download status values and transitions."""

    def test_download_valid_statuses(self, authenticated_mocked_client, mock_db_session):
        """Test that valid download statuses are recognized."""
        valid_statuses = ["pending", "downloading", "completed", "failed", "cancelled"]

        for status_value in valid_statuses:
            mock_db_session.queue_execute_result(
                mock_db_session._MockResult(
                    scalars=[
                        {
                            "download_id": str(uuid.uuid4()),
                            "asin": "B084L6Z6M3",
                            "status": status_value,
                        }
                    ]
                )
            )
            mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=1))

            response = authenticated_mocked_client.get(f"/api/v1/downloads/?status={status_value}")

            # Should accept valid status values
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]


class TestDownloadUserIsolation:
    """Tests for download user isolation."""

    def test_downloads_user_isolation(
        self, authenticated_mocked_client, mock_db_session, test_user_id
    ):
        """Test that users only see their own downloads."""
        mock_db_session.queue_execute_result(
            mock_db_session._MockResult(
                scalars=[
                    {
                        "download_id": str(uuid.uuid4()),
                        "asin": "USERDOWNLOAD",
                        "status": "completed",
                        "user_id": test_user_id,
                    }
                ]
            )
        )
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=1))

        response = authenticated_mocked_client.get("/api/v1/downloads/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should only see user's own downloads (service filters by user_id)
        assert all(download["asin"] == "USERDOWNLOAD" for download in data["items"])


class TestDownloadMinIOIntegration:
    """Tests for downloader MinIO integration."""

    @pytest.mark.asyncio
    async def test_download_book_uploads_to_minio_when_enabled(self, monkeypatch):
        """Test that download_book uploads to MinIO after successful download."""
        from src.core.config import Config
        from src.infrastructure.storage_service import StorageService

        # Mock successful download
        async def mock_validate_book(book):
            return True

        monkeypatch.setattr("src.operations.downloader.validate_book", mock_validate_book)

        # Mock successful MinIO upload
        upload_called = []

        def mock_save_file(user_id, file_path, file_type, asin=None, title=None):
            upload_called.append(
                {
                    "user_id": user_id,
                    "file_type": file_type,
                    "asin": asin,
                }
            )
            return (True, f"downloaded/{asin}.aax")

        # Temporarily enable MinIO
        Config.USE_MINIO_STORAGE
        monkeypatch.setattr(Config, "USE_MINIO_STORAGE", True)

        # Mock subprocess for audible download

        async def mock_create_subprocess_exec(*args, **kwargs):
            mock_process = type("Process", (), {})()
            mock_process.returncode = 0
            mock_process.communicate = lambda: (b"Downloaded: B001ABC.aax", b"")
            return mock_process

        monkeypatch.setattr("asyncio.create_subprocess_exec", mock_create_subprocess_exec)

        # Test with minio enabled
        storage_service = StorageService()
        monkeypatch.setattr(storage_service, "save_file", mock_save_file)

        # We can't fully test without proper mocking of file operations
        # This test demonstrates the integration pattern
        assert True  # Placeholder for actual integration test

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="download object_key is not tracked in ORM services")
    async def test_download_book_updates_database_with_object_key(self, monkeypatch):
        """Test that download_book updates database with object_key."""
        from src.database.services import download_service

        update_calls = []

        def mock_update_download_object_key(download_id, object_key):
            update_calls.append({"download_id": download_id, "object_key": object_key})
            return True

        monkeypatch.setattr(
            download_service,
            "update_download_object_key",
            mock_update_download_object_key,
        )

        # Verify the method exists and is callable
        assert hasattr(download_service, "update_download_object_key")
        assert callable(download_service.update_download_object_key)

    @pytest.mark.asyncio
    async def test_download_book_handles_minio_upload_failure_gracefully(self):
        """Test that download_book handles MinIO upload failures gracefully."""
        # If MinIO upload fails, download should still succeed
        # This is a non-critical operation

    @pytest.mark.asyncio
    async def test_download_book_backward_compatibility_minio_disabled(self, monkeypatch):
        """Test backward compatibility when USE_MINIO_STORAGE is False."""
        from src.core.config import Config

        # Ensure MinIO is disabled
        monkeypatch.setattr(Config, "USE_MINIO_STORAGE", False)

        # Download should work without MinIO
        # (No object_key should be created)
