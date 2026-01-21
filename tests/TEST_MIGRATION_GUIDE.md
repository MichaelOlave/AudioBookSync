# Test Migration Guide: From Monkeypatch to Async ORM

This guide explains how to migrate tests from using monkeypatch mocks to using real async ORM fixtures.

## Overview

The test infrastructure has been modernized to use async SQLAlchemy ORM services instead of mocking with monkeypatch. This provides:

- **Real database testing** - Tests use actual PostgreSQL database (test instance)
- **Type safety** - ORM objects with proper type hints
- **Comprehensive coverage** - Test actual ORM behavior, relationships, and constraints
- **Better error detection** - Database constraints and validation work as in production

## New Test Fixtures

### Async Database Fixtures

#### `db_session`
Provides an async database session for each test with automatic rollback.

```python
@pytest.mark.asyncio
async def test_create_user(db_session):
    user = await user_service.create_user(
        db=db_session,
        username="testuser",
        email="test@example.com"
    )
    await db_session.commit()
    assert user.username == "testuser"
```

### Test Data Factories

Located in `tests/factories.py`, these provide fluent factory methods for creating test data.

#### UserFactory

```python
# Simple user creation
user = await UserFactory.create(
    db=db_session,
    username="testuser",
    email="test@example.com"
)

# User with Audible auth
user = await UserFactory.create_with_auth_json(
    db=db_session,
    username="testuser",
    auth_json={"device_info": {...}},
    activation_bytes="1234567890abcdef"
)
```

#### BookFactory

```python
# Simple book creation
book = await BookFactory.create(
    db=db_session,
    user_id=str(user.user_id),
    asin="B084L6Z6M3",
    title="Test Book",
    author="Test Author"
)

# Book with full metadata (7 tables populated)
book = await BookFactory.create_with_metadata(
    db=db_session,
    user_id=str(user.user_id),
    asin="B084L6Z6M3",
    title="Test Book",
    book_data={
        "authors": [{"name": "Test Author", "type": "author"}],
        "narrators": [{"name": "Test Narrator", "type": "narrator"}],
        "media_info": {"codec": "AAC", "bitrate": 128}
    }
)
```

#### SyncFactory

```python
# Create sync record
sync = await SyncFactory.create(
    db=db_session,
    user_id=str(user.user_id),
    sync_type="full"
)

# Create completed sync with stats
sync = await SyncFactory.create_completed(
    db=db_session,
    user_id=str(user.user_id),
    books_found=10,
    books_added=10,
    books_downloaded=8,
    books_decrypted=5
)
```

#### MetadataFactory

```python
# Add contributor
contributor = await MetadataFactory.create_contributor(
    db=db_session,
    name="Test Author",
    contributor_type="author"
)

# Add media info
await MetadataFactory.add_media_info(
    db=db_session,
    asin="B084L6Z6M3",
    codec="AAC",
    bitrate=128
)

# Add custom metadata
await MetadataFactory.add_custom_metadata(
    db=db_session,
    asin="B084L6Z6M3",
    key="custom_field",
    value={"nested": "value"}
)

# Add badge
await MetadataFactory.add_badge(
    db=db_session,
    asin="B084L6Z6M3",
    badge_name="bestseller"
)
```

## Migration Examples

### Before (Monkeypatch)

```python
def test_get_library(authenticated_client, mock_book_ops):
    """Test library endpoint with mocked database."""
    response = authenticated_client.get("/api/v1/library/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Becoming"
```

**Problems:**
- Mock doesn't test real database behavior
- No validation of actual ORM constraints
- Difficult to test relationships and cascades
- Brittle - mocks must match exact dict structure

### After (Async ORM)

```python
@pytest.mark.asyncio
async def test_get_library(authenticated_client, db_session, test_user_in_db):
    """Test library endpoint with real database."""
    # Create real test data
    book = await BookFactory.create(
        db=db_session,
        user_id=str(test_user_in_db.user_id),
        asin="B084L6Z6M3",
        title="Becoming"
    )
    await db_session.commit()

    # Test API with real data
    response = authenticated_client.get("/api/v1/library/")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["title"] == "Becoming"
```

**Benefits:**
- Tests real database behavior and constraints
- ORM relationships actually work
- Type-safe - ORM objects instead of dicts
- Better error messages from database

## Test Organization

### Unit Tests (No Database)
For testing pure functions and logic:

```python
def test_extract_authors_from_book_data():
    """Test data extraction - no database needed."""
    book_data = {"authors": [{"name": "Author 1"}, {"name": "Author 2"}]}
    result = extract_authors(book_data)
    assert result == "Author 1, Author 2"
```

### Integration Tests (With Database)
For testing ORM operations and relationships:

```python
@pytest.mark.asyncio
@pytest.mark.db
async def test_add_book_with_contributors(db_session, test_user_in_db):
    """Test book creation with contributors - needs database."""
    book = await BookFactory.create_with_metadata(
        db=db_session,
        user_id=str(test_user_in_db.user_id),
        book_data={
            "authors": [{"name": "Test Author"}],
            "narrators": [{"name": "Test Narrator"}]
        }
    )
    await db_session.commit()

    # Verify relationships
    book_with_contrib = await db_session.refresh(book)
    contributors = await book.awaitable_attrs.contributors
    assert len(contributors) == 2
```

### API Tests (With TestClient)
For testing endpoints:

```python
@pytest.mark.asyncio
async def test_create_book_endpoint(client, db_session, test_user_with_tokens):
    """Test API endpoint with real database data."""
    user = await UserFactory.create(db=db_session)
    await db_session.commit()

    response = client.post(
        "/api/v1/library/",
        json={"asin": "B123", "title": "Test"},
        headers=test_user_with_tokens["headers"]
    )
    assert response.status_code == 201
```

## Fixture Selection Guide

| Test Type | Primary Fixture | Secondary | Use Case |
|-----------|-----------------|-----------|----------|
| Unit | None | N/A | Pure functions, logic |
| Database Integration | `db_session` | Factories | ORM operations |
| API (Real DB) | `test_user_in_db` | `db_session` | API endpoints with data |
| API (Mocked) | `mock_book_ops` | `authenticated_client` | Fast API tests (legacy) |

## Database Setup for Tests

The test infrastructure automatically:
1. Creates a test database (`audibooksync_test`)
2. Creates all tables from `Base.metadata`
3. Runs each test in a transaction
4. Rolls back after each test
5. Cleans up completely after test suite

### Connection String
Tests use `TEST_DATABASE_URL` environment variable or default:
```
postgresql+asyncpg://postgres:postgres@localhost/audibooksync_test
```

## Common Patterns

### Creating Data for Assertions

```python
@pytest.mark.asyncio
async def test_book_search(db_session, test_user_in_db):
    # Create multiple books
    books = []
    for i in range(3):
        book = await BookFactory.create(
            db=db_session,
            user_id=str(test_user_in_db.user_id),
            asin=f"B{i:09d}",
            title=f"Book {i}",
            author="Same Author"  # Search by author
        )
        books.append(book)
    await db_session.commit()

    # Search and verify
    results = await book_service.search_books(
        db=db_session,
        user_id=str(test_user_in_db.user_id),
        query="Same Author"
    )
    assert len(results) == 3
```

### Testing Cascading Deletes

```python
@pytest.mark.asyncio
async def test_delete_user_cascades_to_books(db_session, test_user_in_db):
    # Create user with books
    book = await BookFactory.create(
        db=db_session,
        user_id=str(test_user_in_db.user_id)
    )
    await db_session.commit()

    # Delete user
    await user_service.delete_user(db=db_session, user_id=str(test_user_in_db.user_id))
    await db_session.commit()

    # Verify cascade
    remaining_book = await book_service.get_book_by_asin(
        db=db_session,
        asin=book.asin
    )
    assert remaining_book is None  # Cascaded delete
```

### Testing Transactions

```python
@pytest.mark.asyncio
async def test_sync_rollback_on_error(db_session, test_user_in_db):
    sync = await SyncFactory.create(
        db=db_session,
        user_id=str(test_user_in_db.user_id)
    )
    await db_session.commit()

    try:
        # Simulate error during sync
        await db_session.rollback()
        raise Exception("Test error")
    except Exception:
        await db_session.rollback()

    # Verify sync still exists (not deleted on error)
    sync_after = await sync_service.get_sync_by_id(
        db=db_session,
        sync_id=sync.sync_id
    )
    assert sync_after is not None
```

## Performance Considerations

Tests with real database are slightly slower than mocked tests but provide:
- Better coverage of actual behavior
- Earlier detection of schema/constraint issues
- More confidence in production correctness

**Optimization tips:**
1. Use `@pytest.fixture(scope="function")` for test isolation (default)
2. Batch operations where possible
3. Use `db_session.flush()` instead of `commit()` when not needed
4. Consider `@pytest.fixture(scope="module")` for read-only setup data

## Troubleshooting

### "No such module: 'tests.factories'"
Ensure `tests/__init__.py` exists and contains:
```python
"""Test package for AudioBookSync."""
```

### "asyncio event loop is closed"
Use `@pytest.mark.asyncio` decorator on async test functions.

### Database connection issues
Ensure:
1. PostgreSQL is running
2. Test database `audibooksync_test` exists or can be created
3. User has appropriate permissions
4. `TEST_DATABASE_URL` is set if not using default

### Tests fail with foreign key errors
This is often correct behavior! It means:
1. Your test data is incomplete
2. You need to create dependencies first
3. Use factories to handle this automatically

## Next Steps

1. **Audit existing tests** - Identify monkeypatch usage
2. **Convert incrementally** - One test at a time
3. **Test real scenarios** - Add tests for cascades, constraints
4. **Document patterns** - Add examples for your team
5. **Monitor performance** - Ensure test suite doesn't get too slow

## Questions?

See `tests/conftest.py` for fixture implementations or `tests/factories.py` for factory patterns.
