"""Legacy module aliases for backward compatibility.

This module provides import-time aliases so that code importing from the old
individual database modules continues to work during the migration period.

MIGRATION PHASES
================
Phase 1 (current): Both old and new imports work
  # Old way (deprecated but still works)
  from src.database.db_book_metadata import book_metadata_ops
  from src.database.db_downloads import download_ops

  # New way (preferred)
  from src.database.db_books_consolidated import book_ops
  from src.database.db_operations_consolidated import operation_tracking_ops

Phase 2 (future): Old imports will show deprecation warnings
  - Log warnings when old modules are imported
  - Direct users to use consolidated modules
  - Maintain functionality

Phase 3 (future): Old imports removed
  - Delete individual database modules
  - Remove legacy aliases
  - Use consolidated modules exclusively
"""

# Re-export operations from their original modules
# This allows `from src.database.db_books import book_ops` to still work
from .db_books import book_ops
from .db_book_metadata import book_metadata_ops
from .db_contributors import contributor_ops
from .db_book_contributors import book_contributor_ops
from .db_media_info import media_info_ops
from .db_book_availability import book_availability_ops
from .db_companion_materials import companion_material_ops
from .db_downloads import download_ops
from .db_decryptions import decryption_ops
from .db_sync import sync_ops
from .db_users import user_ops
from .db_reading_progress import reading_progress_ops
from .db_errors import error_ops

__all__ = [
    # Book operations (now consolidated)
    "book_ops",
    "book_metadata_ops",
    "contributor_ops",
    "book_contributor_ops",
    "media_info_ops",
    "book_availability_ops",
    "companion_material_ops",
    # Process tracking operations (now consolidated)
    "download_ops",
    "decryption_ops",
    "sync_ops",
    # Standalone operations
    "user_ops",
    "reading_progress_ops",
    "error_ops",
]
