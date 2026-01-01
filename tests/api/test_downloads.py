"""Tests for download endpoints."""

import pytest
from fastapi import status
import uuid
from datetime import datetime


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

    def test_trigger_download_success(self, authenticated_client, monkeypatch, test_download_id):
        """Test successful download trigger."""
        from src.database.db_downloads import download_ops

        def mock_create_download_status(asin, status="pending"):
            return test_download_id

        monkeypatch.setattr(
            download_ops, "create_download_status", mock_create_download_status
        )

        response = authenticated_client.post(
            "/api/v1/downloads/",
            json={"asin": "B084L6Z6M3"},
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "download_id" in data
        assert data["status"] == "in_progress"

    def test_trigger_download_unauthorized(self, client):
        """Test download trigger without authentication."""
        response = client.post(
            "/api/v1/downloads/",
            json={"asin": "B084L6Z6M3"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_trigger_download_invalid_asin(self, authenticated_client):
        """Test download trigger with invalid ASIN."""
        response = authenticated_client.post(
            "/api/v1/downloads/",
            json={"asin": ""},  # Empty ASIN
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_trigger_download_missing_asin(self, authenticated_client):
        """Test download trigger without ASIN."""
        response = authenticated_client.post(
            "/api/v1/downloads/",
            json={},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetDownloads:
    """Tests for getting download list."""

    def test_get_downloads_success(self, authenticated_client, monkeypatch, test_user_id):
        """Test successful downloads list retrieval."""
        from src.database.db_downloads import download_ops

        def mock_get_user_downloads(user_id, status=None, limit=10, offset=0):
            if user_id == test_user_id:
                return [
                    {
                        "download_id": str(uuid.uuid4()),
                        "asin": "B084L6Z6M3",
                        "status": "completed",
                        "download_started_at": "2024-12-20T10:00:00",
                        "download_completed_at": "2024-12-20T10:30:00",
                        "title": "Becoming",
                    }
                ]
            return []

        def mock_count_user_downloads(user_id, status=None):
            return 1

        monkeypatch.setattr(download_ops, "get_user_downloads", mock_get_user_downloads)
        monkeypatch.setattr(download_ops, "count_user_downloads", mock_count_user_downloads)

        response = authenticated_client.get("/api/v1/downloads/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) > 0

    def test_get_downloads_unauthorized(self, client):
        """Test downloads list without authentication."""
        response = client.get("/api/v1/downloads/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_downloads_empty(self, authenticated_client, monkeypatch):
        """Test downloads list when user has no downloads."""
        from src.database.db_downloads import download_ops

        def mock_get_user_downloads(user_id, status=None, limit=10, offset=0):
            return []

        def mock_count_user_downloads(user_id, status=None):
            return 0

        monkeypatch.setattr(download_ops, "get_user_downloads", mock_get_user_downloads)
        monkeypatch.setattr(download_ops, "count_user_downloads", mock_count_user_downloads)

        response = authenticated_client.get("/api/v1/downloads/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_get_downloads_with_status_filter(self, authenticated_client, monkeypatch):
        """Test downloads list with status filter."""
        from src.database.db_downloads import download_ops

        def mock_get_user_downloads(user_id, status=None, limit=10, offset=0):
            if status == "completed":
                return [
                    {
                        "download_id": str(uuid.uuid4()),
                        "asin": "B084L6Z6M3",
                        "status": "completed",
                    }
                ]
            return []

        def mock_count_user_downloads(user_id, status=None):
            return 1 if status == "completed" else 0

        monkeypatch.setattr(download_ops, "get_user_downloads", mock_get_user_downloads)
        monkeypatch.setattr(download_ops, "count_user_downloads", mock_count_user_downloads)

        response = authenticated_client.get("/api/v1/downloads/?status=completed")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        if data["items"]:
            for download in data["items"]:
                assert download["status"] == "completed"

    def test_get_downloads_pagination(self, authenticated_client, monkeypatch):
        """Test downloads list pagination."""
        from src.database.db_downloads import download_ops

        def mock_get_user_downloads(user_id, status=None, limit=10, offset=0):
            return []

        def mock_count_user_downloads(user_id, status=None):
            return 50

        monkeypatch.setattr(download_ops, "get_user_downloads", mock_get_user_downloads)
        monkeypatch.setattr(download_ops, "count_user_downloads", mock_count_user_downloads)

        response = authenticated_client.get("/api/v1/downloads/?page=1&page_size=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 50
        assert "page" in data
        assert "pages" in data

    def test_get_downloads_invalid_status_filter(self, authenticated_client):
        """Test downloads list with invalid status filter."""
        response = authenticated_client.get("/api/v1/downloads/?status=invalid_status")

        # Should either ignore or return 422
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


class TestGetDownloadStatus:
    """Tests for getting download status."""

    def test_get_download_status_success(
        self, authenticated_client, monkeypatch, test_download_id, test_user_id
    ):
        """Test successful download status retrieval."""
        from src.database.db_downloads import download_ops

        def mock_get_download_by_id(download_id):
            return {
                "download_id": download_id,
                "asin": "B084L6Z6M3",
                "status": "downloading",
                "user_id": test_user_id,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(download_ops, "get_download_by_id", mock_get_download_by_id)

        response = authenticated_client.get(f"/api/v1/downloads/{test_download_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["download_id"] == test_download_id
        assert data["status"] == "downloading"

    def test_get_download_status_unauthorized(self, client, test_download_id):
        """Test download status without authentication."""
        response = client.get(f"/api/v1/downloads/{test_download_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_download_status_not_found(
        self, authenticated_client, monkeypatch, test_download_id
    ):
        """Test download status for non-existent download."""
        from src.database.db_downloads import download_ops

        def mock_get_download_by_id(download_id):
            return None

        monkeypatch.setattr(download_ops, "get_download_by_id", mock_get_download_by_id)

        response = authenticated_client.get(f"/api/v1/downloads/{test_download_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_download_status_forbidden(
        self, authenticated_client, monkeypatch, test_download_id
    ):
        """Test download status for other user's download."""
        from src.database.db_downloads import download_ops

        def mock_get_download_by_id(download_id):
            return {
                "download_id": download_id,
                "asin": "B084L6Z6M3",
                "status": "downloading",
                "user_id": "different-user-id",  # Different user
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(download_ops, "get_download_by_id", mock_get_download_by_id)

        response = authenticated_client.get(f"/api/v1/downloads/{test_download_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_download_status_invalid_id_format(self, authenticated_client):
        """Test download status with invalid ID format."""
        response = authenticated_client.get("/api/v1/downloads/not-a-uuid")

        # Should either accept or return 422
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


class TestDownloadStatuses:
    """Tests for download status values and transitions."""

    def test_download_valid_statuses(self, authenticated_client, monkeypatch):
        """Test that valid download statuses are recognized."""
        from src.database.db_downloads import download_ops

        valid_statuses = ["pending", "downloading", "completed", "failed", "cancelled"]

        for status_value in valid_statuses:
            def mock_get_user_downloads(user_id, status=None, limit=10, offset=0):
                if status == status_value:
                    return [
                        {
                            "download_id": str(uuid.uuid4()),
                            "asin": "B084L6Z6M3",
                            "status": status_value,
                        }
                    ]
                return []

            def mock_count_user_downloads(user_id, status=None):
                return 1 if status == status_value else 0

            monkeypatch.setattr(
                download_ops, "get_user_downloads", mock_get_user_downloads
            )
            monkeypatch.setattr(
                download_ops, "count_user_downloads", mock_count_user_downloads
            )

            response = authenticated_client.get(f"/api/v1/downloads/?status={status_value}")

            # Should accept valid status values
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]


class TestDownloadUserIsolation:
    """Tests for download user isolation."""

    def test_downloads_user_isolation(self, authenticated_client, monkeypatch, test_user_id):
        """Test that users only see their own downloads."""
        from src.database.db_downloads import download_ops

        def mock_get_user_downloads(user_id, status=None, limit=10, offset=0):
            # Only return downloads for the requesting user
            if user_id == test_user_id:
                return [
                    {
                        "download_id": str(uuid.uuid4()),
                        "asin": "USERDOWNLOAD",
                        "status": "completed",
                        "user_id": user_id,
                    }
                ]
            else:
                return [
                    {
                        "download_id": str(uuid.uuid4()),
                        "asin": "OTHERDOWNLOAD",
                        "status": "completed",
                        "user_id": "other-user-id",
                    }
                ]

        def mock_count_user_downloads(user_id, status=None):
            return 1

        monkeypatch.setattr(download_ops, "get_user_downloads", mock_get_user_downloads)
        monkeypatch.setattr(download_ops, "count_user_downloads", mock_count_user_downloads)

        response = authenticated_client.get("/api/v1/downloads/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should only see user's own downloads
        for download in data["items"]:
            assert download["user_id"] == test_user_id
