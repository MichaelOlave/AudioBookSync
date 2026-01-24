# Hexagonal Architecture

## Overview

AudioBookSync uses hexagonal architecture (ports and adapters) to decouple business logic from infrastructure concerns. This allows us to swap implementations without changing core logic.

## Structure

```
src/
├── ports/                          # Port definitions (interfaces)
│   ├── __init__.py
│   └── file_storage_port.py       # File storage contract
│
├── adapters/                       # Port implementations (adapters)
│   ├── __init__.py
│   └── storage/
│       ├── __init__.py
│       └── minio_storage_adapter.py   # MinIO implementation
│
├── infrastructure/                 # Low-level infrastructure
│   ├── minio_client.py            # MinIO client wrapper
│   ├── storage_service.py         # Legacy (being phased out)
│   └── file_utils.py
│
└── api/                           # Business logic (uses ports)
    ├── routers/
    ├── services/
    └── ...
```

## Ports

### FileStoragePort (`src/ports/file_storage_port.py`)

Defines the contract for file storage operations:

```python
class FileStoragePort(ABC):
    @abstractmethod
    def ensure_user_bucket(self, user_id: str) -> bool: ...

    @abstractmethod
    def save_file(self, user_id: str, file_path: str, file_type: str,
                  asin: Optional[str] = None, title: Optional[str] = None)
                  -> Tuple[bool, Optional[str]]: ...

    @abstractmethod
    def get_file(self, user_id: str, object_key: str) -> Optional[str]: ...

    @abstractmethod
    def stream_file(self, user_id: str, object_key: str, offset: int = 0,
                    length: Optional[int] = None) -> bytes: ...

    @abstractmethod
    def delete_file(self, user_id: str, object_key: str) -> bool: ...
```

## Adapters

### MinIOStorageAdapter (`src/adapters/storage/minio_storage_adapter.py`)

Implements `FileStoragePort` using MinIO:

- Per-user bucket isolation (`user-{user_id}`)
- Object key patterns:
  - Downloaded: `downloaded/{asin}.aax`
  - Decrypted: `decrypted/{normalized_title}.m4b`
- Range request support for audio seeking
- Comprehensive error handling

## Usage

### Before (Tightly Coupled)

```python
from src.infrastructure.storage_service import StorageService

service = StorageService()  # Depends on MinIO implementation
success, key = service.save_file(...)
```

### After (Loosely Coupled)

```python
from src.ports.file_storage_port import FileStoragePort
from src.adapters.storage.minio_storage_adapter import MinIOStorageAdapter

storage: FileStoragePort = MinIOStorageAdapter()
success, key = storage.save_file(...)
```

Now you can swap implementations:

```python
# Use a different storage backend
from src.adapters.storage.s3_storage_adapter import S3StorageAdapter
storage: FileStoragePort = S3StorageAdapter()
```

## Adding New Storage Adapters

To add a new storage adapter (e.g., AWS S3):

1. Create `src/adapters/storage/s3_storage_adapter.py`
2. Implement `FileStoragePort`
3. Update imports in `src/adapters/storage/__init__.py`
4. Use in code: `storage: FileStoragePort = S3StorageAdapter()`

Example:

```python
from src.ports.file_storage_port import FileStoragePort

class S3StorageAdapter(FileStoragePort):
    def __init__(self, s3_client=None):
        self.s3_client = s3_client or boto3.client('s3')

    def ensure_user_bucket(self, user_id: str) -> bool:
        # AWS S3 bucket creation logic
        pass

    def save_file(self, user_id: str, file_path: str, file_type: str, ...)
                  -> Tuple[bool, Optional[str]]:
        # AWS S3 upload logic
        pass

    # ... implement other methods
```

## Migration Path

The codebase is transitioning from direct `StorageService` usage to `FileStoragePort` usage:

1. **Phase 1** (Current): New code uses `FileStoragePort` interface
2. **Phase 2**: Gradually update existing code to use port
3. **Phase 3**: Remove `StorageService` once fully migrated

## Benefits

- **Testability**: Easy to mock storage implementations
- **Flexibility**: Swap storage backends without changing business logic
- **Separation of Concerns**: Infrastructure code isolated from core logic
- **Future-Proof**: Easy to add new storage backends

## Related Files

- Port definition: `src/ports/file_storage_port.py`
- MinIO adapter: `src/adapters/storage/minio_storage_adapter.py`
- Tests: `tests/adapters/storage/test_minio_storage_adapter.py` (to be created)
