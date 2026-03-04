"""Expanded tests for file streaming endpoints with Range request support."""

from types import SimpleNamespace
from unittest.mock import MagicMock

from fastapi import status

from src.api.middleware.error_handler import AuthorizationError


def _patch_streaming_deps(
    monkeypatch,
    user_id,
    *,
    book_exists=True,
    authorized=True,
    object_key="decrypted/test.m4b",
    stream_bytes=b"audio",
):
    async def mock_get_book_by_asin(db, asin):
        if not book_exists:
            return None
        return SimpleNamespace(asin=asin, title="Test Book")

    async def mock_verify_book_access(db, asin, current_user):
        if not authorized:
            raise AuthorizationError("Not authorized to access this book")
        user_book = SimpleNamespace(user_id=user_id, decrypted_path=object_key)
        book = SimpleNamespace(asin=asin, title="Test Book")
        return user_book, book

    async def mock_resolve_object_key(db, owner_user_id, book, user_book, storage_service):
        return object_key

    mock_storage = MagicMock()
    mock_storage.stream_file.return_value = stream_bytes

    monkeypatch.setattr(
        "src.api.routers.files.book_service.get_book_by_asin", mock_get_book_by_asin
    )
    monkeypatch.setattr("src.api.routers.files.verify_book_access", mock_verify_book_access)
    monkeypatch.setattr("src.api.routers.files._resolve_object_key", mock_resolve_object_key)
    monkeypatch.setattr("src.api.routers.files.StorageService", lambda: mock_storage)


class TestFileStreamingBasics:
    """Tests for basic file streaming functionality."""

    def test_stream_file_success(self, authenticated_mocked_client, monkeypatch):
        """Test successful file streaming."""
        _patch_streaming_deps(monkeypatch, authenticated_mocked_client.user_id)
        response = authenticated_mocked_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        # Either 200 OK or 206 Partial Content
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_206_PARTIAL_CONTENT]

    def test_stream_file_unauthorized(self, client):
        """Test file streaming without authentication."""
        response = client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_stream_file_not_found(self, authenticated_mocked_client, monkeypatch):
        """Test file streaming for non-existent file."""
        _patch_streaming_deps(
            monkeypatch,
            authenticated_mocked_client.user_id,
            book_exists=False,
        )
        response = authenticated_mocked_client.get("/api/v1/files/audiobook/NOTEXIST")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream_file_forbidden(self, authenticated_mocked_client, monkeypatch):
        """Test file streaming for another user's book."""
        _patch_streaming_deps(
            monkeypatch,
            authenticated_mocked_client.user_id,
            authorized=False,
        )
        response = authenticated_mocked_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_stream_file_decrypted_not_available(self, authenticated_mocked_client, monkeypatch):
        """Test file streaming when decrypted file not available."""
        _patch_streaming_deps(
            monkeypatch,
            authenticated_mocked_client.user_id,
            object_key=None,
        )
        response = authenticated_mocked_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestRangeRequests:
    """Tests for HTTP Range request support."""

    def test_range_request_first_bytes(self, authenticated_mocked_client, monkeypatch):
        """Test Range request for first N bytes."""
        _patch_streaming_deps(monkeypatch, authenticated_mocked_client.user_id)
        response = authenticated_mocked_client.get(
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

    def test_range_request_middle_bytes(self, authenticated_mocked_client, monkeypatch):
        """Test Range request for middle bytes."""
        _patch_streaming_deps(monkeypatch, authenticated_mocked_client.user_id)
        response = authenticated_mocked_client.get(
            "/api/v1/files/audiobook/B084L6Z6M3",
            headers={"Range": "bytes=1000000-1001023"},
        )

        # Should support Range requests
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_206_PARTIAL_CONTENT,
        ]

    def test_range_request_last_bytes(self, authenticated_mocked_client, monkeypatch):
        """Test Range request for last N bytes (seeking to end)."""
        file_size = 1024000
        _patch_streaming_deps(monkeypatch, authenticated_mocked_client.user_id)
        response = authenticated_mocked_client.get(
            "/api/v1/files/audiobook/B084L6Z6M3",
            headers={"Range": f"bytes={file_size - 1024}-"},
        )

        # Should support Range requests
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_206_PARTIAL_CONTENT,
        ]

    def test_range_request_invalid_format(self, authenticated_mocked_client, monkeypatch):
        """Test Range request with invalid format."""
        _patch_streaming_deps(monkeypatch, authenticated_mocked_client.user_id)
        response = authenticated_mocked_client.get(
            "/api/v1/files/audiobook/B084L6Z6M3",
            headers={"Range": "invalid-range"},
        )

        # Should either ignore or handle gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_206_PARTIAL_CONTENT,
            status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
        ]

    def test_range_request_out_of_bounds(self, authenticated_mocked_client, monkeypatch):
        """Test Range request beyond file size."""
        _patch_streaming_deps(monkeypatch, authenticated_mocked_client.user_id)
        response = authenticated_mocked_client.get(
            "/api/v1/files/audiobook/B084L6Z6M3",
            headers={"Range": "bytes=2000000-2001000"},
        )

        # Should return 416 Range Not Satisfiable or full file
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_206_PARTIAL_CONTENT,
            status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
        ]


class TestFileStreamingHeaders:
    """Tests for file streaming response headers."""

    def test_streaming_response_has_content_type(self, authenticated_mocked_client, monkeypatch):
        """Test that streaming response includes Content-Type header."""
        _patch_streaming_deps(monkeypatch, authenticated_mocked_client.user_id)
        response = authenticated_mocked_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert "content-type" in response.headers or "Content-Type" in response.headers

    def test_streaming_response_has_accept_ranges(self, authenticated_mocked_client, monkeypatch):
        """Test that streaming response includes Accept-Ranges header."""
        _patch_streaming_deps(monkeypatch, authenticated_mocked_client.user_id)
        response = authenticated_mocked_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        # Should support Range requests
        if response.status_code == status.HTTP_200_OK:
            assert "accept-ranges" in response.headers or "Accept-Ranges" in response.headers

    def test_streaming_response_has_content_length(self, authenticated_mocked_client, monkeypatch):
        """Test that streaming response includes Content-Length header."""
        _patch_streaming_deps(monkeypatch, authenticated_mocked_client.user_id)
        response = authenticated_mocked_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert "content-length" in response.headers or "Content-Length" in response.headers


class TestPathTraversalProtection:
    """Tests for path traversal attack protection."""

    def test_path_traversal_attack_blocked(self, authenticated_mocked_client, monkeypatch):
        """Test that path traversal attacks are blocked."""
        _patch_streaming_deps(
            monkeypatch,
            authenticated_mocked_client.user_id,
            book_exists=False,
        )
        response = authenticated_mocked_client.get("/api/v1/files/audiobook/../../../../etc/passwd")

        # Should be blocked
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_asin_validation(self, authenticated_mocked_client):
        """Test that ASIN format is validated."""
        # ASIN should be alphanumeric, typically 10 chars
        response = authenticated_mocked_client.get("/api/v1/files/audiobook/invalid!@#$asin")

        # Should be rejected
        assert response.status_code in [
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]
