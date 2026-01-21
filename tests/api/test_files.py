"""Tests for audiobook file streaming endpoints."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status

from tests.factories import BookFactory


class TestStreamAudiobook:
    """Tests for stream audiobook endpoint."""

    @pytest.mark.asyncio
    async def test_stream_audiobook_success(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test successful audiobook streaming with real database."""
        # Create a book in the database
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Test Book",
        )
        await db_session.commit()

        # Mock file existence and size
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.stat.return_value = MagicMock(st_size=1024000)

        with patch("src.api.routers.files.Path", return_value=mock_path):
            response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["Accept-Ranges"] == "bytes"

    @pytest.mark.asyncio
    async def test_stream_audiobook_with_range(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test audiobook streaming with Range header using real database."""
        # Create a book in the database
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Test Book",
        )
        await db_session.commit()

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

    def test_stream_audiobook_not_found(self, authenticated_client):
        """Test streaming non-existent audiobook."""
        response = authenticated_client.get("/api/v1/files/audiobook/NOTEXIST")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_stream_audiobook_unauthorized(self, authenticated_client, db_session):
        """Test streaming another user's audiobook with real database."""
        from tests.factories import UserFactory

        # Create another user with a book
        other_user = await UserFactory.create(
            db=db_session, username="otheruser", email="other@example.com"
        )

        await BookFactory.create(
            db=db_session, user_id=str(other_user.user_id), asin="B084L6Z6M3", title="Test Book"
        )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_stream_audiobook_file_not_available(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test streaming when decrypted file is not available with real database."""
        # Create a book without decrypted_path
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Test Book",
        )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        # Should return 404 since file is not available
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream_audiobook_unauthenticated(self, client):
        """Test audiobook streaming without authentication."""
        response = client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_stream_audiobook_invalid_range(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test streaming with invalid Range header using real database."""
        # Create a book in the database
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Test Book",
        )
        await db_session.commit()

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

    @pytest.mark.asyncio
    async def test_stream_audiobook_minio_with_object_key(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test streaming from MinIO when object_key exists using real database."""
        # Create a book in the database
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Test Book",
        )
        await db_session.commit()

        def mock_get_object_key_for_asin(user_id, asin):
            return "decrypted/test-book.m4b"

        # Mock StorageService
        mock_storage_service = MagicMock()
        mock_storage_service.stream_file.return_value = b"audio data"

        with patch("src.api.routers.files._get_object_key_for_asin", mock_get_object_key_for_asin):
            with patch("src.api.routers.files.StorageService", return_value=mock_storage_service):
                response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_stream_audiobook_fallback_to_filesystem_when_no_object_key(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test fallback to filesystem streaming when object_key is NULL using real database."""
        # Create a book in the database
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Test Book",
        )
        await db_session.commit()

        def mock_get_object_key_for_asin(user_id, asin):
            return None  # No object_key, should use filesystem

        # Mock file
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.stat.return_value = MagicMock(st_size=1024000)

        with patch("src.api.routers.files._get_object_key_for_asin", mock_get_object_key_for_asin):
            with patch("src.api.routers.files.Path", return_value=mock_path):
                response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        assert response.status_code == status.HTTP_200_OK
        assert response.headers["Accept-Ranges"] == "bytes"

    @pytest.mark.asyncio
    async def test_stream_audiobook_minio_with_range_header(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test HTTP Range requests work with MinIO streaming using real database."""
        # Create a book in the database
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Test Book",
        )
        await db_session.commit()

        def mock_get_object_key_for_asin(user_id, asin):
            return "decrypted/test-book.m4b"

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

    @pytest.mark.asyncio
    async def test_stream_audiobook_minio_fallback_on_empty_response(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test fallback to filesystem when MinIO streaming returns empty using real database."""
        # Create a book in the database
        await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin="B084L6Z6M3",
            title="Test Book",
        )
        await db_session.commit()

        def mock_get_object_key_for_asin(user_id, asin):
            return "decrypted/test-book.m4b"

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

    @pytest.mark.asyncio
    async def test_stream_audiobook_user_ownership_enforced(self, authenticated_client, db_session):
        """Test user ownership verification still enforced with MinIO streaming using real database."""
        from tests.factories import UserFactory

        # Create another user with a book
        other_user = await UserFactory.create(
            db=db_session, username="otheruser", email="other@example.com"
        )

        await BookFactory.create(
            db=db_session, user_id=str(other_user.user_id), asin="B084L6Z6M3", title="Test Book"
        )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/files/audiobook/B084L6Z6M3")

        # Should be forbidden even if object_key exists (ownership check happens first)
        assert response.status_code == status.HTTP_403_FORBIDDEN
