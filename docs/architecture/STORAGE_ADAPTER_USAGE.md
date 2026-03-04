# Storage Adapter Usage Guide

This guide explains how to use the storage adapter factory system to dynamically load the correct storage provider based on user configuration stored in the database.

## Overview

The storage adapter system works in three layers:

1. **Port** (`FileStoragePort`) - Abstract interface defining storage operations
2. **Adapters** (`MinIOStorageAdapter`, `S3StorageAdapter`) - Concrete implementations
3. **Factory** (`get_storage_adapter`) - Creates appropriate adapter based on configuration
4. **Service** (`get_user_storage_adapter`) - Retrieves user's config and creates adapter

## Architecture

```
User Database
    ↓
storage_config JSON
    ├─ provider_type: "minio" | "aws_s3" | "gcs"
    ├─ endpoint (MinIO)
    ├─ region (S3)
    ├─ access_key
    └─ secret_key
    ↓
get_user_storage_adapter(db, user_id)
    ↓
get_storage_adapter(provider_type, config)
    ↓
    ├─ MinIOStorageAdapter (if minio)
    ├─ S3StorageAdapter (if aws_s3)
    └─ GCSStorageAdapter (if gcs - future)
    ↓
FileStoragePort (interface)
    ↓
Business Logic (no dependencies on specific implementation)
```

## Frontend Flow

### 1. User Selects Storage Provider

Frontend presents options:
```
[x] MinIO (Development)
[ ] AWS S3 (Production)
[ ] Google Cloud Storage (Future)
```

### 2. User Enters Provider Configuration

**For MinIO:**
```json
{
  "provider_type": "minio",
  "endpoint": "http://minio.example.com:9000",
  "access_key": "your-access-key",
  "secret_key": "your-secret-key",
  "use_ssl": false
}
```

**For AWS S3:**
```json
{
  "provider_type": "aws_s3",
  "region": "us-east-1",
  "access_key": "AKIAIOSFODNN7EXAMPLE",
  "secret_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}
```

### 3. Frontend Sends to API

```javascript
// Update storage configuration
const response = await fetch('/api/v1/settings/storage', {
  method: 'PUT',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    provider_type: 'aws_s3',
    region: 'us-east-1',
    access_key: 'AKIA...',
    secret_key: 'wJalr...',
    endpoint: null  // Not needed for S3
  })
});
```

### 4. Backend Stores Configuration

```python
# src/api/routers/settings.py
@router.put("/storage", response_model=StorageConfigResponse)
async def update_storage_config(
    config: StorageConfigRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    storage_config = {
        "provider_type": config.provider_type,
        "endpoint": config.endpoint,
        "region": config.region,
        "access_key": config.access_key,
        "secret_key": config.secret_key,
        "use_ssl": config.use_ssl,
    }

    # Store in database
    success = await user_service.update_user_storage_config(db, user_id, storage_config)
```

The configuration is stored in the `users.storage_config` column as JSON.

### 5. Backend Uses Configuration

When your code needs to perform storage operations:

```python
from src.database.services import user_service

# Get the user's configured storage adapter
storage = await user_service.get_user_storage_adapter(db, user_id)

# Use it like any other storage adapter
success, object_key = storage.save_file(
    user_id=user_id,
    file_path="/path/to/audiobook.m4b",
    file_type="decrypted",
    title="Project Hail Mary"
)
```

That's it! No need to know which provider the user chose - the system handles it automatically.

## Usage Examples

### Example 1: Download Handler Using User's Storage

```python
# src/celery_app/tasks/download_tasks.py
from src.database.services import user_service

async def execute_download_task(user_id: str, book: dict):
    """Download audiobook and save to user's configured storage."""
    async with AsyncSessionLocal() as db:
        # Get user's storage adapter
        storage = await user_service.get_user_storage_adapter(db, user_id)

        # Download from Audible (simplified)
        downloaded_file = "/tmp/B001ABC123.aax"

        # Save to user's configured storage (MinIO, S3, or GCS)
        success, object_key = storage.save_file(
            user_id=user_id,
            file_path=downloaded_file,
            file_type="downloaded",
            asin="B001ABC123"
        )

        if success:
            print(f"Saved to {object_key}")
```

### Example 2: Stream Handler Using User's Storage

```python
# src/api/routers/files.py
from src.database.services import user_service

@router.get("/audiobook/{asin}")
async def stream_audiobook(asin: str, db: AsyncSession = Depends(get_db_session)):
    """Stream audiobook from user's configured storage."""

    # Get user's storage adapter
    storage = await user_service.get_user_storage_adapter(db, user_id)

    # Stream from whatever provider they configured
    data = storage.stream_file(
        user_id=user_id,
        object_key="decrypted/audiobook.m4b",
        offset=1024,
        length=8192
    )

    return StreamingResponse(data, media_type="audio/mp4")
```

### Example 3: Cleanup Task Using User's Storage

```python
# src/celery_app/tasks/cleanup_tasks.py
from src.database.services import user_service

async def cleanup_user_files(user_id: str):
    """Clean up orphaned files from user's storage."""
    async with AsyncSessionLocal() as db:
        # Get user's storage adapter
        storage = await user_service.get_user_storage_adapter(db, user_id)

        # List and delete orphaned files
        orphaned_keys = ["downloaded/B001ABC123.aax"]

        for key in orphaned_keys:
            success = storage.delete_file(user_id, key)
            if success:
                print(f"Deleted {key}")
```

## Factory Function Usage

If you need to use the factory directly without database lookup:

```python
from src.adapters.storage.storage_factory import get_storage_adapter

# Create MinIO adapter
config = {
    "endpoint": "http://localhost:9000",
    "access_key": "minioadmin",
    "secret_key": "minioadmin",
    "secure": False
}
storage = get_storage_adapter("minio", config)

# Create S3 adapter
config = {
    "region": "us-west-2",
    "access_key": "AKIA...",
    "secret_key": "wJalr..."
}
storage = get_storage_adapter("aws_s3", config)
```

## Database Schema

The storage configuration is stored in the `users` table:

```sql
ALTER TABLE users ADD COLUMN storage_config JSONB;

-- Example data for MinIO user
UPDATE users SET storage_config = jsonb_build_object(
    'provider_type', 'minio',
    'endpoint', 'http://localhost:9000',
    'access_key', 'minioadmin',
    'secret_key', 'minioadmin',
    'use_ssl', false
) WHERE user_id = '550e8400-e29b-41d4-a716-446655440000';

-- Example data for S3 user
UPDATE users SET storage_config = jsonb_build_object(
    'provider_type', 'aws_s3',
    'region', 'us-east-1',
    'access_key', 'AKIA...',
    'secret_key', 'wJalr...'
) WHERE user_id = '550e8400-e29b-41d4-a716-446655440000';
```

## Error Handling

The factory provides clear error messages:

```python
from src.adapters.storage.storage_factory import get_storage_adapter

try:
    storage = get_storage_adapter("invalid_provider", {})
except ValueError as e:
    print(f"Unsupported provider: {e}")
    # ValueError: Unsupported storage provider: invalid_provider.
    # Supported providers: minio, aws_s3, gcs

try:
    storage = get_storage_adapter("minio", {})  # Missing endpoint
except ValueError as e:
    print(f"Invalid config: {e}")
    # ValueError: MinIO configuration requires 'endpoint'
```

## Migration Guide

### Migrating from Hardcoded MinIO to User-Selected Providers

**Before (hardcoded MinIO):**
```python
from src.adapters.storage.minio_storage_adapter import MinIOStorageAdapter

storage = MinIOStorageAdapter()  # Always MinIO
```

**After (user-selected provider):**
```python
from src.database.services import user_service

storage = await user_service.get_user_storage_adapter(db, user_id)  # Respects user choice
```

The rest of your code remains identical - you still call the same `FileStoragePort` methods.

## Testing

Create test adapters for different scenarios:

```python
from unittest.mock import Mock
from src.ports.file_storage_port import FileStoragePort

class MockStorageAdapter(FileStoragePort):
    """Mock adapter for testing."""

    def ensure_user_bucket(self, user_id: str) -> bool:
        return True

    def save_file(self, user_id: str, file_path: str, file_type: str, **kwargs):
        return (True, f"mock/{file_type}/file.key")

    # ... implement other methods
```

## Related Documentation

- [Hexagonal Architecture](./HEXAGONAL_ARCHITECTURE.md) - Overall architecture overview
- [MinIO Setup](../storage/MINIO_VS_S3_COMPARISON.md) - Provider comparison
- [S3 Setup](../storage/S3_SETUP_GUIDE.md) - AWS S3 configuration
- [Storage Factory](../code/storage_factory.py) - Factory implementation
