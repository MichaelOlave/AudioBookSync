"""Tests for audiobook file streaming endpoints."""

import pytest
from fastapi import status
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestStreamAudiobook:
    """Tests for stream audiobook endpoint."""

    def test_stream_audiobook_success(self, authenticated_client, monkeypatch):
        """Test successful audiobook streaming."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": authenticated_client.user_id,
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        # Mock file existence and size
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.stat.return_value = MagicMock(st_size=1024000)

        with patch("src.api.routers.files.Path", return_value=mock_path):
            response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["Accept-Ranges"] == "bytes"

    def test_stream_audiobook_with_range(self, authenticated_client, monkeypatch):
        """Test audiobook streaming with Range header."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": authenticated_client.user_id,
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        # Mock file
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.stat.return_value = MagicMock(st_size=1024000)

        with patch("src.api.routers.files.Path", return_value=mock_path):
            response = authenticated_client.get(
                "/api/v1/files/audiobook/B084L6Z6M3",
                headers={"Range": "bytes=0-1023"},
            )

        assert response.status_code == status.HTTP_206_PARTIAL_CONTENT
        assert "Content-Range" in response.headers
        assert "bytes 0-1023/1024000" in response.headers["Content-Range"]

    def test_stream_audiobook_not_found(self, authenticated_client, monkeypatch):
        """Test streaming non-existent audiobook."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return None

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.get("/api/v1/files/audiobook/NOTEXIST")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream_audiobook_unauthorized(self, authenticated_client, monkeypatch):
        """Test streaming another user's audiobook."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": "different-user-id",  # Different user
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_stream_audiobook_file_not_available(self, authenticated_client, monkeypatch):
        """Test streaming when decrypted file is not available."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": authenticated_client.user_id,
                "decrypted_path": None,  # No decrypted path
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream_audiobook_unauthenticated(self, client):
        """Test audiobook streaming without authentication."""
        response = client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_stream_audiobook_invalid_range(self, authenticated_client, monkeypatch):
        """Test streaming with invalid Range header."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": authenticated_client.user_id,
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        # Mock file
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.stat.return_value = MagicMock(st_size=1024000)

        with patch("src.api.routers.files.Path", return_value=mock_path):
            response = authenticated_client.get(
                "/api/v1/files/audiobook/B084L6Z6M3",
                headers={"Range": "bytes=invalid"},
            )

        # Should fall back to full file
        assert response.status_code == status.HTTP_200_OK


class TestStreamAudiobookMinIO:
    """Tests for MinIO streaming integration."""

    def test_stream_audiobook_minio_with_object_key(self, authenticated_client, monkeypatch):
        """Test streaming from MinIO when object_key exists."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": authenticated_client.user_id,
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        def mock_get_object_key_for_asin(user_id, asin):
            return "decrypted/test-book.m4b"

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        # Mock StorageService
        mock_storage_service = MagicMock()
        mock_storage_service.stream_file.return_value = b"audio data"

        with patch("src.api.routers.files._get_object_key_for_asin", mock_get_object_key_for_asin):
            with patch("src.api.routers.files.StorageService", return_value=mock_storage_service):
                response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_200_OK

    def test_stream_audiobook_fallback_to_filesystem_when_no_object_key(
        self, authenticated_client, monkeypatch
    ):
        """Test fallback to filesystem streaming when object_key is NULL."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": authenticated_client.user_id,
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        def mock_get_object_key_for_asin(user_id, asin):
            return None  # No object_key, should use filesystem

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        # Mock file
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.stat.return_value = MagicMock(st_size=1024000)

        with patch("src.api.routers.files._get_object_key_for_asin", mock_get_object_key_for_asin):
            with patch("src.api.routers.files.Path", return_value=mock_path):
                response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["Accept-Ranges"] == "bytes"

    def test_stream_audiobook_minio_with_range_header(
        self, authenticated_client, monkeypatch
    ):
        """Test HTTP Range requests work with MinIO streaming."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": authenticated_client.user_id,
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        def mock_get_object_key_for_asin(user_id, asin):
            return "decrypted/test-book.m4b"

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        # Mock StorageService to return Range request data
        mock_storage_service = MagicMock()
        mock_storage_service.stream_file.return_value = b"x" * 1024  # 1024 bytes

        # Mock file for size calculation
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.stat.return_value = MagicMock(st_size=1024000)

        with patch("src.api.routers.files._get_object_key_for_asin", mock_get_object_key_for_asin):
            with patch("src.api.routers.files.StorageService", return_value=mock_storage_service):
                with patch("src.api.routers.files.Path", return_value=mock_path):
                    response = authenticated_client.get(
                        "/api/v1/files/audiobook/B084L6Z6M3",
                        headers={"Range": "bytes=0-1023"},
                    )

        assert response.status_code == status.HTTP_206_PARTIAL_CONTENT
        assert "Content-Range" in response.headers
        assert "Accept-Ranges" in response.headers

    def test_stream_audiobook_minio_fallback_on_empty_response(
        self, authenticated_client, monkeypatch
    ):
        """Test fallback to filesystem when MinIO streaming returns empty."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": authenticated_client.user_id,
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        def mock_get_object_key_for_asin(user_id, asin):
            return "decrypted/test-book.m4b"

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        # Mock StorageService to fail (return empty bytes)
        mock_storage_service = MagicMock()
        mock_storage_service.stream_file.return_value = b""

        # Mock file
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.stat.return_value = MagicMock(st_size=1024000)

        with patch("src.api.routers.files._get_object_key_for_asin", mock_get_object_key_for_asin):
            with patch("src.api.routers.files.StorageService", return_value=mock_storage_service):
                with patch("src.api.routers.files.Path", return_value=mock_path):
                    response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_200_OK

    def test_stream_audiobook_user_ownership_enforced(
        self, authenticated_client, monkeypatch
    ):
        """Test user ownership verification still enforced with MinIO streaming."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "title": "Test Book",
                "user_id": "different-user-id",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        # Should be forbidden even if object_key exists (ownership check happens first)
        assert response.status_code == status.HTTP_403_FORBIDDEN
