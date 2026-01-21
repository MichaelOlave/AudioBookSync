"""Database layer for AudioBookSync.

All database operations now use SQLAlchemy ORM async layer exclusively.

ORM Services:
  from src.database.services import user_service
  from src.database.services import book_service
  from src.database.services import metadata_service
  from src.database.services import sync_service
  from src.database.services import download_service
  from src.database.services import decryption_service
  from src.database.services import error_service

Engine:
  from src.database.engine import get_db_session
  from src.database.engine import create_async_engine

Models (for schema access):
  from src.database.models import User, Book, Contributor, SyncHistory, etc.
"""

# Engine exports
from .engine import create_async_engine, get_db_session

# Service exports
from .services import (
    user_service,
    book_service,
    metadata_service,
    sync_service,
    download_service,
    decryption_service,
    error_service,
)

# Models (for schema access if needed)
from .models import (
    User,
    Book,
    Contributor,
    SyncHistory,
    Download,
    Decryption,
    MediaInfo,
    ReadingProgress,
)

__all__ = [
    # Engine
    "create_async_engine",
    "get_db_session",
    # Services
    "user_service",
    "book_service",
    "metadata_service",
    "sync_service",
    "download_service",
    "decryption_service",
    "error_service",
    # Models
    "User",
    "Book",
    "Contributor",
    "SyncHistory",
    "Download",
    "Decryption",
    "MediaInfo",
    "ReadingProgress",
]
