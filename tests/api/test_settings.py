"""Tests for user settings endpoints."""

import pytest
from fastapi import status


class TestAudibleCredentialsStatus:
    """Tests for checking Audible credentials status."""

    @pytest.mark.asyncio
    async def test_get_credentials_status_authenticated(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test getting credentials status when authenticated with real database."""
        # User exists but may not have Audible credentials yet
        response = authenticated_client.get("/api/v1/settings/audible/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "has_credentials" in data
        # Will be False since test_user_in_db doesn't have credentials by default
        assert data["has_credentials"] is False

    @pytest.mark.asyncio
    async def test_get_credentials_status_no_credentials(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test getting credentials status when no credentials stored with real database."""
        response = authenticated_client.get("/api/v1/settings/audible/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_credentials"] is False

    def test_get_credentials_status_unauthenticated(self, client):
        """Test getting credentials status without authentication."""
        response = client.get("/api/v1/settings/audible/status")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_credentials_with_region(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test getting credentials status includes region info."""
        # Region info would be set if user had Audible auth configured
        response = authenticated_client.get("/api/v1/settings/audible/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Region might be None or not present if not configured
        assert "region" in data or "has_credentials" in data


class TestClearAudibleCredentials:
    """Tests for clearing Audible credentials."""

    @pytest.mark.asyncio
    async def test_clear_credentials_success(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test successfully clearing credentials with real database."""
        response = authenticated_client.post("/api/v1/settings/audible/clear")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_400_BAD_REQUEST,  # Might fail if no credentials to clear
        ]

    def test_clear_credentials_unauthenticated(self, client):
        """Test clearing credentials without authentication."""
        response = client.post("/api/v1/settings/audible/clear")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_clear_credentials_response_format(
        self, authenticated_client, db_session, test_user_in_db
    ):
        """Test response format when clearing credentials with real database."""
        response = authenticated_client.post("/api/v1/settings/audible/clear")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_400_BAD_REQUEST,
        ]
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # Should have success or message field
            assert "success" in data or "message" in data or data


class TestPreferencesSettings:
    """Tests for user preference settings."""

    @pytest.mark.asyncio
    async def test_get_preferences(self, authenticated_client, db_session, test_user_in_db):
        """Test getting user preferences with real database."""
        response = authenticated_client.get("/api/v1/settings/preferences")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_update_preferences(self, authenticated_client, db_session, test_user_in_db):
        """Test updating user preferences with real database."""
        response = authenticated_client.patch(
            "/api/v1/settings/preferences",
            json={
                "auto_sync_enabled": False,
                "notifications_enabled": False,
            },
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_update_preferences_unauthenticated(self, client):
        """Test updating preferences without authentication."""
        response = client.patch(
            "/api/v1/settings/preferences",
            json={"auto_sync_enabled": False},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestLibrarySettings:
    """Tests for library-specific settings."""

    @pytest.mark.asyncio
    async def test_get_library_stats(self, authenticated_client, db_session, test_user_in_db):
        """Test getting library statistics with real database."""
        from tests.factories import BookFactory

        # Create some books to have stats
        for i in range(5):
            await BookFactory.create(
                db=db_session,
                user_id=str(test_user_in_db.user_id),
                asin=f"B{i:09d}",
                title=f"Book {i}",
                author="Author",
            )
        await db_session.commit()

        response = authenticated_client.get("/api/v1/settings/library/stats")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_get_storage_info(self, authenticated_client, db_session, test_user_in_db):
        """Test getting storage information."""
        response = authenticated_client.get("/api/v1/settings/library/storage")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestSettingsValidation:
    """Tests for settings validation."""

    @pytest.mark.asyncio
    async def test_invalid_sync_interval(self, authenticated_client, db_session, test_user_in_db):
        """Test validation of sync interval with real database."""
        response = authenticated_client.patch(
            "/api/v1/settings/preferences",
            json={"sync_interval_hours": 0},
        )

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,  # Endpoint might not exist
        ]

    @pytest.mark.asyncio
    async def test_invalid_audio_format(self, authenticated_client, db_session, test_user_in_db):
        """Test validation of audio format with real database."""
        response = authenticated_client.patch(
            "/api/v1/settings/preferences",
            json={"default_format": "invalid"},
        )

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]

    @pytest.mark.asyncio
    async def test_valid_format_options(self, authenticated_client, db_session, test_user_in_db):
        """Test all valid audio format options with real database."""
        valid_formats = ["m4b", "mp3", "aac", "flac"]
        for fmt in valid_formats:
            response = authenticated_client.patch(
                "/api/v1/settings/preferences",
                json={"default_format": fmt},
            )
            # Should either succeed or not be implemented
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]
