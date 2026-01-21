"""Pytest configuration and shared fixtures for all tests."""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.database.models.base import Base
from src.database.services import book_service, sync_service, user_service


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_async_engine():
    """Create async test database engine.

    Uses postgresql+asyncpg with a test database.
    """
    # Get test database URL - use separate test database
    test_db_url = os.getenv(
        "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/audibooksync_test"
    )

    engine = create_async_engine(
        test_db_url,
        echo=False,
        future=True,
        poolclass=NullPool,  # No connection pooling for tests
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_async_engine):
    """Create async database session for each test.

    Provides a fresh session for each test and rolls back after completion.
    """
    async_session = async_sessionmaker(
        test_async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()  # Clean up after test


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


# ============================================================================
# Async ORM Test Factories (using real database)
# ============================================================================


@pytest.fixture
async def test_user(db_session, sample_user_data):
    """Create a test user in the database using ORM.

    Returns the created User ORM object.
    """
    user = await user_service.create_user(
        db=db_session,
        username=sample_user_data["username"],
        email=sample_user_data["email"],
        auth_file_path=sample_user_data["auth_file_path"],
        activation_bytes=sample_user_data["activation_bytes"],
    )
    await db_session.commit()
    return user


@pytest.fixture
async def test_book(db_session, test_user, sample_book_data):
    """Create a test book in the database using ORM.

    Returns the created Book ORM object.
    """
    success = await book_service.add_book(
        db=db_session,
        asin=sample_book_data["asin"],
        user_id=str(test_user.user_id),
        title=sample_book_data["title"],
        author=sample_book_data["author"],
        runtime_min=sample_book_data["runtime_min"],
        purchase_date=sample_book_data["purchase_date"],
    )
    if success:
        await db_session.commit()
        return await book_service.get_book_by_asin(db=db_session, asin=sample_book_data["asin"])
    return None


@pytest.fixture
async def test_sync(db_session, test_user, sample_sync_data):
    """Create a test sync record in the database using ORM.

    Returns the created SyncHistory ORM object.
    """
    sync_history = await sync_service.create_sync_history(
        db=db_session,
        user_id=test_user.user_id,
        sync_type=sample_sync_data["sync_type"],
    )
    await db_session.commit()
    return sync_history


# ============================================================================
# Marks for test organization
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "db: mark test as database test")
