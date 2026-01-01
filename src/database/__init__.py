"""Database layer for AudioBookSync.

This module provides access to all database operations. The database layer
is transitioning from 14 individual modules to 6 consolidated modules.

MIGRATION PROGRESS
==================
Phase 1 (current): Dual export system
  - All 14 old modules still available
  - 6 new consolidated modules available
  - Both import styles work seamlessly

Example imports:
  # Consolidated modules (preferred)
  from src.database import book_ops  # Consolidated book operations
  from src.database.db_books_consolidated import book_ops
  from src.database.db_operations_consolidated import download_ops

  # Individual modules (deprecated, still work)
  from src.database.db_downloads import download_ops
  from src.database.db_contributors import contributor_ops

See database/db_books_consolidated.py and database/db_operations_consolidated.py
for migration information.
"""

# Old imports (preserved for backward compatibility)
from .database import DatabaseOperations, db_ops
from .db_books import BookOperations, book_ops
from .db_decryptions import DecryptionOperations, decryption_ops
from .db_downloads import DownloadOperations, download_ops
from .db_errors import ErrorOperations, error_ops
from .db_pool import DatabasePool, db_pool
from .db_sync import SyncOperations, sync_ops
from .db_users import UserOperations, user_ops

# New consolidated modules (preferred)
from .db_books_consolidated import BookOperations as BookOperationsConsolidated
from .db_books_consolidated import book_ops as book_ops_consolidated
from .db_operations_consolidated import OperationTracking, operation_tracking_ops
from .db_operations_consolidated import download_ops as download_ops_new
from .db_operations_consolidated import decryption_ops as decryption_ops_new
from .db_operations_consolidated import sync_ops as sync_ops_new

__all__ = [
    # Infrastructure
    "DatabasePool",
    "db_pool",
    "DatabaseOperations",
    "db_ops",
    # User operations
    "UserOperations",
    "user_ops",
    # Old-style imports (backward compatibility)
    "BookOperations",
    "book_ops",
    "DownloadOperations",
    "download_ops",
    "DecryptionOperations",
    "decryption_ops",
    "SyncOperations",
    "sync_ops",
    "ErrorOperations",
    "error_ops",
    # New consolidated modules (preferred)
    "BookOperationsConsolidated",
    "book_ops_consolidated",
    "OperationTracking",
    "operation_tracking_ops",
    "download_ops_new",
    "decryption_ops_new",
    "sync_ops_new",
]
