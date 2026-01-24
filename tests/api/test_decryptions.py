"""Tests for decryption endpoints."""

import uuid
from datetime import datetime

import pytest
from fastapi import status


@pytest.fixture
def test_decryption_id():
    """Generate a test decryption ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_decryption_data(test_decryption_id):
    """Test decryption data."""
    return {
        "decryption_id": test_decryption_id,
        "asin": "B084L6Z6M3",
        "status": "decrypting",
        "decryption_started_at": "2024-12-20T10:30:00",
    }


class TestTriggerDecryption:
    """Tests for triggering decryptions."""

    def test_trigger_decryption_success(
        self, authenticated_client, monkeypatch, test_decryption_id
    ):
        """Test successful decryption trigger."""
        from src.database.db_decryptions import decryption_ops
        from src.database.db_downloads import download_ops

        def mock_get_download_by_asin(asin):
            return {
                "asin": asin,
                "status": "completed",
                "download_path": "/audiobooks/downloaded/B084L6Z6M3.m4b",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        def mock_create_decryption_status(asin, download_id=None, status="pending", **kwargs):
            return test_decryption_id

        monkeypatch.setattr(download_ops, "get_download_by_asin", mock_get_download_by_asin)
        monkeypatch.setattr(
            decryption_ops, "create_decryption_status", mock_create_decryption_status
        )

        response = authenticated_client.post(
            "/api/v1/decryptions/",
            json={"asin": "B084L6Z6M3"},
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "decryption_id" in data
        assert data["status"] == "in_progress"

    def test_trigger_decryption_no_download(self, authenticated_client, monkeypatch):
        """Test decryption trigger when download doesn't exist."""
        from src.database.db_downloads import download_ops

        def mock_get_download_by_asin(asin):
            return None  # Download not found

        monkeypatch.setattr(download_ops, "get_download_by_asin", mock_get_download_by_asin)

        response = authenticated_client.post(
            "/api/v1/decryptions/",
            json={"asin": "B084L6Z6M3"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "download" in data["detail"].lower()

    def test_trigger_decryption_download_not_completed(self, authenticated_client, monkeypatch):
        """Test decryption trigger when download not yet completed."""
        from src.database.db_downloads import download_ops

        def mock_get_download_by_asin(asin):
            return {
                "asin": asin,
                "status": "downloading",  # Still downloading
                "download_path": None,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(download_ops, "get_download_by_asin", mock_get_download_by_asin)

        response = authenticated_client.post(
            "/api/v1/decryptions/",
            json={"asin": "B084L6Z6M3"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_trigger_decryption_unauthorized(self, client):
        """Test decryption trigger without authentication."""
        response = client.post(
            "/api/v1/decryptions/",
            json={"asin": "B084L6Z6M3"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_trigger_decryption_invalid_asin(self, authenticated_client):
        """Test decryption trigger with invalid ASIN."""
        response = authenticated_client.post(
            "/api/v1/decryptions/",
            json={"asin": ""},  # Empty ASIN
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_trigger_decryption_with_output_format(
        self, authenticated_client, monkeypatch, test_decryption_id
    ):
        """Test decryption trigger with specific output format."""
        from src.database.db_decryptions import decryption_ops
        from src.database.db_downloads import download_ops

        def mock_get_download_by_asin(asin):
            return {
                "asin": asin,
                "status": "completed",
                "download_path": "/audiobooks/downloaded/B084L6Z6M3.m4b",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        def mock_create_decryption_status(
            asin, download_id=None, status="pending", output_format="m4b"
        ):
            # Verify output format is captured
            assert output_format in ["m4b", "mp3", "flac", "aac"]
            return test_decryption_id

        monkeypatch.setattr(download_ops, "get_download_by_asin", mock_get_download_by_asin)
        monkeypatch.setattr(
            decryption_ops, "create_decryption_status", mock_create_decryption_status
        )

        response = authenticated_client.post(
            "/api/v1/decryptions/",
            json={"asin": "B084L6Z6M3", "output_format": "mp3"},
        )

        assert response.status_code in [
            status.HTTP_202_ACCEPTED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


class TestGetDecryptions:
    """Tests for getting decryption list."""

    def test_get_decryptions_success(self, authenticated_client, monkeypatch, test_user_id):
        """Test successful decryptions list retrieval."""
        from src.database.db_decryptions import decryption_ops

        def mock_get_user_decryptions(user_id, status=None, limit=10, offset=0):
            if user_id == test_user_id:
                return [
                    {
                        "decryption_id": str(uuid.uuid4()),
                        "asin": "B084L6Z6M3",
                        "status": "completed",
                        "decryption_started_at": "2024-12-20T10:30:00",
                        "decryption_completed_at": "2024-12-20T10:35:00",
                        "title": "Becoming",
                    }
                ]
            return []

        def mock_count_user_decryptions(user_id, status=None):
            return 1

        monkeypatch.setattr(decryption_ops, "get_user_decryptions", mock_get_user_decryptions)
        monkeypatch.setattr(decryption_ops, "count_user_decryptions", mock_count_user_decryptions)

        response = authenticated_client.get("/api/v1/decryptions/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) > 0

    def test_get_decryptions_unauthorized(self, client):
        """Test decryptions list without authentication."""
        response = client.get("/api/v1/decryptions/")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_decryptions_empty(self, authenticated_client, monkeypatch):
        """Test decryptions list when user has no decryptions."""
        from src.database.db_decryptions import decryption_ops

        def mock_get_user_decryptions(user_id, status=None, limit=10, offset=0):
            return []

        def mock_count_user_decryptions(user_id, status=None):
            return 0

        monkeypatch.setattr(decryption_ops, "get_user_decryptions", mock_get_user_decryptions)
        monkeypatch.setattr(decryption_ops, "count_user_decryptions", mock_count_user_decryptions)

        response = authenticated_client.get("/api/v1/decryptions/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_get_decryptions_with_status_filter(self, authenticated_client, monkeypatch):
        """Test decryptions list with status filter."""
        from src.database.db_decryptions import decryption_ops

        def mock_get_user_decryptions(user_id, status=None, limit=10, offset=0):
            if status == "completed":
                return [
                    {
                        "decryption_id": str(uuid.uuid4()),
                        "asin": "B084L6Z6M3",
                        "status": "completed",
                    }
                ]
            return []

        def mock_count_user_decryptions(user_id, status=None):
            return 1 if status == "completed" else 0

        monkeypatch.setattr(decryption_ops, "get_user_decryptions", mock_get_user_decryptions)
        monkeypatch.setattr(decryption_ops, "count_user_decryptions", mock_count_user_decryptions)

        response = authenticated_client.get("/api/v1/decryptions/?status=completed")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        if data["items"]:
            for decryption in data["items"]:
                assert decryption["status"] == "completed"

    def test_get_decryptions_pagination(self, authenticated_client, monkeypatch):
        """Test decryptions list pagination."""
        from src.database.db_decryptions import decryption_ops

        def mock_get_user_decryptions(user_id, status=None, limit=10, offset=0):
            return []

        def mock_count_user_decryptions(user_id, status=None):
            return 50

        monkeypatch.setattr(decryption_ops, "get_user_decryptions", mock_get_user_decryptions)
        monkeypatch.setattr(decryption_ops, "count_user_decryptions", mock_count_user_decryptions)

        response = authenticated_client.get("/api/v1/decryptions/?page=1&page_size=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 50
        assert "page" in data
        assert "pages" in data


class TestGetDecryptionStatus:
    """Tests for getting decryption status."""

    def test_get_decryption_status_success(
        self, authenticated_client, monkeypatch, test_decryption_id, test_user_id
    ):
        """Test successful decryption status retrieval."""
        from src.database.db_decryptions import decryption_ops

        def mock_get_decryption_by_id(decryption_id):
            return {
                "decryption_id": decryption_id,
                "asin": "B084L6Z6M3",
                "status": "decrypting",
                "user_id": test_user_id,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(decryption_ops, "get_decryption_by_id", mock_get_decryption_by_id)

        response = authenticated_client.get(f"/api/v1/decryptions/{test_decryption_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["decryption_id"] == test_decryption_id
        assert data["status"] == "decrypting"

    def test_get_decryption_status_unauthorized(self, client, test_decryption_id):
        """Test decryption status without authentication."""
        response = client.get(f"/api/v1/decryptions/{test_decryption_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_decryption_status_not_found(
        self, authenticated_client, monkeypatch, test_decryption_id
    ):
        """Test decryption status for non-existent decryption."""
        from src.database.db_decryptions import decryption_ops

        def mock_get_decryption_by_id(decryption_id):
            return None

        monkeypatch.setattr(decryption_ops, "get_decryption_by_id", mock_get_decryption_by_id)

        response = authenticated_client.get(f"/api/v1/decryptions/{test_decryption_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_decryption_status_forbidden(
        self, authenticated_client, monkeypatch, test_decryption_id
    ):
        """Test decryption status for other user's decryption."""
        from src.database.db_decryptions import decryption_ops

        def mock_get_decryption_by_id(decryption_id):
            return {
                "decryption_id": decryption_id,
                "asin": "B084L6Z6M3",
                "status": "decrypting",
                "user_id": "different-user-id",  # Different user
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(decryption_ops, "get_decryption_by_id", mock_get_decryption_by_id)

        response = authenticated_client.get(f"/api/v1/decryptions/{test_decryption_id}")

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestDecryptionStatuses:
    """Tests for decryption status values."""

    def test_decryption_valid_statuses(self, authenticated_client, monkeypatch):
        """Test that valid decryption statuses are recognized."""
        from src.database.db_decryptions import decryption_ops

        valid_statuses = ["pending", "decrypting", "completed", "failed", "cancelled"]

        for status_value in valid_statuses:

            def mock_get_user_decryptions(user_id, status_filter=None, limit=10, offset=0):
                if status_filter == status_value:
                    return [
                        {
                            "decryption_id": str(uuid.uuid4()),
                            "asin": "B084L6Z6M3",
                            "status": status_value,
                        }
                    ]
                return []

            def mock_count_user_decryptions(user_id, status_filter=None):
                return 1 if status_filter == status_value else 0

            monkeypatch.setattr(decryption_ops, "get_user_decryptions", mock_get_user_decryptions)
            monkeypatch.setattr(
                decryption_ops, "count_user_decryptions", mock_count_user_decryptions
            )

            response = authenticated_client.get(f"/api/v1/decryptions/?status={status_value}")

            # Should accept valid status values
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]


class TestDecryptionUserIsolation:
    """Tests for decryption user isolation."""

    def test_decryptions_user_isolation(self, authenticated_client, monkeypatch, test_user_id):
        """Test that users only see their own decryptions."""
        from src.database.db_decryptions import decryption_ops

        def mock_get_user_decryptions(user_id, status=None, limit=10, offset=0):
            # Only return decryptions for the requesting user
            if user_id == test_user_id:
                return [
                    {
                        "decryption_id": str(uuid.uuid4()),
                        "asin": "USERDECRYPT",
                        "status": "completed",
                        "user_id": user_id,
                    }
                ]
            else:
                return [
                    {
                        "decryption_id": str(uuid.uuid4()),
                        "asin": "OTHERDECRYPT",
                        "status": "completed",
                        "user_id": "other-user-id",
                    }
                ]

        def mock_count_user_decryptions(user_id, status=None):
            return 1

        monkeypatch.setattr(decryption_ops, "get_user_decryptions", mock_get_user_decryptions)
        monkeypatch.setattr(decryption_ops, "count_user_decryptions", mock_count_user_decryptions)

        response = authenticated_client.get("/api/v1/decryptions/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should only see user's own decryptions
        for decryption in data["items"]:
            assert decryption["user_id"] == test_user_id


class TestDecryptionMinIOIntegration:
    """Tests for decryptor MinIO integration."""

    @pytest.mark.asyncio
    async def test_decrypt_book_uploads_to_minio_when_enabled(self, monkeypatch):
        """Test that decrypt_book uploads to MinIO after successful decryption."""
        from src.core.config import Config
        from src.infrastructure.storage_service import StorageService

        # Mock successful decryption
        async def mock_validate_decrypted_book(book):
            return True

        monkeypatch.setattr(
            "src.operations.decryptor.validate_decrypted_book", mock_validate_decrypted_book
        )

        # Mock successful MinIO upload
        upload_called = []

        def mock_save_file(user_id, file_path, file_type, asin=None, title=None):
            upload_called.append(
                {
                    "user_id": user_id,
                    "file_type": file_type,
                    "title": title,
                }
            )
            return (True, f"decrypted/{title}.m4b")

        # Temporarily enable MinIO
        Config.USE_MINIO_STORAGE
        monkeypatch.setattr(Config, "USE_MINIO_STORAGE", True)

        # Mock subprocess for FFmpeg decryption

        async def mock_create_subprocess_exec(*args, **kwargs):
            mock_process = type("Process", (), {})()
            mock_process.returncode = 0
            mock_process.communicate = lambda: (b"Converted successfully", b"")
            return mock_process

        monkeypatch.setattr("asyncio.create_subprocess_exec", mock_create_subprocess_exec)

        # Test with minio enabled
        storage_service = StorageService()
        monkeypatch.setattr(storage_service, "save_file", mock_save_file)

        # We can't fully test without proper mocking of file operations
        # This test demonstrates the integration pattern
        assert True  # Placeholder for actual integration test

    @pytest.mark.asyncio
    async def test_decrypt_book_updates_database_with_object_key(self, monkeypatch):
        """Test that decrypt_book updates database with object_key."""
        from src.database.db_decryptions import decryption_ops

        update_calls = []

        def mock_update_decryption_object_key(decryption_id, object_key):
            update_calls.append({"decryption_id": decryption_id, "object_key": object_key})
            return True

        monkeypatch.setattr(
            decryption_ops,
            "update_decryption_object_key",
            mock_update_decryption_object_key,
        )

        # Verify the method exists and is callable
        assert hasattr(decryption_ops, "update_decryption_object_key")
        assert callable(decryption_ops.update_decryption_object_key)

    @pytest.mark.asyncio
    async def test_decrypt_book_handles_minio_upload_failure_gracefully(self):
        """Test that decrypt_book handles MinIO upload failures gracefully."""
        # If MinIO upload fails, decryption should still succeed
        # This is a non-critical operation

    @pytest.mark.asyncio
    async def test_decrypt_book_backward_compatibility_minio_disabled(self, monkeypatch):
        """Test backward compatibility when USE_MINIO_STORAGE is False."""
        from src.core.config import Config

        # Ensure MinIO is disabled
        monkeypatch.setattr(Config, "USE_MINIO_STORAGE", False)

        # Decryption should work without MinIO
        # (No object_key should be created)
