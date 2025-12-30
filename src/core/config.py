"""Configuration management for AudioBookSync."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration loaded from environment variables and defaults."""

    DATABASE_URL = os.getenv(
        "DATABASE_URL", "postgresql://postgres@localhost:5432/audiobooksync"
    )

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

    @classmethod
    def ensure_directories(cls) -> None:
        """Create necessary directories if they don't exist."""
        for directory in [cls.DOWNLOAD_DIR, cls.DECRYPTED_DIR, cls.LOG_DIR]:
            Path(directory).mkdir(parents=True, exist_ok=True)
