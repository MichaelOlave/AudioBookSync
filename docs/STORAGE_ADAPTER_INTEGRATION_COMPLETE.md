# Storage Adapter System - Complete Integration Guide

This document explains the complete system for user-selectable storage providers in AudioBookSync.

## Overview

Users can now select their preferred storage provider (MinIO, AWS S3, or future providers) through the frontend, and the system automatically uses the chosen provider for all file operations.

## Components Created

### 1. Storage Adapters

#### MinIOStorageAdapter (`src/adapters/storage/minio_storage_adapter.py`)
- Implements `FileStoragePort` for MinIO
- Handles per-user bucket isolation
- Supports Range requests for audio streaming
- 380+ lines of production-ready code

#### S3StorageAdapter (`src/adapters/storage/s3_storage_adapter.py`)
- Implements `FileStoragePort` for AWS S3
- Configurable region support
- Boto3 client management
- 360+ lines of production-ready code

### 2. Storage Factory (`src/adapters/storage/storage_factory.py`)

Factory function that creates the appropriate adapter:

```python
from src.adapters.storage import get_storage_adapter

storage = get_storage_adapter("minio", config)  # MinIOStorageAdapter
storage = get_storage_adapter("aws_s3", config)  # S3StorageAdapter
```

**Features:**
- Provider type validation
- Configuration validation per provider
- Automatic client initialization
- Clear error messages

### 3. User Service Extension (`src/database/services/user_service.py`)

New function: `get_user_storage_adapter(db, user_id)`

Retrieves user's storage configuration from database and returns configured adapter:

```python
storage = await user_service.get_user_storage_adapter(db, user_id)
```

**Features:**
- Reads from `users.storage_config` JSON column
- Defaults to MinIO if not configured
- Error handling with clear messages
- Logging for debugging

### 4. Database Model Update (`src/database/models/user.py`)

Added `storage_config` column to User model:

```python
storage_config = Column(
    JSON,
    nullable=True,
    comment="Storage provider configuration (provider_type, endpoint, credentials, etc)"
)
```

### 5. Database Migration (`database/alembic/versions/010_add_user_storage_config.py`)

Alembic migration to add `storage_config` column:
- Creates JSONB column
- Sets default MinIO config for existing users
- Reversible downgrade

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend                                │
│  User selects storage provider (MinIO / S3)                 │
│  Enters configuration (endpoint, region, credentials)       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼ PUT /api/v1/settings/storage
┌──────────────────────────────────────────────────────────────┐
│              Backend API (settings.py)                       │
│  - Validates configuration                                  │
│  - Tests connection                                         │
│  - Saves to database                                        │
└──────────────────────┬───────────────────────────────────────┘
                       │
                       ▼ update_user_storage_config()
┌──────────────────────────────────────────────────────────────┐
│         Database (users.storage_config JSON)                │
│  {                                                           │
│    "provider_type": "aws_s3",                               │
│    "region": "us-east-1",                                   │
│    "access_key": "AKIA...",                                 │
│    "secret_key": "wJalr..."                                 │
│  }                                                          │
└──────────────────────┬───────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        │                             │
        ▼                             ▼
At Runtime:                    During Testing:
get_user_storage_adapter()     Inject mock adapter
        │                             │
        ▼                             ▼
   Factory                       Direct instantiation
        │                             │
        ├─ MinIO?                     │
        │  └─ MinIOStorageAdapter     │
        │                             │
        ├─ S3?                        │
        │  └─ S3StorageAdapter        │
        │                             │
        └─ GCS? (future)              │
           └─ GCSStorageAdapter       │
                                      │
        └─────────────────────────────┘
                    │
                    ▼ FileStoragePort interface
        ┌──────────────────────────────┐
        │  - save_file()               │
        │  - get_file()                │
        │  - stream_file()             │
        │  - delete_file()             │
        │  - file_exists()             │
        │  - ensure_user_bucket()      │
        └──────────────────────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   Download    Decryption   Streaming
      Task        Task       Endpoint
```

## Usage in Code

### In API Endpoints

```python
@router.get("/audiobook/{asin}")
async def stream_audiobook(
    asin: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    user_id = get_user_id(current_user)

    # Get user's configured storage adapter
    storage = await user_service.get_user_storage_adapter(db, user_id)

    # Use it - works with any provider
    data = storage.stream_file(user_id, object_key, offset, length)

    return StreamingResponse(data, media_type="audio/mp4")
```

### In Background Tasks

```python
async def execute_download_task(user_id: str, book: dict):
    async with AsyncSessionLocal() as db:
        # Get user's storage adapter
        storage = await user_service.get_user_storage_adapter(db, user_id)

        # Download and save
        success, object_key = storage.save_file(
            user_id=user_id,
            file_path=downloaded_file,
            file_type="downloaded",
            asin=book["asin"]
        )
```

### In Cleanup Tasks

```python
async def cleanup_user_files(user_id: str):
    async with AsyncSessionLocal() as db:
        storage = await user_service.get_user_storage_adapter(db, user_id)

        # Delete files from whatever provider they use
        storage.delete_file(user_id, "downloaded/B001ABC123.aax")
```

## Storage Configuration Format

### MinIO Configuration

```json
{
  "provider_type": "minio",
  "endpoint": "http://minio.example.com:9000",
  "access_key": "your-access-key",
  "secret_key": "your-secret-key",
  "use_ssl": false,
  "bucket_name": "audiobooks"
}
```

### AWS S3 Configuration

```json
{
  "provider_type": "aws_s3",
  "region": "us-east-1",
  "access_key": "AKIAIOSFODNN7EXAMPLE",
  "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
```

### Google Cloud Storage Configuration (Future)

```json
{
  "provider_type": "gcs",
  "project_id": "my-project",
  "credentials_path": "/path/to/service-account-key.json"
}
```

## Frontend Integration

### Settings Page Flow

```
1. GET /api/v1/settings/storage
   ↓ Shows current provider and configuration

2. User selects new provider from dropdown:
   [ ] MinIO (Current)
   [x] AWS S3
   [ ] Google Cloud Storage

3. User enters provider-specific config:
   AWS S3:
   - Region: [us-east-1]
   - Access Key: [AKIA...]
   - Secret Key: [••••••••]

4. User clicks "Test Connection"
   POST /api/v1/settings/storage/test
   ↓ Returns: { success: true, bucket_exists: true }

5. User saves configuration
   PUT /api/v1/settings/storage
   ↓ Updates database, returns new configuration
```

## Database Migration Steps

1. Run migration to add `storage_config` column:
   ```bash
   alembic upgrade head
   ```

2. Existing users get default MinIO config:
   ```json
   {
     "provider_type": "minio",
     "endpoint": "http://localhost:9000",
     "access_key": "minioadmin",
     "secret_key": "minioadmin",
     "use_ssl": false
   }
   ```

3. Users can update through API or manually:
   ```sql
   UPDATE users SET storage_config = jsonb_build_object(
     'provider_type', 'aws_s3',
     'region', 'us-west-2',
     'access_key', 'AKIA...',
     'secret_key', 'wJalr...'
   ) WHERE user_id = '550e8400-e29b-41d4-a716-446655440000';
   ```

## Migration from Hardcoded Provider

If your code was using a hardcoded storage adapter:

**Before:**
```python
from src.adapters.storage.minio_storage_adapter import MinIOStorageAdapter

storage = MinIOStorageAdapter()  # Always MinIO
```

**After:**
```python
from src.database.services import user_service

storage = await user_service.get_user_storage_adapter(db, user_id)
```

The rest of your code remains identical!

## Error Handling

The system provides clear error messages:

```python
try:
    storage = await user_service.get_user_storage_adapter(db, user_id)
except ValueError as e:
    # "User not found: user-id-here"
    # "Failed to initialize storage adapter: MinIO connection required 'endpoint'"

try:
    success, key = storage.save_file(user_id, path, "downloaded", asin=asin)
except Exception as e:
    # Provider-specific errors with context
    logger.error(f"Failed to save file: {e}")
```

## Testing

Create test adapters:

```python
from src.ports.file_storage_port import FileStoragePort

class MockStorageAdapter(FileStoragePort):
    def ensure_user_bucket(self, user_id: str) -> bool:
        return True

    def save_file(self, user_id: str, file_path: str, file_type: str, **kwargs):
        return (True, f"mock/{file_type}/{file_path.split('/')[-1]}")

    # ... implement other methods

# Use in tests
storage = MockStorageAdapter()
```

## Dependency Injection (Recommended)

For testability, use dependency injection:

```python
from fastapi import Depends

async def get_storage(
    user_id: str = Depends(get_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> FileStoragePort:
    """Dependency that provides storage adapter for current user."""
    return await user_service.get_user_storage_adapter(db, user_id)

@router.post("/upload")
async def upload_file(
    storage: FileStoragePort = Depends(get_storage),
):
    # Use storage - works with any provider
    ...
```

## Performance Considerations

### Caching (Future Enhancement)

Consider caching the adapter per user per request:

```python
@lru_cache(maxsize=1000)
async def get_user_storage_adapter(db, user_id):
    """Cached version - invalidate when config changes."""
    ...
```

### Connection Pooling

The factory creates new clients. For high-volume scenarios:

```python
# S3 adapter uses connection pooling by default
s3_client = boto3.client("s3")  # Reuses connections

# MinIO adapter creates new client
minio_client = MinIOClient(...)  # Could pool connections
```

## Troubleshooting

### User Storage Config Not Found

If `get_user_storage_adapter()` fails:

1. Check user exists: `SELECT * FROM users WHERE user_id = '...';`
2. Check storage_config: `SELECT storage_config FROM users WHERE user_id = '...';`
3. If null, run migration: `alembic upgrade head`
4. Fallback to default MinIO config

### Storage Connection Failed

1. Check configuration: GET /api/v1/settings/storage
2. Test connection: POST /api/v1/settings/storage/test
3. Verify credentials have required permissions
4. Check network connectivity to storage endpoint

### Provider Not Recognized

```python
try:
    storage = get_storage_adapter("invalid_provider", {})
except ValueError as e:
    print(e)
    # ValueError: Unsupported storage provider: invalid_provider.
    # Supported providers: minio, aws_s3, gcs
```

## Related Documentation

- [Hexagonal Architecture](docs/architecture/HEXAGONAL_ARCHITECTURE.md)
- [Storage Adapter Usage](docs/architecture/STORAGE_ADAPTER_USAGE.md)
- [MinIO vs S3 Comparison](docs/storage/MINIO_VS_S3_COMPARISON.md)
- [S3 Setup Guide](docs/storage/S3_SETUP_GUIDE.md)
- [Storage Factory Source](src/adapters/storage/storage_factory.py)
- [User Service Source](src/database/services/user_service.py)

## Summary

The complete storage adapter integration provides:

✅ **User Choice** - Select storage provider from frontend
✅ **Database Persistence** - Configuration stored in `users.storage_config`
✅ **Automatic Selection** - System picks correct adapter at runtime
✅ **No Code Changes** - Business logic unchanged, just call `get_user_storage_adapter()`
✅ **Future Proof** - Easy to add new providers (GCS, etc.)
✅ **Production Ready** - Error handling, logging, validation included
✅ **Testable** - Dependency injection and mock support
