# Example Route Updates: From psycopg2 to SQLAlchemy

This document shows how to update existing routes from the old psycopg2 pattern to the new SQLAlchemy async pattern.

## Example 1: Authentication Routes

### Old Pattern (psycopg2)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from src.database.db_users import user_ops
from src.api.schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.post("/register")
async def register(user_data: UserCreate):
    # Synchronous call in async function (blocking!)
    user_id = user_ops.create_user(
        username=user_data.username,
        email=user_data.email,
        auth_file_path=user_data.auth_file_path,
        activation_bytes=user_data.activation_bytes,
    )

    if not user_id:
        raise HTTPException(status_code=400, detail="Registration failed")

    return {"user_id": user_id, "message": "User created"}
```

### New Pattern (SQLAlchemy Async)

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.services import user_service
from src.database.engine import get_db_session
from src.api.schemas.user import UserCreate, UserResponse

router = APIRouter()

@router.post("/register")
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    # Fully async call - non-blocking!
    user = await user_service.create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        auth_file_path=user_data.auth_file_path,
        activation_bytes=user_data.activation_bytes,
    )

    if not user:
        raise HTTPException(status_code=400, detail="Registration failed")

    await db.commit()
    return UserResponse.from_orm(user)
```

## Example 2: User Profile Routes

### Old Pattern

```python
from src.database.db_users import user_ops
from src.api.security.auth import get_current_user

@router.get("/me")
async def get_profile(current_user: dict = Depends(get_current_user)):
    # current_user is already fetched (but synchronously)
    return UserResponse(**current_user)

@router.put("/me/password")
async def update_password(
    password_data: PasswordUpdate,
    current_user: dict = Depends(get_current_user)
):
    # Synchronous database call
    success = user_ops.update_user_password(
        current_user["user_id"],
        password_data.new_password_hash
    )

    if not success:
        raise HTTPException(status_code=400, detail="Update failed")

    return {"message": "Password updated"}
```

### New Pattern

```python
from src.database.services import user_service
from src.database.engine import get_db_session
from src.api.security.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/me")
async def get_profile(current_user: User = Depends(get_current_user)):
    # current_user is already fetched and is an ORM object
    return UserResponse.from_orm(current_user)

@router.put("/me/password")
async def update_password(
    password_data: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Async database call
    success = await user_service.update_user_password(
        db=db,
        user_id=str(current_user.user_id),
        password_hash=password_data.new_password_hash
    )

    if not success:
        raise HTTPException(status_code=400, detail="Update failed")

    await db.commit()
    return {"message": "Password updated"}
```

## Example 3: Book Library Routes

### Old Pattern

```python
from src.database.db_books import book_ops
from src.database.db_downloads import download_ops

@router.get("/library/books")
async def get_library(current_user: dict = Depends(get_current_user)):
    # Synchronous calls
    books = book_ops.get_books_by_user(current_user["user_id"])
    return [BookResponse(**book) for book in books]

@router.get("/library/books/{asin}")
async def get_book(asin: str, current_user: dict = Depends(get_current_user)):
    # Synchronous call
    book = book_ops.get_book_by_asin(asin)

    if not book or book["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookResponse(**book)

@router.post("/library/books/{asin}/download")
async def start_download(
    asin: str,
    current_user: dict = Depends(get_current_user)
):
    # Create download record
    download_id = download_ops.create_download_status(asin)
    return {"download_id": download_id}
```

### New Pattern

```python
from src.database.services import book_service, download_service
from src.database.engine import get_db_session
from src.api.security.auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/library/books")
async def get_library(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Fully async calls
    books = await book_service.get_books_by_user(
        db=db,
        user_id=str(current_user.user_id)
    )
    return [BookResponse.from_orm(book) for book in books]

@router.get("/library/books/{asin}")
async def get_book(
    asin: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Async call
    book = await book_service.get_book_by_asin(db=db, asin=asin)

    if not book or book.user_id != current_user.user_id:
        raise HTTPException(status_code=404, detail="Book not found")

    return BookResponse.from_orm(book)

@router.post("/library/books/{asin}/download")
async def start_download(
    asin: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Create download record with async call
    download = await download_service.create_download_status(
        db=db,
        asin=asin,
        status="pending"
    )

    if not download:
        raise HTTPException(status_code=400, detail="Failed to create download")

    await db.commit()
    return {"download_id": str(download.download_id)}
```

## Example 4: Sync Operations

### Old Pattern

```python
from src.database.db_sync import sync_ops
from src.database.db_errors import error_ops

@router.post("/sync")
async def start_sync(current_user: dict = Depends(get_current_user)):
    try:
        sync_id = sync_ops.create_sync_history(current_user["user_id"])
        # ... do sync work ...
        sync_ops.complete_sync(sync_id, stats)
        return {"sync_id": sync_id, "status": "completed"}
    except Exception as e:
        error_ops.log_error(
            user_id=current_user["user_id"],
            error_type="sync_error",
            error_message=str(e)
        )
        raise
```

### New Pattern

```python
from src.database.services import sync_service, error_service
from src.database.engine import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

@router.post("/sync")
async def start_sync(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    try:
        # Create sync record
        sync = await sync_service.create_sync_history(
            db=db,
            user_id=current_user.user_id,
            sync_type="full"
        )

        # ... do sync work ...

        # Complete sync
        success = await sync_service.complete_sync(
            db=db,
            sync_id=sync.sync_id,
            books_found=10,
            books_added=3,
            books_removed=0,
            books_downloaded=5,
            books_decrypted=4,
            errors_count=0
        )

        await db.commit()

        if success:
            return {
                "sync_id": str(sync.sync_id),
                "status": "completed"
            }
        else:
            raise HTTPException(status_code=500, detail="Sync update failed")

    except Exception as e:
        # Log error with async call
        await error_service.log_error(
            db=db,
            user_id=current_user.user_id,
            error_type="sync_error",
            error_message=str(e),
            severity="error"
        )
        await db.commit()
        raise HTTPException(status_code=500, detail=str(e))
```

## Example 5: Error Handling

### Old Pattern

```python
from src.database.db_errors import error_ops

@router.get("/errors")
async def get_errors(current_user: dict = Depends(get_current_user)):
    # Synchronous call
    errors = error_ops.get_errors_by_user(current_user["user_id"])
    return [ErrorResponse(**err) for err in errors]

@router.put("/errors/{error_id}/resolve")
async def resolve_error(
    error_id: str,
    resolution: ErrorResolution,
    current_user: dict = Depends(get_current_user)
):
    # Synchronous call
    success = error_ops.resolve_error(error_id, resolution.notes)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resolve")
    return {"message": "Error resolved"}
```

### New Pattern

```python
from src.database.services import error_service
from src.database.engine import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

@router.get("/errors")
async def get_errors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Async call
    errors = await error_service.get_errors_by_user(
        db=db,
        user_id=current_user.user_id,
        unresolved_only=False
    )
    return [ErrorResponse.from_orm(err) for err in errors]

@router.put("/errors/{error_id}/resolve")
async def resolve_error(
    error_id: str,
    resolution: ErrorResolution,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Async call
    from uuid import UUID
    success = await error_service.resolve_error(
        db=db,
        error_id=UUID(error_id),
        resolution_notes=resolution.notes
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to resolve")

    await db.commit()
    return {"message": "Error resolved"}
```

## Key Changes Summary

### 1. Dependency Injection

**Old:**
```python
async def endpoint(current_user: dict = Depends(get_current_user)):
    pass
```

**New:**
```python
async def endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    pass
```

### 2. Service Imports

**Old:**
```python
from src.database.db_users import user_ops
from src.database.db_books import book_ops
```

**New:**
```python
from src.database.services import user_service, book_service
```

### 3. Function Calls

**Old:**
```python
result = db_ops.get_something(param)
```

**New:**
```python
result = await service.get_something(db=db, param=param)
```

### 4. Commit Strategy

**Old:**
```python
# Auto-committed by context manager
user_ops.create_user(...)
```

**New:**
```python
# Must commit explicitly in async context
await user_service.create_user(db=db, ...)
await db.commit()
```

### 5. ORM Object Handling

**Old:**
```python
# Returns dict
user_dict = user_ops.get_user(user_id)
UserResponse(**user_dict)
```

**New:**
```python
# Returns ORM object
user_orm = await user_service.get_user(db, user_id)
UserResponse.from_orm(user_orm)
```

## Testing the Updated Routes

### Using pytest-asyncio

```python
@pytest.mark.asyncio
async def test_get_library(client, test_db_session):
    # Create test user
    user = await user_service.create_user(
        db=test_db_session,
        username="testuser",
        email="test@example.com",
        password_hash="hash123"
    )
    await test_db_session.commit()

    # Create test book
    await book_service.add_book(
        db=test_db_session,
        asin="TEST123",
        user_id=str(user.user_id),
        title="Test Book"
    )
    await test_db_session.commit()

    # Test endpoint
    response = await client.get("/api/v1/library/books")
    assert response.status_code == 200
    assert len(response.json()) == 1
```

## Migration Checklist

- [ ] Update all imports from `db_*.py` to `services`
- [ ] Add `db: AsyncSession = Depends(get_db_session)` to all endpoints
- [ ] Replace all service calls with `await` keyword
- [ ] Change `get_current_user` to accept `db: AsyncSession`
- [ ] Update return types from dict to ORM models
- [ ] Add `await db.commit()` where needed
- [ ] Update schemas to use `.from_orm()`
- [ ] Update tests to use new service layer
- [ ] Test all endpoints with the new services
- [ ] Remove old `db_*.py` files once all routes are migrated

## Performance Considerations

1. **Connection Pooling**: asyncpg handles connection pooling internally
2. **Session Management**: FastAPI's `Depends` ensures proper session cleanup
3. **Lazy Loading**: All relationships use `lazy="select"` to avoid N+1 queries
4. **Explicit Commits**: Only commit when needed for better transaction control

## Debugging Tips

1. Enable SQL logging in engine:
   ```python
   engine = create_async_engine(url, echo=True)  # Logs all SQL
   ```

2. Use browser DevTools to inspect requests/responses

3. Check FastAPI docs at `/docs` for endpoint schemas

4. Use pytest with `-v` for detailed test output:
   ```bash
   pytest tests/ -v -s
   ```
