"""Storage adapters for file storage implementations."""

from src.adapters.storage.minio_storage_adapter import MinIOStorageAdapter
from src.adapters.storage.storage_factory import get_storage_adapter

# S3StorageAdapter is imported lazily in storage_factory when needed
# to avoid dependency on boto3 which is optional

__all__ = ["MinIOStorageAdapter", "get_storage_adapter"]
