"""Integration tests for new SQLAlchemy services.

These tests verify that all endpoints work correctly with the new async services.
Requires a running PostgreSQL database and alembic migrations applied.

Run with:
    pytest tests/integration_test_new_services.py -v
"""

import pytest
import asyncio
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.api.main import create_app
from src.database.engine import get_db_session
from src.database.models import Base
from src.database.services import (
    user_service,
    book_service,
    download_service,
    sync_service,
    error_service,
    metadata_service,
)
from src.core.config import Config


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    # Use test database URL
    test_db_url = Config.DATABASE_URL.replace("audiobooksync", "audiobooksync_test")
    test_db_url = test_db_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(
        test_db_url,
        echo=False,
        poolclass=__import__("sqlalchemy.pool", fromlist=["NullPool"]).NullPool,
    )

    yield engine

    await engine.dispose()


@pytest.fixture(scope="session")
async def test_db_session(test_engine):
    """Create test database session."""
    TestSessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session = TestSessionLocal()
    yield session
    await session.close()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def app_with_test_db(test_db_session):
    """Create FastAPI app with test database."""
    app = create_app()

    # Override get_db_session dependency
    async def override_get_db():
        yield test_db_session

    from src.database.engine import get_db_session

    app.dependency_overrides[get_db_session] = override_get_db

    yield app

    app.dependency_overrides.clear()


@pytest.fixture
async def client(app_with_test_db):
    """Create async test client."""
    async with AsyncClient(app=app_with_test_db, base_url="http://test") as client:
        yield client


# ============================================================================
# USER SERVICE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_user(test_db_session):
    """Test creating a user with user_service."""
    user = await user_service.create_user(
        db=test_db_session,
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password_123",
    )

    assert user is not None
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.password_hash == "hashed_password_123"
    assert user.is_active is True
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_get_user_by_username(test_db_session):
    """Test getting user by username."""
    await user_service.create_user(
        db=test_db_session,
        username="john_doe",
        email="john@example.com",
        password_hash="hashed123",
    )
    await test_db_session.commit()

    user = await user_service.get_user_by_username(test_db_session, "john_doe")

    assert user is not None
    assert user.username == "john_doe"
    assert user.email == "john@example.com"


@pytest.mark.asyncio
async def test_get_user_by_email(test_db_session):
    """Test getting user by email."""
    await user_service.create_user(
        db=test_db_session,
        username="jane_doe",
        email="jane@example.com",
        password_hash="hashed456",
    )
    await test_db_session.commit()

    user = await user_service.get_user_by_email(test_db_session, "jane@example.com")

    assert user is not None
    assert user.username == "jane_doe"
    assert user.email == "jane@example.com"


@pytest.mark.asyncio
async def test_update_user_password(test_db_session):
    """Test updating user password."""
    user = await user_service.create_user(
        db=test_db_session,
        username="pwd_test",
        email="pwd@example.com",
        password_hash="old_hash",
    )
    await test_db_session.commit()

    success = await user_service.update_user_password(
        test_db_session,
        user.user_id,
        "new_hash",
    )
    await test_db_session.commit()

    assert success is True

    updated_user = await user_service.get_user_by_id(test_db_session, str(user.user_id))
    assert updated_user.password_hash == "new_hash"


# ============================================================================
# BOOK SERVICE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_add_book(test_db_session):
    """Test adding a book with book_service."""
    user = await user_service.create_user(
        db=test_db_session,
        username="book_owner",
        email="owner@example.com",
        password_hash="hash123",
    )
    await test_db_session.commit()

    success = await book_service.add_book(
        db=test_db_session,
        asin="B001",
        user_id=str(user.user_id),
        title="The Stand",
        author="Stephen King",
        narrator="Grover Gardner",
        runtime_min=1152,
        rating=4.8,
    )

    assert success is True
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_get_book_by_asin(test_db_session):
    """Test getting book by ASIN."""
    user = await user_service.create_user(
        db=test_db_session,
        username="reader",
        email="reader@example.com",
        password_hash="hash456",
    )
    await test_db_session.commit()

    await book_service.add_book(
        db=test_db_session,
        asin="B002",
        user_id=str(user.user_id),
        title="Misery",
        author="Stephen King",
    )
    await test_db_session.commit()

    book = await book_service.get_book_by_asin(test_db_session, "B002")

    assert book is not None
    assert book.asin == "B002"
    assert book.title == "Misery"


@pytest.mark.asyncio
async def test_get_books_by_user(test_db_session):
    """Test getting all books for a user."""
    user = await user_service.create_user(
        db=test_db_session,
        username="collector",
        email="collector@example.com",
        password_hash="hash789",
    )
    await test_db_session.commit()

    # Add multiple books
    for i in range(3):
        await book_service.add_book(
            db=test_db_session,
            asin=f"B{i:03d}",
            user_id=str(user.user_id),
            title=f"Book {i}",
            author="Author",
        )
    await test_db_session.commit()

    books = await book_service.get_books_by_user(test_db_session, str(user.user_id))

    assert len(books) == 3


# ============================================================================
# DOWNLOAD SERVICE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_download_status(test_db_session):
    """Test creating download status."""
    user = await user_service.create_user(
        db=test_db_session,
        username="downloader",
        email="down@example.com",
        password_hash="hash000",
    )
    await test_db_session.commit()

    await book_service.add_book(
        db=test_db_session,
        asin="B_DL01",
        user_id=str(user.user_id),
        title="Download Test",
    )
    await test_db_session.commit()

    download = await download_service.create_download_status(
        db=test_db_session,
        asin="B_DL01",
        status="pending",
    )

    assert download is not None
    assert download.asin == "B_DL01"
    assert download.status == "pending"
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_download_workflow(test_db_session):
    """Test complete download workflow."""
    user = await user_service.create_user(
        db=test_db_session,
        username="workflow_user",
        email="workflow@example.com",
        password_hash="workflow_hash",
    )
    await test_db_session.commit()

    await book_service.add_book(
        db=test_db_session,
        asin="B_WF01",
        user_id=str(user.user_id),
        title="Workflow Test",
    )
    await test_db_session.commit()

    # Create download
    download = await download_service.create_download_status(
        db=test_db_session,
        asin="B_WF01",
    )
    await test_db_session.commit()

    # Start download
    await download_service.start_download(test_db_session, download.download_id)
    await test_db_session.commit()

    # Complete download
    await download_service.complete_download(
        test_db_session,
        download.download_id,
        download_path="/path/to/file.aax",
        file_size_bytes=1000000,
    )
    await test_db_session.commit()

    # Verify
    updated = await download_service.get_download_by_id(
        test_db_session, download.download_id
    )
    assert updated.status == "completed"
    assert updated.download_path == "/path/to/file.aax"


# ============================================================================
# SYNC SERVICE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_sync_history(test_db_session):
    """Test creating sync history."""
    user = await user_service.create_user(
        db=test_db_session,
        username="syncer",
        email="sync@example.com",
        password_hash="sync_hash",
    )
    await test_db_session.commit()

    sync = await sync_service.create_sync_history(
        db=test_db_session,
        user_id=user.user_id,
        sync_type="full",
    )

    assert sync is not None
    assert sync.status == "in_progress"
    assert sync.sync_type == "full"
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_complete_sync(test_db_session):
    """Test completing a sync."""
    user = await user_service.create_user(
        db=test_db_session,
        username="sync_completer",
        email="sync_complete@example.com",
        password_hash="sync_complete_hash",
    )
    await test_db_session.commit()

    sync = await sync_service.create_sync_history(
        db=test_db_session,
        user_id=user.user_id,
        sync_type="incremental",
    )
    await test_db_session.commit()

    success = await sync_service.complete_sync(
        test_db_session,
        sync.sync_id,
        books_found=10,
        books_added=3,
        books_removed=1,
        books_downloaded=5,
        books_decrypted=4,
        errors_count=0,
    )
    await test_db_session.commit()

    assert success is True

    updated_sync = await sync_service.get_sync_by_id(test_db_session, sync.sync_id)
    assert updated_sync.status == "completed"
    assert updated_sync.books_found == 10


# ============================================================================
# ERROR SERVICE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_log_error(test_db_session):
    """Test logging an error."""
    error = await error_service.log_error(
        db=test_db_session,
        error_type="download_error",
        error_message="Connection timeout",
        error_code="TIMEOUT",
        severity="error",
    )

    assert error is not None
    assert error.error_type == "download_error"
    assert error.error_message == "Connection timeout"
    assert error.severity == "error"
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_resolve_error(test_db_session):
    """Test resolving an error."""
    error = await error_service.log_error(
        db=test_db_session,
        error_type="api_error",
        error_message="API rate limit exceeded",
        severity="warning",
    )
    await test_db_session.commit()

    success = await error_service.resolve_error(
        test_db_session,
        error.error_id,
        resolution_notes="Retried after 1 minute",
    )
    await test_db_session.commit()

    assert success is True

    resolved_error = await error_service.get_error_by_id(test_db_session, error.error_id)
    assert resolved_error.resolved is True


# ============================================================================
# METADATA SERVICE TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_create_contributor(test_db_session):
    """Test creating a contributor."""
    contributor = await metadata_service.create_contributor(
        db=test_db_session,
        name="Stephen King",
        contributor_type="author",
    )

    assert contributor is not None
    assert contributor.name == "Stephen King"
    assert contributor.type == "author"
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_create_media_info(test_db_session):
    """Test creating media info."""
    user = await user_service.create_user(
        db=test_db_session,
        username="media_user",
        email="media@example.com",
        password_hash="media_hash",
    )
    await test_db_session.commit()

    await book_service.add_book(
        db=test_db_session,
        asin="B_MEDIA01",
        user_id=str(user.user_id),
        title="Media Test",
    )
    await test_db_session.commit()

    media = await metadata_service.create_media_info(
        db=test_db_session,
        asin="B_MEDIA01",
        codec="AAC",
        bitrate=128000,
        duration_ms=3600000,
    )

    assert media is not None
    assert media.asin == "B_MEDIA01"
    assert media.codec == "AAC"
    await test_db_session.commit()


@pytest.mark.asyncio
async def test_reading_progress(test_db_session):
    """Test reading progress tracking."""
    user = await user_service.create_user(
        db=test_db_session,
        username="reader_user",
        email="reader_prog@example.com",
        password_hash="reader_hash",
    )
    await test_db_session.commit()

    await book_service.add_book(
        db=test_db_session,
        asin="B_READ01",
        user_id=str(user.user_id),
        title="Progress Test",
    )
    await test_db_session.commit()

    progress = await metadata_service.create_reading_progress(
        db=test_db_session,
        asin="B_READ01",
        user_id=user.user_id,
    )

    assert progress is not None
    await test_db_session.commit()

    # Update progress
    success = await metadata_service.update_reading_progress(
        test_db_session,
        "B_READ01",
        user.user_id,
        percent_complete=50,
        position_ms=1800000,
    )
    await test_db_session.commit()

    assert success is True

    updated = await metadata_service.get_reading_progress(
        test_db_session,
        "B_READ01",
        user.user_id,
    )
    assert updated.percent_complete == 50


# ============================================================================
# API ENDPOINT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Test health check endpoint."""
    response = await client.get("/health")

    assert response.status_code == 200


# Run tests with: pytest tests/integration_test_new_services.py -v
