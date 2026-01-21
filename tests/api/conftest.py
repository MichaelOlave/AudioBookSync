"""Pytest configuration and fixtures for API tests."""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.main import app
from src.api.security.auth import create_access_token, create_refresh_token
from src.api.security.password import hash_password
from src.database.services import book_service, user_service
from tests.factories import BookFactory, UserFactory


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
    return str(uuid4())


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
def authenticated_client(client, test_user_with_tokens, mock_user_ops):
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
def test_book_response_data(test_book_data):
    """Test book data with datetime fields for response mocks."""
    return {
        **test_book_data,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
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


# ============================================================================
# ORM-Based Database Fixtures
# ============================================================================


@pytest.fixture
async def test_user_in_db(db_session: AsyncSession, test_user_id: str):
    """Create a real test user in database using ORM.

    For use in async tests that need a real database user.
    """
    user = await UserFactory.create(
        db=db_session,
        username="testuser",
        email="testuser@example.com",
    )
    await db_session.commit()
    return user


@pytest.fixture
async def test_book_in_db(db_session: AsyncSession, test_user_in_db):
    """Create a real test book in database using ORM.

    For use in async tests that need a real database book.
    """
    book = await BookFactory.create(
        db=db_session,
        user_id=str(test_user_in_db.user_id),
        asin="B084L6Z6M3",
        title="Becoming",
        author="Michelle Obama",
        narrator="Michelle Obama",
    )
    await db_session.commit()
    return book


# Database cleanup fixtures (cleanup after tests)


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    # Cleanup would go here if using real database
    # For now, tests use in-memory database or mocked operations


# ============================================================================
# Legacy Fixtures with Mocked Database Operations (for backward compatibility)
# ============================================================================


@pytest.fixture
def mock_user_ops(monkeypatch):
    """Mock user ORM service for tests.

    NOTE: This is a legacy fixture. For new tests, use test_user_in_db with
    async tests, or implement service mocking directly.
    """
    from unittest.mock import AsyncMock

    mock_get_user_by_username = AsyncMock(return_value=None)
    mock_get_user_by_email = AsyncMock(return_value=None)
    mock_get_user_by_id = AsyncMock(return_value=None)

    monkeypatch.setattr(user_service, "get_user_by_username", mock_get_user_by_username)
    monkeypatch.setattr(user_service, "get_user_by_email", mock_get_user_by_email)
    monkeypatch.setattr(user_service, "get_user_by_id", mock_get_user_by_id)

    return user_service


@pytest.fixture
def mock_book_ops(monkeypatch, test_user_id):
    """Mock book ORM service for tests.

    NOTE: This is a legacy fixture. For new tests, use test_book_in_db with
    async tests, or implement service mocking directly.
    """
    from unittest.mock import AsyncMock, MagicMock

    now = datetime.now()

    # Create mock book ORM object
    mock_book = MagicMock()
    mock_book.asin = "B084L6Z6M3"
    mock_book.title = "Becoming"
    mock_book.author = "Michelle Obama"
    mock_book.user_id = test_user_id
    mock_book.purchase_date = "2023-01-15"
    mock_book.runtime_min = 1440
    mock_book.rating = 4.8
    mock_book.is_downloaded = True
    mock_book.is_decrypted = True
    mock_book.download_path = "/audiobooks/downloaded/B084L6Z6M3.m4b"
    mock_book.decrypted_path = "/audiobooks/decrypted/B084L6Z6M3.m4a"
    mock_book.created_at = now
    mock_book.updated_at = now

    mock_get_books_by_user = AsyncMock(return_value=[mock_book])
    mock_get_book_by_asin = AsyncMock(return_value=mock_book)
    mock_add_book = AsyncMock(return_value=True)
    mock_delete_book = AsyncMock(return_value=True)

    monkeypatch.setattr(book_service, "get_books_by_user", mock_get_books_by_user)
    monkeypatch.setattr(book_service, "get_book_by_asin", mock_get_book_by_asin)
    monkeypatch.setattr(book_service, "add_book", mock_add_book)
    monkeypatch.setattr(book_service, "delete_book", mock_delete_book)

    return book_service
