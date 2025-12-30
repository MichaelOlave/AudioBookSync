"""Tests for authentication endpoints."""

import pytest
from fastapi import status


class TestRegister:
    """Tests for user registration endpoint."""

    def test_register_success(self, client, test_user_data, mock_user_ops):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert "password" not in data  # Password should not be returned

    def test_register_duplicate_username(self, client, test_user_data, monkeypatch):
        """Test registration with existing username."""
        from src.database.db_users import user_ops

        def mock_get_user_by_username(username):
            return {"user_id": "existing", "username": username}

        monkeypatch.setattr(user_ops, "get_user_by_username", mock_get_user_by_username)

        response = client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already taken" in data["detail"].lower()

    def test_register_duplicate_email(self, client, test_user_data, monkeypatch):
        """Test registration with existing email."""
        from src.database.db_users import user_ops

        def mock_get_user_by_email(email):
            return {"user_id": "existing", "email": email}

        def mock_get_user_by_username(username):
            return None

        monkeypatch.setattr(user_ops, "get_user_by_username", mock_get_user_by_username)
        monkeypatch.setattr(user_ops, "get_user_by_email", mock_get_user_by_email)

        response = client.post(
            "/api/v1/auth/register",
            json=test_user_data,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already registered" in data["detail"].lower()

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "password": "TestPassword123!",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_short_password(self, client):
        """Test registration with password too short."""
        response = client.post(
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

    def test_login_success(self, client, test_user_data, monkeypatch):
        """Test successful login."""
        from src.database.db_users import user_ops
        from src.api.security.password import hash_password

        user = {
            "user_id": "test-user-123",
            "username": test_user_data["username"],
            "password_hash": hash_password(test_user_data["password"]),
            "is_active": True,
        }

        def mock_get_user_by_username(username):
            if username == test_user_data["username"]:
                return user
            return None

        monkeypatch.setattr(user_ops, "get_user_by_username", mock_get_user_by_username)

        response = client.post(
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

    def test_login_invalid_username(self, client, test_user_data, monkeypatch):
        """Test login with non-existent username."""
        from src.database.db_users import user_ops

        def mock_get_user_by_username(username):
            return None

        monkeypatch.setattr(user_ops, "get_user_by_username", mock_get_user_by_username)

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "AnyPassword123!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "Invalid username or password" in data["detail"]

    def test_login_invalid_password(self, client, test_user_data, monkeypatch):
        """Test login with wrong password."""
        from src.database.db_users import user_ops
        from src.api.security.password import hash_password

        user = {
            "user_id": "test-user-123",
            "username": test_user_data["username"],
            "password_hash": hash_password("CorrectPassword123!"),
            "is_active": True,
        }

        def mock_get_user_by_username(username):
            if username == test_user_data["username"]:
                return user
            return None

        monkeypatch.setattr(user_ops, "get_user_by_username", mock_get_user_by_username)

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user_data["username"],
                "password": "WrongPassword123!",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "Invalid username or password" in data["detail"]

    def test_login_inactive_user(self, client, test_user_data, monkeypatch):
        """Test login with inactive user."""
        from src.database.db_users import user_ops
        from src.api.security.password import hash_password

        user = {
            "user_id": "test-user-123",
            "username": test_user_data["username"],
            "password_hash": hash_password(test_user_data["password"]),
            "is_active": False,  # Inactive user
        }

        def mock_get_user_by_username(username):
            if username == test_user_data["username"]:
                return user
            return None

        monkeypatch.setattr(user_ops, "get_user_by_username", mock_get_user_by_username)

        response = client.post(
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

    def test_refresh_success(self, client, test_user_with_tokens, monkeypatch):
        """Test successful token refresh."""
        from src.database.db_users import user_ops

        def mock_get_user_by_id(user_id):
            return {
                "user_id": user_id,
                "is_active": True,
            }

        monkeypatch.setattr(user_ops, "get_user_by_id", mock_get_user_by_id)

        response = client.post(
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

    def test_refresh_invalid_token(self, client):
        """Test refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "invalid-token",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_expired_token(self, client, monkeypatch):
        """Test refresh with expired token."""
        from src.api.security.auth import decode_token

        def mock_decode_token(token):
            raise Exception("Token expired")

        monkeypatch.setattr("src.api.routers.auth.decode_token", mock_decode_token)

        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "expired-token",
            },
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
