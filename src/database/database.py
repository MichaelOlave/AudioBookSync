"""Database operations aggregator for easy access to all database modules."""

from .db_books import BookOperations, book_ops
from .db_decryptions import DecryptionOperations, decryption_ops
from .db_downloads import DownloadOperations, download_ops
from .db_errors import ErrorOperations, error_ops
from .db_pool import DatabasePool, db_pool
from .db_sync import SyncOperations, sync_ops
from .db_users import UserOperations, user_ops


class DatabaseOperations:
    """Aggregated database operations interface (singleton)."""

    _instance = None

    def __new__(cls):
        """Enforce singleton pattern for unified operations interface."""
        if cls._instance is None:
            cls._instance = super(DatabaseOperations, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize all database operation modules once."""
        if getattr(self, "_initialized", False):
            return

        self.users = user_ops
        self.books = book_ops
        self.downloads = download_ops
        self.decryptions = decryption_ops
        self.syncs = sync_ops
        self.errors = error_ops
        self.pool = db_pool

        self._initialized = True

    def close_all_connections(self):
        """Close all database connections in the pool."""
        self.pool.close_all_connections()


# Singleton instance for backward compatibility
db_ops = DatabaseOperations()

__all__ = [
    "DatabaseOperations",
    "db_ops",
    "UserOperations",
    "BookOperations",
    "DownloadOperations",
    "DecryptionOperations",
    "SyncOperations",
    "ErrorOperations",
    "DatabasePool",
    "user_ops",
    "book_ops",
    "download_ops",
    "decryption_ops",
    "sync_ops",
    "error_ops",
    "db_pool",
]
