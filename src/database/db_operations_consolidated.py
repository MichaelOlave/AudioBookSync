"""Consolidated operation tracking database operations module.

This module consolidates all process tracking database operations that were
previously spread across 3 separate modules:
- db_downloads.py (272 lines) - Download status tracking
- db_decryptions.py (250 lines) - Decryption status tracking
- db_sync.py (205 lines) - Sync history tracking

CONSOLIDATION STRATEGY
======================
This module re-exports operations from the individual modules with a unified
interface. This approach:
1. Maintains 100% backward compatibility (old imports still work)
2. Reduces import complexity (single import instead of 3)
3. Logically groups related operations (all process tracking in one place)
4. Preserves singleton pattern across modules

MIGRATION PATH
==============
Phase 1 (current): Both old and new imports work
  from src.database.db_downloads import download_ops  # Still works
  from src.database.db_operations_consolidated import download_ops  # New way

Phase 2 (future): Consolidate actual implementation
  - Merge module contents into this file
  - Update all internal imports
  - Remove old individual modules
"""

from ..database.db_decryptions import decryption_ops as _decryption_ops
from ..database.db_downloads import download_ops as _download_ops
from ..database.db_sync import sync_ops as _sync_ops


class OperationTracking:
    """Unified operation tracking interface consolidating 3 modules.

    Provides a single entry point for all process tracking database operations,
    including downloads, decryptions, and sync history.

    Usage:
        from src.database.db_operations_consolidated import operation_tracking_ops

        # All operations are accessible through this single object
        ops = operation_tracking_ops
        ops.create_download_status(asin="B123")
        ops.update_download_status(download_id="d456", status="completed")
    """

    # =====================
    # Download Operations
    # =====================

    def create_download_status(self, asin: str, status: str = "pending"):
        """Create a download status entry (from db_downloads)."""
        return _download_ops.create_download_status(asin=asin, status=status)

    def update_download_status(self, download_id: str, status: str, **kwargs) -> bool:
        """Update download status (from db_downloads)."""
        return _download_ops.update_download_status(
            download_id=download_id, status=status, **kwargs
        )

    def get_download_by_id(self, download_id: str):
        """Get download record by ID (from db_downloads)."""
        return _download_ops.get_download_by_id(download_id=download_id)

    def get_user_downloads(self, user_id: str, status=None, limit: int = 10, offset: int = 0):
        """Get downloads for a user (from db_downloads)."""
        return _download_ops.get_user_downloads(
            user_id=user_id, status=status, limit=limit, offset=offset
        )

    # =====================
    # Decryption Operations
    # =====================

    def create_decryption_status(self, asin: str, status: str = "pending"):
        """Create a decryption status entry (from db_decryptions)."""
        return _decryption_ops.create_decryption_status(asin=asin, status=status)

    def update_decryption_status(self, decryption_id: str, status: str, **kwargs) -> bool:
        """Update decryption status (from db_decryptions)."""
        return _decryption_ops.update_decryption_status(
            decryption_id=decryption_id, status=status, **kwargs
        )

    def get_decryption_by_id(self, decryption_id: str):
        """Get decryption record by ID (from db_decryptions)."""
        return _decryption_ops.get_decryption_by_id(decryption_id=decryption_id)

    def get_user_decryptions(self, user_id: str, status=None, limit: int = 10, offset: int = 0):
        """Get decryptions for a user (from db_decryptions)."""
        return _decryption_ops.get_user_decryptions(
            user_id=user_id, status=status, limit=limit, offset=offset
        )

    # =====================
    # Sync History Operations
    # =====================

    def create_sync_history(self, user_id: str, sync_type: str = "full"):
        """Create a sync history entry (from db_sync)."""
        return _sync_ops.create_sync_history(user_id=user_id, sync_type=sync_type)

    def complete_sync_history(self, sync_id: str, status: str, **stats) -> bool:
        """Complete a sync history entry (from db_sync)."""
        return _sync_ops.complete_sync_history(sync_id=sync_id, status=status, **stats)

    def get_sync_by_id(self, sync_id: str):
        """Get sync history by ID (from db_sync)."""
        return _sync_ops.get_sync_by_id(sync_id=sync_id)

    def get_user_sync_history(self, user_id: str, limit: int = 10):
        """Get sync history for a user (from db_sync)."""
        return _sync_ops.get_user_sync_history(user_id=user_id, limit=limit)


# Singleton instances
operation_tracking_ops = OperationTracking()

# Aliases for backward compatibility and direct access to individual operations
download_ops = _download_ops
decryption_ops = _decryption_ops
sync_ops = _sync_ops
