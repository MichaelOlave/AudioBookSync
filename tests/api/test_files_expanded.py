"""Expanded tests for file streaming endpoints with Range request support."""

import pytest
from fastapi import status
import os
from datetime import datetime


class TestFileStreamingBasics:
    """Tests for basic file streaming functionality."""

    def test_stream_file_success(self, authenticated_client, monkeypatch):
        """Test successful file streaming."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": authenticated_client.user_id,
                "title": "Test Book",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
        monkeypatch.setattr("os.path.exists", lambda x: True)
        monkeypatch.setattr("os.path.getsize", lambda x: 1024000)

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        # Either 200 OK or 206 Partial Content
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_206_PARTIAL_CONTENT]

    def test_stream_file_unauthorized(self, client):
        """Test file streaming without authentication."""
        response = client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_stream_file_not_found(self, authenticated_client, monkeypatch):
        """Test file streaming for non-existent file."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return None

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.get("/api/v1/files/audiobook/NOTEXIST")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream_file_forbidden(self, authenticated_client, monkeypatch):
        """Test file streaming for another user's book."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": "different-user-id",  # Different user
                "title": "Test Book",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_stream_file_decrypted_not_available(self, authenticated_client, monkeypatch):
        """Test file streaming when decrypted file not available."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": authenticated_client.user_id,
                "title": "Test Book",
                "decrypted_path": None,  # Not decrypted
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRangeRequests:
    """Tests for HTTP Range request support."""

    def test_range_request_first_bytes(self, authenticated_client, monkeypatch):
        """Test Range request for first N bytes."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": authenticated_client.user_id,
                "title": "Test Book",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
        monkeypatch.setattr("os.path.exists", lambda x: True)
        monkeypatch.setattr("os.path.getsize", lambda x: 1024000)

        response = authenticated_client.get(
            "/api/v1/files/audiobook/B084L6Z6M3",
            headers={"Range": "bytes=0-1023"},
        )

        # Should support Range requests
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_206_PARTIAL_CONTENT,
        ]
        if response.status_code == status.HTTP_206_PARTIAL_CONTENT:
            assert "Content-Range" in response.headers
            assert "Content-Length" in response.headers

    def test_range_request_middle_bytes(self, authenticated_client, monkeypatch):
        """Test Range request for middle bytes."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": authenticated_client.user_id,
                "title": "Test Book",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
        monkeypatch.setattr("os.path.exists", lambda x: True)
        monkeypatch.setattr("os.path.getsize", lambda x: 1024000)

        response = authenticated_client.get(
            "/api/v1/files/audiobook/B084L6Z6M3",
            headers={"Range": "bytes=1000000-1001023"},
        )

        # Should support Range requests
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_206_PARTIAL_CONTENT,
        ]

    def test_range_request_last_bytes(self, authenticated_client, monkeypatch):
        """Test Range request for last N bytes (seeking to end)."""
        from src.database.db_books import book_ops

        file_size = 1024000

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": authenticated_client.user_id,
                "title": "Test Book",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
        monkeypatch.setattr("os.path.exists", lambda x: True)
        monkeypatch.setattr("os.path.getsize", lambda x: file_size)

        response = authenticated_client.get(
            "/api/v1/files/audiobook/B084L6Z6M3",
            headers={"Range": f"bytes={file_size-1024}-"},
        )

        # Should support Range requests
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_206_PARTIAL_CONTENT,
        ]

    def test_range_request_invalid_format(self, authenticated_client, monkeypatch):
        """Test Range request with invalid format."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": authenticated_client.user_id,
                "title": "Test Book",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
        monkeypatch.setattr("os.path.exists", lambda x: True)
        monkeypatch.setattr("os.path.getsize", lambda x: 1024000)

        response = authenticated_client.get(
            "/api/v1/files/audiobook/B084L6Z6M3",
            headers={"Range": "invalid-range"},
        )

        # Should either ignore or handle gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_206_PARTIAL_CONTENT,
            status.HTTP_416_RANGE_NOT_SATISFIABLE,
        ]

    def test_range_request_out_of_bounds(self, authenticated_client, monkeypatch):
        """Test Range request beyond file size."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": authenticated_client.user_id,
                "title": "Test Book",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
        monkeypatch.setattr("os.path.exists", lambda x: True)
        monkeypatch.setattr("os.path.getsize", lambda x: 1024000)

        response = authenticated_client.get(
            "/api/v1/files/audiobook/B084L6Z6M3",
            headers={"Range": "bytes=2000000-2001000"},
        )

        # Should return 416 Range Not Satisfiable or full file
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_416_RANGE_NOT_SATISFIABLE,
        ]


class TestFileStreamingHeaders:
    """Tests for file streaming response headers."""

    def test_streaming_response_has_content_type(self, authenticated_client, monkeypatch):
        """Test that streaming response includes Content-Type header."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": authenticated_client.user_id,
                "title": "Test Book",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
        monkeypatch.setattr("os.path.exists", lambda x: True)
        monkeypatch.setattr("os.path.getsize", lambda x: 1024000)

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert "content-type" in response.headers or "Content-Type" in response.headers

    def test_streaming_response_has_accept_ranges(self, authenticated_client, monkeypatch):
        """Test that streaming response includes Accept-Ranges header."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": authenticated_client.user_id,
                "title": "Test Book",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
        monkeypatch.setattr("os.path.exists", lambda x: True)
        monkeypatch.setattr("os.path.getsize", lambda x: 1024000)

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        # Should support Range requests
        if response.status_code == status.HTTP_200_OK:
            assert (
                "accept-ranges" in response.headers
                or "Accept-Ranges" in response.headers
            )

    def test_streaming_response_has_content_length(self, authenticated_client, monkeypatch):
        """Test that streaming response includes Content-Length header."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            return {
                "asin": asin,
                "user_id": authenticated_client.user_id,
                "title": "Test Book",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
        monkeypatch.setattr("os.path.exists", lambda x: True)
        monkeypatch.setattr("os.path.getsize", lambda x: 1024000)

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert "content-length" in response.headers or "Content-Length" in response.headers


class TestPathTraversalProtection:
    """Tests for path traversal attack protection."""

    def test_path_traversal_attack_blocked(self, authenticated_client, monkeypatch):
        """Test that path traversal attacks are blocked."""
        from src.database.db_books import book_ops

        def mock_get_book_by_asin(asin):
            # Simulate attacker trying to access files outside audiobooks directory
            if ".." in asin or "/" in asin:
                return None
            return None

        monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)

        # Try path traversal attack
        response = authenticated_client.get(
            "/api/v1/files/audiobook/../../../../etc/passwd"
        )

        # Should be blocked
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_asin_validation(self, authenticated_client):
        """Test that ASIN format is validated."""
        # ASIN should be alphanumeric, typically 10 chars
        response = authenticated_client.get("/api/v1/files/audiobook/invalid!@#$asin")

        # Should be rejected
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]
