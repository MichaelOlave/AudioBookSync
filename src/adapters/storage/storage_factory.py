"""Factory for creating storage adapters based on configuration.

This module provides a factory function that instantiates the correct storage adapter
based on user-selected provider type and configuration stored in the database.
"""

from typing import Literal, Optional

from loguru import logger

from src.ports.file_storage_port import FileStoragePort


def get_storage_adapter(
    provider_type: Literal["minio", "aws_s3", "gcs"],
    config: Optional[dict] = None,
) -> FileStoragePort:
    """Get storage adapter instance based on provider type.

    Factory function that creates and returns the appropriate storage adapter
    based on the provider type and optional configuration.

    Args:
        provider_type: Type of storage provider ("minio", "aws_s3", or "gcs")
        config: Optional configuration dictionary containing provider-specific settings:
                - For MinIO: endpoint, access_key, secret_key, secure, region
                - For S3: region, access_key, secret_key
                - For GCS: project_id, credentials_path (not yet implemented)

    Returns:
        FileStoragePort: Configured storage adapter instance

    Raises:
        ValueError: If provider_type is unsupported or configuration is invalid

    Example:
        >>> config = {
        ...     "provider_type": "minio",
        ...     "endpoint": "http://localhost:9000",
        ...     "access_key": "minioadmin",
        ...     "secret_key": "minioadmin",
        ...     "secure": False
        ... }
        >>> storage = get_storage_adapter("minio", config)
        >>> success, key = storage.save_file(
        ...     user_id="user-123",
        ...     file_path="/path/to/file.aax",
        ...     file_type="downloaded",
        ...     asin="B001ABC123"
        ... )
    """
    config = config or {}

    if provider_type == "minio":
        return _get_minio_adapter(config)
    elif provider_type == "aws_s3":
        return _get_s3_adapter(config)
    elif provider_type == "gcs":
        return _get_gcs_adapter(config)
    else:
        raise ValueError(
            f"Unsupported storage provider: {provider_type}. "
            f"Supported providers: minio, aws_s3, gcs"
        )


def _get_minio_adapter(config: dict) -> FileStoragePort:
    """Create MinIO storage adapter from configuration.

    Args:
        config: MinIO configuration dictionary with keys:
                - endpoint: MinIO server endpoint (required)
                - access_key: Access key (optional, defaults to minioadmin)
                - secret_key: Secret key (optional, defaults to minioadmin)
                - secure: Use SSL/TLS (optional, defaults to False)
                - region: Region name (optional, defaults to us-east-1)

    Returns:
        FileStoragePort: Configured MinIOStorageAdapter instance

    Raises:
        ValueError: If required configuration is missing
    """
    from src.infrastructure.minio_client import MinIOClient
    from src.adapters.storage.minio_storage_adapter import MinIOStorageAdapter

    endpoint = config.get("endpoint")
    if not endpoint:
        raise ValueError("MinIO configuration requires 'endpoint'")

    access_key = config.get("access_key", "minioadmin")
    secret_key = config.get("secret_key", "minioadmin")
    secure = config.get("secure", False)

    logger.info(f"Creating MinIO adapter with endpoint: {endpoint}")

    # Create MinIO client with provided configuration
    minio_client = MinIOClient(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )

    return MinIOStorageAdapter(minio_client=minio_client)


def _get_s3_adapter(config: dict) -> FileStoragePort:
    """Create AWS S3 storage adapter from configuration.

    Args:
        config: S3 configuration dictionary with keys:
                - region: AWS region (optional, defaults to us-east-1)
                - bucket_name: S3 bucket name (optional, defaults to per-user bucket pattern)
                - access_key: AWS access key (optional, uses AWS credentials chain)
                - secret_key: AWS secret key (optional, uses AWS credentials chain)

    Returns:
        FileStoragePort: Configured S3StorageAdapter instance

    Raises:
        ValueError: If configuration is invalid
    """
    from src.adapters.storage.s3_storage_adapter import S3StorageAdapter
    import boto3

    region_name = config.get("region", "us-east-1")
    bucket_name = config.get("bucket_name")

    logger.info(f"Creating S3 adapter with region: {region_name}, bucket_name: {bucket_name}")

    # If access keys are provided, use them; otherwise boto3 will use credential chain
    access_key = config.get("access_key")
    secret_key = config.get("secret_key")

    if access_key and secret_key:
        # Create S3 client with explicit credentials
        s3_client = boto3.client(
            "s3",
            region_name=region_name,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
    else:
        # Use credential chain (env vars, IAM role, etc.)
        s3_client = boto3.client("s3", region_name=region_name)

    return S3StorageAdapter(region_name=region_name, s3_client=s3_client, bucket_name=bucket_name)


def _get_gcs_adapter(config: dict) -> FileStoragePort:
    """Create Google Cloud Storage adapter from configuration.

    Not yet implemented.

    Args:
        config: GCS configuration dictionary

    Raises:
        NotImplementedError: GCS adapter is not yet available
    """
    raise NotImplementedError(
        "Google Cloud Storage adapter is not yet implemented. "
        "Currently supported providers: minio, aws_s3"
    )
