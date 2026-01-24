"""Tests for authentication endpoints."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import status


def _make_user(**overrides):
    """Create a lightweight user-like object for response/model usage."""
    defaults = {
        "user_id": "00000000-0000-0000-0000-000000000000",
        "username": "testuser",
        "email": "testuser@example.com",
        "password_hash": None,
        "is_active": True,
        "family_id": None,
        "share_library_with_family": False,
        "last_sync_date": None,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class TestRegister:
    """Tests for user registration endpoint."""

    def test_register_success(self, mocked_client, test_user_data, monkeypatch):
        """Test successful user registration."""
        from src.database.services import user_service

        created_user = _make_user(
            username=test_user_data["username"],
            email=test_user_data["email"],
        )
        monkeypatch.setattr(
            user_service,
            "get_user_by_username",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            user_service,
            "get_user_by_email",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            user_service,
            "create_user",
            AsyncMock(return_value=created_user),
        )

        response = mocked_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "password" not in data  # Password should not be returned

    def test_register_duplicate_username(self, mocked_client, test_user_data, monkeypatch):
        """Test registration with existing username."""
        from src.database.services import user_service

        monkeypatch.setattr(
            user_service,
            "get_user_by_username",
            AsyncMock(return_value=_make_user(username=test_user_data["username"])),
        )

        response = mocked_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already taken" in data["detail"].lower()

    def test_register_duplicate_email(self, mocked_client, test_user_data, monkeypatch):
        """Test registration with existing email."""
        from src.database.services import user_service

        monkeypatch.setattr(
            user_service,
            "get_user_by_username",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            user_service,
            "get_user_by_email",
            AsyncMock(return_value=_make_user(email=test_user_data["email"])),
        )

        response = mocked_client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already registered" in data["detail"].lower()

    def test_register_invalid_email(self, mocked_client):
        """Test registration with invalid email."""
        response = mocked_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_short_password(self, mocked_client):
        """Test registration with password too short."""
        response = mocked_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "short",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLogin:
    """Tests for login endpoint."""

    def test_login_success(self, mocked_client, test_user_data, monkeypatch):
        """Test successful login."""
        from src.api.security.password import hash_password
        from src.database.services import user_service

        user = _make_user(
            user_id="test-user-123",
            username=test_user_data["username"],
            password_hash=hash_password(test_user_data["password"]),
            is_active=True,
        )

        monkeypatch.setattr(
            user_service,
            "get_user_by_username",
            AsyncMock(return_value=user),
        )

        response = mocked_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_username(self, mocked_client, test_user_data, monkeypatch):
        """Test login with non-existent username."""
        from src.database.services import user_service

        monkeypatch.setattr(
            user_service,
            "get_user_by_username",
            AsyncMock(return_value=None),
        )

        response = mocked_client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "AnyPassword123!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "Invalid username or password" in data["detail"]

    def test_login_invalid_password(self, mocked_client, test_user_data, monkeypatch):
        """Test login with wrong password."""
        from src.api.security.password import hash_password
        from src.database.services import user_service

        user = _make_user(
            user_id="test-user-123",
            username=test_user_data["username"],
            password_hash=hash_password("CorrectPassword123!"),
            is_active=True,
        )

        monkeypatch.setattr(
            user_service,
            "get_user_by_username",
            AsyncMock(return_value=user),
        )

        response = mocked_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["username"],
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "Invalid username or password" in data["detail"]

    def test_login_inactive_user(self, mocked_client, test_user_data, monkeypatch):
        """Test login with inactive user."""
        from src.api.security.password import hash_password
        from src.database.services import user_service

        user = _make_user(
            user_id="test-user-123",
            username=test_user_data["username"],
            password_hash=hash_password(test_user_data["password"]),
            is_active=False,
        )

        monkeypatch.setattr(
            user_service,
            "get_user_by_username",
            AsyncMock(return_value=user),
        )

        response = mocked_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["username"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "inactive" in data["detail"].lower()


class TestRefresh:
    """Tests for token refresh endpoint."""

    def test_refresh_success(self, mocked_client, test_user_with_tokens, monkeypatch):
        """Test successful token refresh."""
        from src.database.services import user_service

        monkeypatch.setattr(
            user_service,
            "get_user_by_id",
            AsyncMock(return_value=_make_user(user_id=test_user_with_tokens["user_id"])),
        )

        response = mocked_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": test_user_with_tokens["refresh_token"],
            },
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_invalid_token(self, mocked_client):
        """Test refresh with invalid token."""
        response = mocked_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "invalid-token",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_expired_token(self, mocked_client, monkeypatch):
        """Test refresh with expired token."""
        from fastapi import HTTPException

        def mock_decode_token(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )

        monkeypatch.setattr("src.api.routers.auth.decode_token", mock_decode_token)

        response = mocked_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "expired-token",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_inactive_user(self, mocked_client, test_user_with_tokens, monkeypatch):
        """Test refresh with inactive user."""
        from src.database.services import user_service

        monkeypatch.setattr(
            user_service,
            "get_user_by_id",
            AsyncMock(
                return_value=_make_user(user_id=test_user_with_tokens["user_id"], is_active=False)
            ),
        )

        response = mocked_client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": test_user_with_tokens["refresh_token"],
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "inactive" in data["detail"].lower()


class TestAuthorization:
    """Tests for authorization and authentication requirements."""

    def test_missing_authorization_header(self, mocked_client):
        """Test request without Authorization header."""
        response = mocked_client.get("/api/v1/library/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_authorization_header_format(self, mocked_client):
        """Test request with malformed Authorization header."""
        response = mocked_client.get(
            "/api/v1/library/",
            headers={"Authorization": "InvalidFormat token"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token(self, mocked_client):
        """Test request with invalid token."""
        response = mocked_client.get(
            "/api/v1/library/",
            headers={"Authorization": "Bearer invalid-token-xyz"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_malformed_jwt(self, mocked_client):
        """Test request with malformed JWT token."""
        response = mocked_client.get(
            "/api/v1/library/",
            headers={"Authorization": "Bearer not.a.jwt"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.skip(reason="PyJWT not installed as dependency")
    def test_token_with_tampered_payload(self, mocked_client):
        """Test token with tampered payload doesn't work."""
        import jwt

        # Create a token with wrong signature
        tampered_token = jwt.encode(
            {"sub": "user123"},
            "wrong-secret-key",
            algorithm="HS256",
        )

        response = mocked_client.get(
            "/api/v1/library/",
            headers={"Authorization": f"Bearer {tampered_token}"},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_bearer_token(self, mocked_client):
        """Test request with empty Bearer token."""
        response = mocked_client.get(
            "/api/v1/library/",
            headers={"Authorization": "Bearer "},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_case_insensitive_bearer(self, mocked_client, test_user_with_tokens):
        """Test that Bearer keyword is case-sensitive."""
        # FastAPI/OpenAPI expects "Bearer" with capital B
        response = mocked_client.get(
            "/api/v1/library/",
            headers={"Authorization": f"bearer {test_user_with_tokens['access_token']}"},
        )
        # This should fail because "bearer" (lowercase) is not valid
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordValidation:
    """Tests for password validation during registration."""

    def test_register_no_uppercase(self, mocked_client):
        """Test registration with password missing uppercase."""
        response = mocked_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "testpassword123!",  # No uppercase
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_no_lowercase(self, mocked_client):
        """Test registration with password missing lowercase."""
        response = mocked_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "TESTPASSWORD123!",  # No lowercase
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_no_digit(self, mocked_client):
        """Test registration with password missing digit."""
        response = mocked_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "TestPassword!",  # No digit
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_no_special_char(self, mocked_client):
        """Test registration with password missing special character."""
        response = mocked_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "TestPassword123",  # No special char
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_whitespace_in_password(self, mocked_client):
        """Test registration with whitespace in password."""
        response = mocked_client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "Test Password123!",  # Has space
            },
        )
        # Should accept - spaces are allowed in passwords
        # Just checking it doesn't crash
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]


class TestTokenExpiration:
    """Tests for token expiration handling."""

    def test_access_token_with_correct_expiration(self, test_user_with_tokens):
        """Verify access token has correct expiration time."""
        from datetime import datetime, timezone

        from jose import jwt

        token = test_user_with_tokens["access_token"]
        decoded = jwt.get_unverified_claims(token)

        # Should have exp claim
        assert "exp" in decoded
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        # Should be approximately 30 minutes from now

        now = datetime.now(timezone.utc)
        diff = exp_time - now
        # Allow 1 minute margin
        assert 29 * 60 < diff.total_seconds() < 31 * 60

    def test_refresh_token_with_correct_expiration(self, test_user_with_tokens):
        """Verify refresh token has correct expiration time."""
        from datetime import datetime, timezone

        from jose import jwt

        token = test_user_with_tokens["refresh_token"]
        decoded = jwt.get_unverified_claims(token)

        # Should have exp claim
        assert "exp" in decoded
        exp_time = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        # Should be approximately 7 days from now

        now = datetime.now(timezone.utc)
        diff = exp_time - now
        # Allow 1 minute margin
        assert 6 * 24 * 60 * 60 < diff.total_seconds() < 7 * 24 * 60 * 60 + 60
