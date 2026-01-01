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
