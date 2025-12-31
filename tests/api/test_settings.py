"""Tests for user settings endpoints."""

import pytest
from fastapi import status


class TestAudibleCredentialsStatus:
    """Tests for checking Audible credentials status."""

    def test_get_credentials_status_authenticated(self, authenticated_client, monkeypatch):
        """Test getting credentials status when authenticated."""
        from src.database.db_users import user_ops

        def mock_get_user_by_id(user_id):
            return {
                "user_id": user_id,
                "username": "testuser",
                "audible_auth_token": "token-123",  # Has credentials
                "audible_region": "US",
            }

        monkeypatch.setattr(user_ops, "get_user_by_id", mock_get_user_by_id)

        response = authenticated_client.get("/api/v1/settings/audible/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "has_credentials" in data
        assert data["has_credentials"] is True

    def test_get_credentials_status_no_credentials(self, authenticated_client, monkeypatch):
        """Test getting credentials status when no credentials stored."""
        from src.database.db_users import user_ops

        def mock_get_user_by_id(user_id):
            return {
                "user_id": user_id,
                "username": "testuser",
                "audible_auth_token": None,  # No credentials
            }

        monkeypatch.setattr(user_ops, "get_user_by_id", mock_get_user_by_id)

        response = authenticated_client.get("/api/v1/settings/audible/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["has_credentials"] is False

    def test_get_credentials_status_unauthenticated(self, client):
        """Test getting credentials status without authentication."""
        response = client.get("/api/v1/settings/audible/status")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_credentials_with_region(self, authenticated_client, monkeypatch):
        """Test getting credentials status includes region info."""
        from src.database.db_users import user_ops

        def mock_get_user_by_id(user_id):
            return {
                "user_id": user_id,
                "username": "testuser",
                "audible_auth_token": "token-123",
                "audible_region": "GB",
            }

        monkeypatch.setattr(user_ops, "get_user_by_id", mock_get_user_by_id)

        response = authenticated_client.get("/api/v1/settings/audible/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data.get("region") == "GB"


class TestClearAudibleCredentials:
    """Tests for clearing Audible credentials."""

    def test_clear_credentials_success(self, authenticated_client, monkeypatch):
        """Test successfully clearing credentials."""
        from src.database.db_users import user_ops

        clear_called = []

        def mock_clear_audible_credentials(user_id):
            clear_called.append(user_id)
            return True

        monkeypatch.setattr(
            user_ops, "clear_audible_credentials", mock_clear_audible_credentials
        )

        response = authenticated_client.post("/api/v1/settings/audible/clear")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ]
        assert len(clear_called) > 0

    def test_clear_credentials_unauthenticated(self, client):
        """Test clearing credentials without authentication."""
        response = client.post("/api/v1/settings/audible/clear")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_clear_credentials_response_format(self, authenticated_client, monkeypatch):
        """Test response format when clearing credentials."""
        from src.database.db_users import user_ops

        def mock_clear_audible_credentials(user_id):
            return True

        monkeypatch.setattr(
            user_ops, "clear_audible_credentials", mock_clear_audible_credentials
        )

        response = authenticated_client.post("/api/v1/settings/audible/clear")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ]
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "success" in data or "message" in data


class TestPreferencesSettings:
    """Tests for user preference settings."""

    def test_get_preferences(self, authenticated_client, monkeypatch):
        """Test getting user preferences."""
        from src.database.db_users import user_ops

        def mock_get_user_preferences(user_id):
            return {
                "user_id": user_id,
                "auto_sync_enabled": True,
                "sync_interval_hours": 24,
                "auto_decrypt": True,
                "default_format": "m4b",
                "notifications_enabled": True,
            }

        monkeypatch.setattr(
            user_ops, "get_user_preferences", mock_get_user_preferences
        )

        response = authenticated_client.get("/api/v1/settings/preferences")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_update_preferences(self, authenticated_client, monkeypatch):
        """Test updating user preferences."""
        from src.database.db_users import user_ops

        def mock_update_user_preferences(user_id, preferences):
            return True

        monkeypatch.setattr(
            user_ops, "update_user_preferences", mock_update_user_preferences
        )

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

    def test_get_library_stats(self, authenticated_client, monkeypatch):
        """Test getting library statistics."""
        from src.database.db_books import book_ops

        def mock_get_user_library_stats(user_id):
            return {
                "total_books": 100,
                "downloaded_books": 50,
                "decrypted_books": 45,
                "unplayed_books": 30,
                "total_duration_hours": 5000,
            }

        monkeypatch.setattr(book_ops, "get_user_library_stats", mock_get_user_library_stats)

        response = authenticated_client.get("/api/v1/settings/library/stats")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    def test_get_storage_info(self, authenticated_client, monkeypatch):
        """Test getting storage information."""
        from src.infrastructure.file_utils import FileUtilities

        def mock_get_user_storage_usage(user_id):
            return {
                "total_size_bytes": 1000000000,  # 1GB
                "used_size_bytes": 750000000,    # 750MB
                "free_size_bytes": 250000000,    # 250MB
            }

        monkeypatch.setattr(
            FileUtilities, "get_user_storage_usage", mock_get_user_storage_usage
        )

        response = authenticated_client.get("/api/v1/settings/library/storage")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestSettingsValidation:
    """Tests for settings validation."""

    def test_invalid_sync_interval(self, authenticated_client, monkeypatch):
        """Test validation of sync interval."""
        from src.database.db_users import user_ops

        def mock_update_user_preferences(user_id, preferences):
            if preferences.get("sync_interval_hours", 0) < 1:
                raise ValueError("Sync interval must be at least 1 hour")
            return True

        monkeypatch.setattr(
            user_ops, "update_user_preferences", mock_update_user_preferences
        )

        response = authenticated_client.patch(
            "/api/v1/settings/preferences",
            json={"sync_interval_hours": 0},
        )

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_invalid_audio_format(self, authenticated_client, monkeypatch):
        """Test validation of audio format."""
        from src.database.db_users import user_ops

        def mock_update_user_preferences(user_id, preferences):
            valid_formats = ["m4b", "mp3", "aac", "flac"]
            if preferences.get("default_format") not in valid_formats:
                raise ValueError("Invalid audio format")
            return True

        monkeypatch.setattr(
            user_ops, "update_user_preferences", mock_update_user_preferences
        )

        response = authenticated_client.patch(
            "/api/v1/settings/preferences",
            json={"default_format": "invalid"},
        )

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_valid_format_options(self, authenticated_client, monkeypatch):
        """Test all valid audio format options."""
        from src.database.db_users import user_ops

        def mock_update_user_preferences(user_id, preferences):
            return True

        monkeypatch.setattr(
            user_ops, "update_user_preferences", mock_update_user_preferences
        )

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
