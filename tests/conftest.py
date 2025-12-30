"""Pytest configuration and shared fixtures for all tests."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    test_env = {
        "AUDIBLE_AUTH_FILE": "/tmp/auth.json",
        "AUDIBLE_ACTIVATION_BYTES": "1234567890abcdef",
        "DOWNLOAD_DIR": "/tmp/downloads",
        "DECRYPTED_DIR": "/tmp/decrypted",
        "LOG_DIR": "/tmp/logs",
        "AUDIBLE_NUM_RESULTS": "100",
        "DATABASE_URL": "postgresql://test:test@localhost/audibooksync_test",
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    return test_env


@pytest.fixture
def mock_db_pool():
    """Mock database pool for testing."""
    pool_mock = MagicMock()
    pool_mock.getconn = MagicMock(return_value=MagicMock())
    pool_mock.putconn = MagicMock()
    return pool_mock


@pytest.fixture
def mock_db_connection():
    """Mock database connection for testing."""
    conn = MagicMock()
    conn.cursor = MagicMock(return_value=MagicMock())
    conn.commit = MagicMock()
    conn.rollback = MagicMock()
    conn.close = MagicMock()
    return conn


@pytest.fixture
def mock_cursor():
    """Mock database cursor for testing."""
    cursor = MagicMock()
    cursor.execute = MagicMock()
    cursor.fetchone = MagicMock(return_value=None)
    cursor.fetchall = MagicMock(return_value=[])
    cursor.close = MagicMock()
    return cursor


@pytest.fixture
def sample_book_data():
    """Sample book data for testing."""
    return {
        "asin": "B001ABC123",
        "title": "Test Audiobook",
        "author": "Test Author",
        "purchase_date": "2023-01-01",
        "runtime_min": 600,
        "cover_url": "https://example.com/cover.jpg",
        "narrators": ["Test Narrator"],
        "language": "en",
        "publisher": "Test Publisher",
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "auth_file_path": "/tmp/auth.json",
        "activation_bytes": "1234567890abcdef",
    }


@pytest.fixture
def sample_sync_data():
    """Sample sync data for testing."""
    return {
        "user_id": "test-user-id",
        "sync_type": "full",
        "status": "in_progress",
    }


@pytest.fixture
def mock_audible_book():
    """Mock Audible book object for testing."""
    return {
        "asin": "B001ABC123",
        "title": "Test Audiobook",
        "author": "Test Author",
        "purchase_date": "2023-01-01",
        "runtime_length_min": 600,
        "cover_url": "https://example.com/cover.jpg",
        "narrators": [{"name": "Test Narrator"}],
        "language": "en",
        "publisher_name": "Test Publisher",
    }


@pytest.fixture
def mock_subprocess_result():
    """Mock subprocess result for testing."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = "Success"
    result.stderr = ""
    return result


# Marks for test organization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "db: mark test as database test")
