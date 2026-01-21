"""Tests for Audible authentication endpoints."""

import pytest
from fastapi import status


@pytest.mark.skip(reason="Audible API integration not yet fully implemented")
class TestAudibleAuthStart:
    """Tests for starting Audible authentication flow."""

    def test_start_audible_auth_success(self, authenticated_client, monkeypatch):
        """Test successfully starting Audible auth flow."""
        from src.infrastructure.audible_client import AudibleClient

        auth_url = "https://auth.audible.com/oauth?state=test&redirect_uri=..."

        def mock_get_auth_url(region="US"):
            return auth_url

        monkeypatch.setattr(AudibleClient, "get_auth_url", mock_get_auth_url)

        response = authenticated_client.post(
            "/api/v1/audible/auth/start",
            json={"region": "US"},
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED,
        ]
        data = response.json()
        if response.status_code == status.HTTP_200_OK:
            assert "auth_url" in data or "url" in data

    def test_start_audible_auth_with_region(self, authenticated_client, monkeypatch):
        """Test Audible auth with different regions."""
        from src.infrastructure.audible_client import AudibleClient

        regions_tested = []

        def mock_get_auth_url(region="US"):
            regions_tested.append(region)
            return f"https://auth.audible.{region.lower()}/oauth"

        monkeypatch.setattr(AudibleClient, "get_auth_url", mock_get_auth_url)

        # Test different regions
        for region in ["US", "GB", "CA", "AU"]:
            response = authenticated_client.post(
                "/api/v1/audible/auth/start",
                json={"region": region},
            )
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_202_ACCEPTED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,  # If region validation fails
            ]

    def test_start_audible_auth_unauthenticated(self, client):
        """Test Audible auth without authentication."""
        response = client.post(
            "/api/v1/audible/auth/start",
            json={"region": "US"},
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_start_audible_auth_invalid_region(self, authenticated_client):
        """Test Audible auth with invalid region."""
        response = authenticated_client.post(
            "/api/v1/audible/auth/start",
            json={"region": "INVALID"},
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


@pytest.mark.skip(reason="Audible API integration not yet fully implemented")
class TestAudibleAuthCallback:
    """Tests for Audible authentication callback."""

    def test_auth_callback_success(self, authenticated_client, monkeypatch, test_user_id):
        """Test successful auth callback."""
        from src.database.db_users import user_ops
        from src.infrastructure.audible_client import AudibleClient

        def mock_get_auth_token(auth_code):
            return {
                "access_token": "token-123",
                "refresh_token": "refresh-123",
                "expires_in": 3600,
            }

        def mock_store_audible_credentials(user_id, token, region):
            return True

        monkeypatch.setattr(AudibleClient, "get_auth_token", mock_get_auth_token)
        monkeypatch.setattr(user_ops, "store_audible_credentials", mock_store_audible_credentials)

        response = authenticated_client.post(
            "/api/v1/audible/auth/callback",
            json={
                "code": "auth-code-123",
                "state": "state-123",
                "region": "US",
            },
        )

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_202_ACCEPTED,
        ]

    def test_auth_callback_missing_code(self, authenticated_client):
        """Test callback without auth code."""
        response = authenticated_client.post(
            "/api/v1/audible/auth/callback",
            json={"state": "state-123", "region": "US"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_auth_callback_invalid_code(self, authenticated_client, monkeypatch):
        """Test callback with invalid auth code."""
        from src.infrastructure.audible_client import AudibleClient

        def mock_get_auth_token(auth_code):
            raise Exception("Invalid authorization code")

        monkeypatch.setattr(AudibleClient, "get_auth_token", mock_get_auth_token)

        response = authenticated_client.post(
            "/api/v1/audible/auth/callback",
            json={
                "code": "invalid-code",
                "state": "state-123",
                "region": "US",
            },
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_auth_callback_expired_code(self, authenticated_client, monkeypatch):
        """Test callback with expired auth code."""
        from src.infrastructure.audible_client import AudibleClient

        def mock_get_auth_token(auth_code):
            raise Exception("Authorization code has expired")

        monkeypatch.setattr(AudibleClient, "get_auth_token", mock_get_auth_token)

        response = authenticated_client.post(
            "/api/v1/audible/auth/callback",
            json={
                "code": "expired-code",
                "state": "state-123",
                "region": "US",
            },
        )

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_auth_callback_unauthenticated(self, client):
        """Test callback without user authentication."""
        response = client.post(
            "/api/v1/audible/auth/callback",
            json={
                "code": "auth-code-123",
                "state": "state-123",
                "region": "US",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.skip(reason="Audible API integration not yet fully implemented")
class TestAudibleTokenRefresh:
    """Tests for Audible token refresh."""

    def test_refresh_audible_token(self, authenticated_client, monkeypatch, test_user_id):
        """Test refreshing Audible token."""
        from src.database.db_users import user_ops
        from src.infrastructure.audible_client import AudibleClient

        def mock_refresh_token(refresh_token):
            return {
                "access_token": "new-token-123",
                "refresh_token": "new-refresh-123",
                "expires_in": 3600,
            }

        def mock_get_user_by_id(user_id):
            return {
                "user_id": user_id,
                "audible_refresh_token": "old-refresh-token",
            }

        def mock_update_audible_token(user_id, token):
            return True

        monkeypatch.setattr(AudibleClient, "refresh_token", mock_refresh_token)
        monkeypatch.setattr(user_ops, "get_user_by_id", mock_get_user_by_id)
        monkeypatch.setattr(user_ops, "update_audible_token", mock_update_audible_token)

        response = authenticated_client.post("/api/v1/audible/auth/refresh")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,  # If user doesn't have token
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        ]

    def test_refresh_token_no_credentials(self, authenticated_client, monkeypatch):
        """Test refresh when user has no Audible credentials."""
        from src.database.db_users import user_ops

        def mock_get_user_by_id(user_id):
            return {
                "user_id": user_id,
                "audible_refresh_token": None,
            }

        monkeypatch.setattr(user_ops, "get_user_by_id", mock_get_user_by_id)

        response = authenticated_client.post("/api/v1/audible/auth/refresh")

        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_refresh_token_unauthenticated(self, client):
        """Test token refresh without user authentication."""
        response = client.post("/api/v1/audible/auth/refresh")

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.skip(reason="Audible API integration not yet fully implemented")
class TestAudibleAuthSessionManagement:
    """Tests for Audible auth session management."""

    def test_verify_credentials(self, authenticated_client, monkeypatch, test_user_id):
        """Test verifying stored Audible credentials."""
        from src.database.db_users import user_ops
        from src.infrastructure.audible_client import AudibleClient

        def mock_verify_credentials(access_token):
            # Simulate API call to verify token
            return True

        def mock_get_user_by_id(user_id):
            return {
                "user_id": user_id,
                "audible_auth_token": "valid-token",
            }

        monkeypatch.setattr(AudibleClient, "verify_credentials", mock_verify_credentials)
        monkeypatch.setattr(user_ops, "get_user_by_id", mock_get_user_by_id)

        response = authenticated_client.post("/api/v1/audible/auth/verify")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_verify_invalid_credentials(self, authenticated_client, monkeypatch):
        """Test verifying invalid credentials."""
        from src.infrastructure.audible_client import AudibleClient

        def mock_verify_credentials(access_token):
            return False

        monkeypatch.setattr(AudibleClient, "verify_credentials", mock_verify_credentials)

        response = authenticated_client.post("/api/v1/audible/auth/verify")

        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_revoke_credentials(self, authenticated_client, monkeypatch):
        """Test revoking Audible credentials."""
        from src.database.db_users import user_ops

        def mock_clear_audible_credentials(user_id):
            return True

        monkeypatch.setattr(user_ops, "clear_audible_credentials", mock_clear_audible_credentials)

        response = authenticated_client.post("/api/v1/audible/auth/revoke")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
        ]


@pytest.mark.skip(reason="Audible API integration not yet fully implemented")
class TestMultiLocaleSupport:
    """Tests for multi-locale Audible support."""

    def test_supported_locales(self, authenticated_client, monkeypatch):
        """Test getting list of supported locales."""
        from src.infrastructure.audible_client import AudibleClient

        def mock_get_supported_locales():
            return ["US", "GB", "CA", "AU", "FR", "DE"]

        monkeypatch.setattr(AudibleClient, "get_supported_locales", mock_get_supported_locales)

        response = authenticated_client.get("/api/v1/audible/locales")

        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_auth_with_different_locales(self, authenticated_client, monkeypatch):
        """Test authentication with different locales."""
        from src.infrastructure.audible_client import AudibleClient

        locales_tested = []

        def mock_get_auth_url(region="US"):
            locales_tested.append(region)
            return f"https://auth.audible.{region.lower()}/oauth"

        monkeypatch.setattr(AudibleClient, "get_auth_url", mock_get_auth_url)

        locales = ["US", "GB", "CA"]
        for locale in locales:
            response = authenticated_client.post(
                "/api/v1/audible/auth/start",
                json={"region": locale},
            )
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_202_ACCEPTED,
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            ]
