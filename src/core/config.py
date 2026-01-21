"""Configuration management for AudioBookSync."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables and defaults."""

    # Build DATABASE_URL from individual env vars or use full URL if provided
    if "DATABASE_URL" in os.environ:
        DATABASE_URL = os.getenv("DATABASE_URL")
    else:
        # Build from individual components (defaults to Docker service names)
        _db_host = os.getenv("POSTGRES_HOST", "localhost")
        _db_port = os.getenv("POSTGRES_PORT", "5432")
        _db_name = os.getenv("POSTGRES_DB", "audiobooksync")
        _db_user = os.getenv("POSTGRES_USER", "postgres")
        _db_password = os.getenv("POSTGRES_PASSWORD", "")
        _db_password_part = f":{_db_password}@" if _db_password else "@"
        DATABASE_URL = f"postgresql://{_db_user}{_db_password_part}{_db_host}:{_db_port}/{_db_name}"

    # Audible Authentication
    AUTH_FILE = os.getenv("AUTH_FILE", "auth.json")
    ACTIVATION_BYTES = os.getenv("ACTIVATION_BYTES", "bytes_go_here")
    # Directories
    DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "audiobooks/downloaded")
    DECRYPTED_DIR = os.getenv("DECRYPTED_DIR", "audiobooks/decrypted")
    LOG_DIR = os.getenv("LOG_DIR", "logs")

    # Audible API
    AUDIBLE_NUM_RESULTS = int(os.getenv("AUDIBLE_NUM_RESULTS", "2"))

    # Comprehensive response groups for rich metadata from Audible API
    # Includes: product info, contributors, media details, ratings, categories,
    # pricing, availability, companion materials, and reading progress
    AUDIBLE_RESPONSE_GROUPS = os.getenv(
        "AUDIBLE_RESPONSE_GROUPS",
        (
            "product_desc, product_attrs, contributors, media, series, "
            "rating, reviews, categories, category_ladders, price, "
            "cover_art_url, publisher, publication_date, origin_asin, "
            "is_returnable, is_removable, is_archived, is_playable, "
            "pdf_url, sku, badge_types, review_attrs, relationships, "
            "percent_complete, last_position_heard, is_finished, "
            "listening_status, claim_code_url"
        ),
    )
    AUDIBLE_SORT_BY = os.getenv("AUDIBLE_SORT_BY", "-PurchaseDate")

    # ========================================================================
    # FastAPI Configuration
    # ========================================================================
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    API_WORKERS = int(os.getenv("API_WORKERS", "4"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # ========================================================================
    # Security Configuration
    # ========================================================================
    SECRET_KEY = os.getenv(
        "SECRET_KEY", "your-secret-key-change-in-production-use-openssl-rand-hex-32"
    )
    ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # ========================================================================
    # CORS Configuration
    # ========================================================================
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8080,http://localhost:5173",
    ).split(",")

    # ========================================================================
    # File Serving Configuration
    # ========================================================================
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(5 * 1024 * 1024 * 1024)))  # 5GB
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", str(1024 * 1024)))  # 1MB

    # ========================================================================
    # Rate Limiting Configuration
    # ========================================================================
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_LOGIN_PER_MINUTE = int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "5"))

    # ========================================================================
    # MinIO Object Storage Configuration
    # ========================================================================
    # MinIO Connection Settings
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() in ("true", "1", "yes")

    # MinIO Feature Flags
    USE_MINIO_STORAGE = os.getenv("USE_MINIO_STORAGE", "false").lower() in (
        "true",
        "1",
        "yes",
    )

    # MinIO Migration Settings
    MIGRATION_FAILURE_THRESHOLD = float(
        os.getenv("MIGRATION_FAILURE_THRESHOLD", "0.10")
    )  # 10% failure rate triggers rollback
    MIGRATION_LOCK_TIMEOUT_HOURS = int(
        os.getenv("MIGRATION_LOCK_TIMEOUT_HOURS", "2")
    )  # Lock timeout for stale migrations
    MIGRATION_BATCH_SIZE = int(
        os.getenv("MIGRATION_BATCH_SIZE", "10")
    )  # Files per batch during migration

    # MinIO Cleanup Settings
    CLEANUP_SCHEDULE = os.getenv(
        "CLEANUP_SCHEDULE", "0 2 * * *"
    )  # Cron schedule for orphaned file cleanup (default: daily at 2 AM)

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        for directory in [cls.DOWNLOAD_DIR, cls.DECRYPTED_DIR, cls.LOG_DIR]:
            Path(directory).mkdir(parents=True, exist_ok=True)
