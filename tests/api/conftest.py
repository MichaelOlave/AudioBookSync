"""Pytest configuration and fixtures for API tests."""

import pytest
from fastapi.testclient import TestClient
from datetime import timedelta
import uuid

from src.api.main import app
from src.api.security.auth import create_access_token, create_refresh_token
from src.api.security.password import hash_password
from src.database.db_users import user_ops
from src.database.db_books import book_ops


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def test_user_data():
    """Test user credentials."""
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "TestPassword123!",
    }


@pytest.fixture
def test_user_id():
    """Generate a test user ID."""
    return str(uuid.uuid4())


@pytest.fixture
def test_user_with_tokens(test_user_id):
    """Test user with valid JWT tokens."""
    user = {
        "user_id": test_user_id,
        "username": "testuser",
        "email": "testuser@example.com",
        "password_hash": hash_password("TestPassword123!"),
        "is_active": True,
    }

    # Create tokens
    access_token = create_access_token(
        data={"sub": test_user_id},
        expires_delta=timedelta(minutes=30),
    )
    refresh_token = create_refresh_token(
        data={"sub": test_user_id},
    )

    return {
        "user": user,
        "user_id": test_user_id,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "headers": {"Authorization": f"Bearer {access_token}"},
    }


@pytest.fixture
def authenticated_client(client, test_user_with_tokens):
    """Test client with authentication headers."""
    client.headers = test_user_with_tokens["headers"]
    client.user_id = test_user_with_tokens["user_id"]
    client.access_token = test_user_with_tokens["access_token"]
    client.refresh_token = test_user_with_tokens["refresh_token"]
    return client


@pytest.fixture
def test_book_data():
    """Test book data."""
    return {
        "asin": "B084L6Z6M3",
        "title": "Becoming",
        "author": "Michelle Obama",
        "narrator": "Michelle Obama",
        "series_name": None,
        "description": "An intimate, powerful, and inspiring memoir.",
        "rating": 4.8,
        "runtime_min": 1440,
    }


@pytest.fixture
def test_book_with_user(test_user_id, test_book_data):
    """Test book with user association."""
    return {
        **test_book_data,
        "user_id": test_user_id,
        "purchase_date": "2023-01-15",
    }


@pytest.fixture
def test_sync_data():
    """Test sync data."""
    return {
        "sync_type": "full",
    }


# Database fixtures (cleanup after tests)


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    # Cleanup would go here if using real database
    # For now, tests use in-memory database or mocked operations


# Alternative fixtures with mocked database operations


@pytest.fixture
def mock_user_ops(monkeypatch):
    """Mock user database operations."""

    def mock_get_user_by_username(username):
        return None

    def mock_get_user_by_email(email):
        return None

    def mock_create_user_with_password(username, email, password_hash, **kwargs):
        return str(uuid.uuid4())

    def mock_get_user_by_id(user_id):
        return {
            "user_id": user_id,
            "username": "testuser",
            "email": "testuser@example.com",
            "password_hash": hash_password("TestPassword123!"),
            "is_active": True,
            "created_at": None,
            "updated_at": None,
        }

    monkeypatch.setattr(user_ops, "get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr(user_ops, "get_user_by_email", mock_get_user_by_email)
    monkeypatch.setattr(
        user_ops, "create_user_with_password", mock_create_user_with_password
    )
    monkeypatch.setattr(user_ops, "get_user_by_id", mock_get_user_by_id)

    return user_ops


@pytest.fixture
def mock_book_ops(monkeypatch, test_user_id):
    """Mock book database operations."""

    def mock_get_user_books(user_id):
        if user_id == test_user_id:
            return [
                {
                    "asin": "B084L6Z6M3",
                    "title": "Becoming",
                    "author": "Michelle Obama",
                    "user_id": user_id,
                    "purchase_date": "2023-01-15",
                    "runtime_min": 1440,
                    "rating": 4.8,
                    "is_downloaded": True,
                    "is_decrypted": True,
                    "download_path": "/audiobooks/downloaded/B084L6Z6M3.m4b",
                    "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                    "created_at": None,
                    "updated_at": None,
                }
            ]
        return []

    def mock_get_book_by_asin(asin):
        if asin == "B084L6Z6M3":
            return {
                "asin": asin,
                "title": "Becoming",
                "author": "Michelle Obama",
                "user_id": test_user_id,
                "purchase_date": "2023-01-15",
                "runtime_min": 1440,
                "rating": 4.8,
                "is_downloaded": True,
                "is_decrypted": True,
                "download_path": "/audiobooks/downloaded/B084L6Z6M3.m4b",
                "decrypted_path": "/audiobooks/decrypted/B084L6Z6M3.m4a",
                "created_at": None,
                "updated_at": None,
            }
        return None

    def mock_add_book(asin, user_id, title, **kwargs):
        return True

    def mock_remove_book(asin):
        return True

    monkeypatch.setattr(book_ops, "get_user_books", mock_get_user_books)
    monkeypatch.setattr(book_ops, "get_book_by_asin", mock_get_book_by_asin)
    monkeypatch.setattr(book_ops, "add_book", mock_add_book)
    monkeypatch.setattr(book_ops, "remove_book", mock_remove_book)

    return book_ops
