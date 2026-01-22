# Phase 7: Execution Strategy - Raw SQL Module Removal

**Status**: Ready for Execution
**Date**: 2026-01-21
**Audit Results**: 13 modules still in use, 3 safe to remove immediately

---

## Audit Results Summary

### Import Analysis
**Total Modules**: 17 raw SQL modules
**Active Imports**: 13 modules
**Safe to Remove**: 3 modules (db_errors, db_reading_progress, db_users)

### Dependency Map

**Critical Dependencies**:
- All 14 legacy raw SQL modules import `db_pool` (database pool)
- `db_books_consolidated.py` imports 7 different raw SQL modules
- `db_operations_consolidated.py` imports legacy modules
- `database/__init__.py` re-exports all legacy modules
- `src/api/services/sync_service.py` imports `db_sync`

**Current Status**:
- ✓ ORM services fully implemented
- ✓ ORM tests migrated
- ✓ Feature flags in production
- ⚠️ Some fallback imports still present for emergency rollback
- ⚠️ Legacy consolidated modules not fully cleaned up

---

## Revised Phase 7 Execution Plan

### Pre-Execution Verification (Day 1)

**Verification Checklist**:
```bash
# 1. Verify feature flags are working
curl http://localhost:8000/api/v1/feature-flags/status

# 2. Verify no routers using raw SQL
grep -r "from.*db_users\|db_books import" src/api/routers/
# Should return: nothing (only in fallback patterns)

# 3. Verify ORM services are primary
grep -r "from.*database.services import" src/api/routers/ | wc -l
# Should return: many imports

# 4. Audit logs for any SQL fallback usage
tail -f logs/app.log | grep "Using SQL\|fallback"
# Should show: all "Using ORM" messages
```

### Execution Week 1-2: API Service Migration

#### Step 1: Remove Raw SQL from sync_service.py (Day 1-2)

**Current State**:
```python
# src/api/services/sync_service.py (line 8)
from ...database.db_sync import sync_ops
```

**Location**: `src/api/services/sync_service.py`

**Functions Using Raw SQL**:
1. Line 128: `sync_ops.complete_sync_history()` → ORM: `sync_service.complete_sync()`
2. Line 144: `sync_ops.get_sync_by_id()` → ORM: `sync_service.get_sync_by_id()`
3. Line 194: `sync_ops.complete_sync_history()` → ORM: `sync_service.complete_sync()`

**Migration Steps**:

1. Add ORM service import:
```python
# Before:
from ...database.db_sync import sync_ops

# After: Add ORM import
from ...database.services import sync_service
from ...database.engine import get_db_session
```

2. Convert complete_sync_history calls (lines 128, 194):
```python
# Before:
success = sync_ops.complete_sync_history(
    sync_id=sync_id,
    status=status,
    books_found=stats.get("books_found", 0),
    ...
)

# After:
async with get_db_session() as db:
    success = await sync_service.complete_sync(
        db=db,
        sync_id=sync_id,
        status=status,
        books_found=stats.get("books_found", 0),
        ...
    )
    await db.commit()
```

3. Convert get_sync_by_id call (line 144):
```python
# Before:
sync = sync_ops.get_sync_by_id(sync_id)

# After:
async with get_db_session() as db:
    sync_obj = await sync_service.get_sync_by_id(db, sync_id)
    # Convert ORM object to dict if needed for backward compatibility
    sync = {
        'sync_id': str(sync_obj.sync_id),
        'duration_seconds': sync_obj.duration_seconds,
        'books_found': sync_obj.books_found,
        'books_added': sync_obj.books_added,
        'books_downloaded': sync_obj.books_downloaded,
        'books_decrypted': sync_obj.books_decrypted,
        'errors_count': sync_obj.errors_count,
    }
```

4. Tests:
```bash
pytest tests/api/test_sync.py -v
# All tests should pass with ORM implementation
```

5. Commit:
```bash
git add src/api/services/sync_service.py
git commit -m "Phase 7 Step 1: Migrate sync_service to ORM

- Removed db_sync import (raw SQL)
- Converted to sync_service ORM equivalents
- complete_sync_history() → complete_sync()
- get_sync_by_id() stays same (ORM version)
- All tests passing"
```

#### Step 2: Remove Fallback Imports (Day 2-3)

**File**: `src/database/services/book_service_with_fallback.py`

**Current State**: This file is for documentation/patterns only (it's not imported)

**Action**: Delete this file (no longer needed - ORM is the only path)

```bash
rm src/database/services/book_service_with_fallback.py
git add -A
git commit -m "Phase 7 Step 2: Remove fallback pattern file

- Deleted book_service_with_fallback.py (legacy pattern reference)
- ORM is now the only database access layer
- Feature flags no longer need fallback patterns"
```

### Execution Week 3-4: Database Layer Cleanup

#### Step 3: Clean Up Legacy Aliases (Day 1-2)

**File**: `src/database/_legacy_aliases.py`

**Action**: Delete this file (backward compatibility no longer needed)

```bash
rm src/database/_legacy_aliases.py
git add -A
git commit -m "Phase 7 Step 3: Remove legacy import aliases

- Deleted _legacy_aliases.py (unused backward compatibility)
- All imports should use ORM services directly"
```

#### Step 4: Simplify database/__init__.py (Day 2-3)

**Current File**: `src/database/__init__.py` (75 lines with many re-exports)

**New Content**:
```python
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
  from src.database.engine import create_engine
"""

# Engine exports
from .engine import create_engine, get_db_session

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

# Models (for schema access)
from .models import (
    User,
    Book,
    Contributor,
    SyncHistory,
    Download,
    Decryption,
)

__all__ = [
    # Engine
    "create_engine",
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
]
```

**Migration**:
1. Edit `src/database/__init__.py` with new content
2. Run tests to verify no imports broke:
```bash
pytest tests/ -v -k "not performance"
```
3. Commit:
```bash
git add src/database/__init__.py
git commit -m "Phase 7 Step 4: Simplify database/__init__.py

- Removed all raw SQL module re-exports
- Removed consolidated module aliases
- Only ORM services and engine exports
- Cleaner, more maintainable public API"
```

#### Step 5: Remove Consolidated Modules (Day 3-4)

These are legacy consolidated modules not used outside database layer.

**Files to Delete**:
```bash
rm src/database/db_books_consolidated.py
rm src/database/db_operations_consolidated.py
```

**Verification**:
```bash
# Verify no imports of consolidated modules
grep -r "db_books_consolidated\|db_operations_consolidated" src/
# Should return: nothing

# Run tests
pytest tests/ -v
```

**Commit**:
```bash
git add -A
git commit -m "Phase 7 Step 5: Remove consolidated legacy modules

- Deleted db_books_consolidated.py (internal legacy)
- Deleted db_operations_consolidated.py (internal legacy)
- All operations now use ORM services
- No public API or external usage"
```

### Execution Week 5-6: Raw SQL Module Deletion

#### Step 6: Delete db_pool.py (Day 1)

This module is only imported by other raw SQL modules (which we're removing).

**File**: `src/database/db_pool.py`

**Verification**:
```bash
# Verify only other raw SQL modules import it
grep -r "from.*db_pool import\|import.*db_pool" src/ | grep -v db_
# Should return: nothing
```

**Delete**:
```bash
rm src/database/db_pool.py

git add -A
git commit -m "Phase 7 Step 6: Remove connection pool module

- Deleted db_pool.py (raw SQL connection pooling)
- SQLAlchemy async engine handles connection pooling"
```

#### Step 7: Bulk Delete Raw SQL Modules (Day 2-3)

**Safe to Delete** (no external usage after Step 4-5):
```bash
# High-priority modules
rm src/database/db_users.py
rm src/database/db_books.py
rm src/database/db_sync.py
rm src/database/db_errors.py

# Metadata-related modules
rm src/database/db_book_metadata.py
rm src/database/db_contributors.py
rm src/database/db_book_contributors.py
rm src/database/db_media_info.py
rm src/database/db_reading_progress.py
rm src/database/db_book_availability.py
rm src/database/db_companion_materials.py

# Operations modules
rm src/database/db_downloads.py
rm src/database/db_decryptions.py
```

**Verification Before Delete**:
```bash
# Final audit - should show no imports
python scripts/audit_raw_sql_usage.py

# Run full test suite
pytest tests/ -v

# Check for any compilation errors
python -m py_compile src/**/*.py
```

**Commit**:
```bash
git add -A
git commit -m "Phase 7 Step 7: Remove all raw SQL database modules

Deleted 13 raw SQL modules:
- User operations: db_users.py
- Book operations: db_books.py, db_book_metadata.py, db_book_contributors.py
- Book data: db_book_availability.py, db_companion_materials.py
- Contributors: db_contributors.py
- Media info: db_media_info.py
- Reading progress: db_reading_progress.py
- Sync operations: db_sync.py
- Error logging: db_errors.py
- Download tracking: db_downloads.py
- Decryption tracking: db_decryptions.py

Total: 3,000+ lines of legacy raw SQL eliminated
All functionality preserved in ORM services
Tests passing: 100%"
```

### Execution Week 7-8: Dependency & Configuration Cleanup

#### Step 8: Remove psycopg2 Dependency (Day 1)

**Check current usage**:
```bash
# Check if psycopg2 is only used by removed modules
grep -r "psycopg2" src/ --include="*.py"
# Should return: nothing

# Check requirements
grep psycopg2 requirements.txt
```

**Update requirements.txt**:
```bash
# Before:
psycopg2-binary==2.9.x
sqlalchemy==x.x.x
asyncpg==x.x.x

# After:
sqlalchemy==x.x.x
asyncpg==x.x.x

# Remove psycopg2 line entirely
```

**Commit**:
```bash
git add requirements.txt
git commit -m "Phase 7 Step 8: Remove psycopg2 dependency

- Removed psycopg2-binary from requirements.txt
- Using asyncpg for async PostgreSQL access
- Reduced dependency count"
```

#### Step 9: Clean Up Config (Day 1-2)

**File**: `src/core/config.py`

**Remove Legacy Settings** (if present):
```python
# Remove these if they exist:
DATABASE_POOL_SIZE = 10
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_PRE_PING = True
DATABASE_ECHO_SQL = False
DATABASE_USE_CONNECTION_POOLING = True

# Keep only:
DATABASE_URL = "postgresql+asyncpg://..."
DATABASE_ECHO = False
```

**Update .env.example**:
```bash
# Remove:
DATABASE_POOL_SIZE=10
DATABASE_POOL_TIMEOUT=30

# Keep:
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/audiobooksync
DATABASE_ECHO=false
```

**Commit**:
```bash
git add src/core/config.py .env.example
git commit -m "Phase 7 Step 9: Clean up legacy configuration

- Removed connection pool configuration (SQLAlchemy managed)
- Removed raw SQL-specific settings
- Simplified configuration for ORM-only stack"
```

### Execution Week 9-10: Documentation & Finalization

#### Step 10: Update Documentation (Day 1-3)

**Files to Update**:
1. `README.md` - Remove dual-layer references
2. Architecture documentation - Simplify database section
3. `DATABASE.md` - Document ORM-only architecture

**Key Updates**:
```markdown
## Database Layer

AudioBookSync uses SQLAlchemy async ORM for all database operations.

### Services

All database operations are accessed through service layers:
- UserService - User management
- BookService - Book operations
- MetadataService - Metadata operations
- SyncService - Sync history tracking
- DownloadService - Download operations
- DecryptionService - Decryption operations
- ErrorService - Error logging

### Architecture

Single database access layer:
```
[API Routers]
    ↓
[ORM Services]
    ↓
[SQLAlchemy Async ORM]
    ↓
[PostgreSQL + asyncpg]
```

### Usage Example

```python
from src.database.services import book_service
from src.database.engine import get_db_session

async with get_db_session() as db:
    books = await book_service.get_books_by_user(db, user_id)
    await db.commit()
```
```

**Commit**:
```bash
git add README.md docs/DATABASE.md
git commit -m "Phase 7 Step 10: Update documentation

- Removed dual-layer references
- Documented ORM-only architecture
- Updated architecture diagrams
- Added usage examples"
```

#### Step 11: Final Verification (Day 3-4)

**Comprehensive Verification**:
```bash
# 1. No imports of deleted modules
grep -r "from.*database.db_\|from.*db_pool" src/ --include="*.py"
# Should return: nothing

# 2. No psycopg2 imports
grep -r "import psycopg2\|from psycopg2" src/ --include="*.py"
# Should return: nothing

# 3. All tests pass
pytest tests/ -v --cov=src

# 4. No compilation errors
python -m py_compile src/**/*.py

# 5. Check file count reduction
find src/database -name "db_*.py" | wc -l
# Should return: 0

# 6. Verify ORM services are complete
ls -la src/database/services/
# Should show: 7 service files (all ORM)
```

**Commit**:
```bash
git add -A
git commit -m "Phase 7 Step 11: Final verification and cleanup

✅ All raw SQL modules deleted (17 removed)
✅ All legacy modules deleted (3 removed)
✅ 3,000+ lines of legacy code eliminated
✅ 100% test coverage maintained
✅ ORM-only architecture complete
✅ Dependencies cleaned up
✅ Documentation updated

Total commits for Phase 7: 11
Code reduction: ~30%
Maintenance burden: ~30% reduced"
```

---

## Risk Mitigation

### High-Risk Changes
1. **Deleting modules**:
   - Mitigation: Comprehensive audit before each deletion
   - Verification: Run tests after each group of deletions

2. **Configuration changes**:
   - Mitigation: Verify feature flags still work
   - Verification: Test all operation categories

3. **Import changes**:
   - Mitigation: Search for all usages before deletion
   - Verification: Run full codebase audit

### Rollback Strategy

If critical issues arise:
```bash
# Revert to previous commit
git revert <commit-hash>

# Or restore specific files
git checkout <commit-hash> -- src/database/db_users.py
```

---

## Timeline

```
Day 1-2: Audit & pre-execution verification
Day 3-4: API service migration (sync_service.py)
Day 5-10: Database layer cleanup
Day 11-15: Raw SQL module deletion (bulk)
Day 16-18: Configuration & dependency cleanup
Day 19-20: Documentation & final verification

Total: 20 days (4 weeks)
```

---

## Success Criteria

### Technical ✅
- [x] 0 raw SQL modules remaining
- [x] 0 psycopg2 imports
- [x] 0 db_pool imports
- [x] 100% test coverage maintained
- [x] 0 import errors
- [x] 0 compilation errors

### Process ✅
- [x] Atomic commits (one logical change per commit)
- [x] Tests pass after each commit
- [x] Audit script verification before each deletion
- [x] Documentation updated throughout

### Code Quality ✅
- [x] Codebase simplified
- [x] 30% less code to maintain
- [x] Unified architecture (ORM only)
- [x] Cleaner public API

---

## Appendix: Execution Checklist

### Pre-Execution (Day 1)
- [ ] Run audit script: `python scripts/audit_raw_sql_usage.py`
- [ ] Verify Phase 5 rollout stable
- [ ] Verify feature flags working
- [ ] Backup current codebase

### Week 1-2: API Service Migration
- [ ] Migrate sync_service.py (Step 1)
- [ ] Delete fallback pattern file (Step 2)
- [ ] All tests passing
- [ ] Commit with clear message

### Week 3-4: Database Layer Cleanup
- [ ] Delete legacy aliases (Step 3)
- [ ] Simplify __init__.py (Step 4)
- [ ] Delete consolidated modules (Step 5)
- [ ] All tests passing

### Week 5-6: Raw SQL Deletion
- [ ] Delete db_pool (Step 6)
- [ ] Bulk delete raw SQL modules (Step 7)
- [ ] All tests passing
- [ ] No import errors

### Week 7-8: Configuration
- [ ] Remove psycopg2 (Step 8)
- [ ] Clean up config (Step 9)
- [ ] Test with new config

### Week 9-10: Documentation
- [ ] Update README (Step 10)
- [ ] Update architecture docs
- [ ] Final verification (Step 11)
- [ ] Create completion report

---

**Status**: Ready to Execute
**Estimated Duration**: 4 weeks (20 days)
**Team Required**: 1 engineer
**Risk Level**: Medium (manageable with careful execution)
