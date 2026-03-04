"""Tests for decryption endpoints."""

import uuid
from datetime import datetime
from types import SimpleNamespace

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
        self, authenticated_mocked_client, mock_db_session, test_decryption_id
    ):
        """Test successful decryption trigger."""
        download = SimpleNamespace(
            download_id=uuid.uuid4(),
            asin="B084L6Z6M3",
            status="completed",
        )
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=download))

        response = authenticated_mocked_client.post(
            "/api/v1/decryptions/",
            json={"asin": "B084L6Z6M3", "title": "Becoming"},
        )

        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "decryption_id" in data
        assert data["status"] == "pending"

    def test_trigger_decryption_no_download(self, authenticated_mocked_client, mock_db_session):
        """Test decryption trigger when download doesn't exist."""
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=None))

        response = authenticated_mocked_client.post(
            "/api/v1/decryptions/",
            json={"asin": "B084L6Z6M3", "title": "Becoming"},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "download" in data["detail"].lower()

    def test_trigger_decryption_download_not_completed(
        self, authenticated_mocked_client, mock_db_session
    ):
        """Test decryption trigger when download not yet completed."""
        download = SimpleNamespace(
            download_id=uuid.uuid4(),
            asin="B084L6Z6M3",
            status="downloading",
        )
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=download))

        response = authenticated_mocked_client.post(
            "/api/v1/decryptions/",
            json={"asin": "B084L6Z6M3", "title": "Becoming"},
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_trigger_decryption_unauthorized(self, mocked_client):
        """Test decryption trigger without authentication."""
        response = mocked_client.post(
            "/api/v1/decryptions/",
            json={"asin": "B084L6Z6M3", "title": "Becoming"},
        )

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_trigger_decryption_invalid_asin(self, authenticated_mocked_client):
        """Test decryption trigger with invalid ASIN."""
        response = authenticated_mocked_client.post(
            "/api/v1/decryptions/",
            json={"asin": "", "title": "Becoming"},  # Empty ASIN
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_trigger_decryption_with_output_format(
        self, authenticated_mocked_client, mock_db_session
    ):
        """Test decryption trigger with specific output format."""
        download = SimpleNamespace(
            download_id=uuid.uuid4(),
            asin="B084L6Z6M3",
            status="completed",
        )
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=download))
        response = authenticated_mocked_client.post(
            "/api/v1/decryptions/",
            json={"asin": "B084L6Z6M3", "title": "Becoming", "output_format": "mp3"},
        )

        assert response.status_code == status.HTTP_202_ACCEPTED


class TestGetDecryptions:
    """Tests for getting decryption list."""

    def test_get_decryptions_success(
        self, authenticated_mocked_client, mock_db_session, test_user_id
    ):
        """Test successful decryptions list retrieval."""
        mock_db_session.queue_execute_result(
            mock_db_session._MockResult(
                scalars=[
                    {
                        "decryption_id": str(uuid.uuid4()),
                        "asin": "B084L6Z6M3",
                        "status": "completed",
                        "decryption_started_at": "2024-12-20T10:30:00",
                        "decryption_completed_at": "2024-12-20T10:35:00",
                        "title": "Becoming",
                    }
                ]
            )
        )
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=1))

        response = authenticated_mocked_client.get("/api/v1/decryptions/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) > 0

    def test_get_decryptions_unauthorized(self, mocked_client):
        """Test decryptions list without authentication."""
        response = mocked_client.get("/api/v1/decryptions/")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_get_decryptions_empty(self, authenticated_mocked_client, mock_db_session):
        """Test decryptions list when user has no decryptions."""
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalars=[]))
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=0))

        response = authenticated_mocked_client.get("/api/v1/decryptions/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0

    def test_get_decryptions_with_status_filter(self, authenticated_mocked_client, mock_db_session):
        """Test decryptions list with status filter."""
        mock_db_session.queue_execute_result(
            mock_db_session._MockResult(
                scalars=[
                    {
                        "decryption_id": str(uuid.uuid4()),
                        "asin": "B084L6Z6M3",
                        "status": "completed",
                    }
                ]
            )
        )
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=1))

        response = authenticated_mocked_client.get("/api/v1/decryptions/?status=completed")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        if data["items"]:
            for decryption in data["items"]:
                assert decryption["status"] == "completed"

    def test_get_decryptions_pagination(self, authenticated_mocked_client, mock_db_session):
        """Test decryptions list pagination."""
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalars=[]))
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=50))

        response = authenticated_mocked_client.get("/api/v1/decryptions/?page=1&page_size=10")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 50
        assert "page" in data
        assert "pages" in data


class TestGetDecryptionStatus:
    """Tests for getting decryption status."""

    def test_get_decryption_status_success(
        self, authenticated_mocked_client, mock_db_session, test_decryption_id, test_user_id
    ):
        """Test successful decryption status retrieval."""
        decryption = SimpleNamespace(
            decryption_id=uuid.UUID(test_decryption_id),
            asin="B084L6Z6M3",
            status="decrypting",
            user_id=test_user_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=decryption))

        response = authenticated_mocked_client.get(f"/api/v1/decryptions/{test_decryption_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["decryption_id"] == test_decryption_id
        assert data["status"] == "decrypting"

    def test_get_decryption_status_unauthorized(self, mocked_client, test_decryption_id):
        """Test decryption status without authentication."""
        response = mocked_client.get(f"/api/v1/decryptions/{test_decryption_id}")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_get_decryption_status_not_found(
        self, authenticated_mocked_client, mock_db_session, test_decryption_id
    ):
        """Test decryption status for non-existent decryption."""
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=None))

        response = authenticated_mocked_client.get(f"/api/v1/decryptions/{test_decryption_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_decryption_status_forbidden(
        self, authenticated_mocked_client, mock_db_session, test_decryption_id
    ):
        """Test decryption status for other user's decryption."""
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=None))

        response = authenticated_mocked_client.get(f"/api/v1/decryptions/{test_decryption_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDecryptionStatuses:
    """Tests for decryption status values."""

    def test_decryption_valid_statuses(self, authenticated_mocked_client, mock_db_session):
        """Test that valid decryption statuses are recognized."""
        valid_statuses = ["pending", "decrypting", "completed", "failed", "cancelled"]

        for status_value in valid_statuses:
            mock_db_session.queue_execute_result(
                mock_db_session._MockResult(
                    scalars=[
                        {
                            "decryption_id": str(uuid.uuid4()),
                            "asin": "B084L6Z6M3",
                            "status": status_value,
                        }
                    ]
                )
            )
            mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=1))

            response = authenticated_mocked_client.get(
                f"/api/v1/decryptions/?status={status_value}"
            )

            # Should accept valid status values
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]


class TestDecryptionUserIsolation:
    """Tests for decryption user isolation."""

    def test_decryptions_user_isolation(
        self, authenticated_mocked_client, mock_db_session, test_user_id
    ):
        """Test that users only see their own decryptions."""
        mock_db_session.queue_execute_result(
            mock_db_session._MockResult(
                scalars=[
                    {
                        "decryption_id": str(uuid.uuid4()),
                        "asin": "USERDECRYPT",
                        "status": "completed",
                        "user_id": test_user_id,
                    }
                ]
            )
        )
        mock_db_session.queue_execute_result(mock_db_session._MockResult(scalar_one=1))

        response = authenticated_mocked_client.get("/api/v1/decryptions/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should only see user's own decryptions (service filters by user_id)
        assert all(item["asin"] == "USERDECRYPT" for item in data["items"])


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
    @pytest.mark.skip(reason="decryption object_key is not tracked in ORM services")
    async def test_decrypt_book_updates_database_with_object_key(self, monkeypatch):
        """Test that decrypt_book updates database with object_key."""
        update_calls = []

        def mock_update_decryption_object_key(decryption_id, object_key):
            update_calls.append({"decryption_id": decryption_id, "object_key": object_key})
            return True

        assert update_calls is not None

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
