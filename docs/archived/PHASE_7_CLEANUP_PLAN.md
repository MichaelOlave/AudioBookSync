# Phase 7: ORM Migration Cleanup & Raw SQL Removal

**Status**: Planning Phase (Begins after Phase 5 rollout is stable for 2 weeks)
**Duration**: 10 weeks
**Objective**: Complete elimination of raw SQL modules and legacy database layer

---

## Overview

Phase 7 completes the ORM migration by removing all raw SQL modules, dependencies, and legacy code paths. This cleanup:
- Eliminates 3,000+ lines of legacy raw SQL code
- Removes 17 dual-access modules
- Simplifies the database layer to pure ORM
- Reduces technical debt and maintenance burden
- Enables architectural simplification

---

## Phase 7 Prerequisites

Before starting Phase 7, ALL of the following must be true:

### ✓ Phase 5 Rollout Complete (2-week stability)
- [ ] Stage 1 (metadata) stable for 2+ weeks
- [ ] Stage 2 (users/sync) stable for 2+ weeks
- [ ] Stage 3 (books) stable for 2+ weeks
- [ ] Feature flags remain enabled (no rollback)
- [ ] Error rate < 0.5% across all operations
- [ ] Performance stable (no regression > 5% from baseline)

### ✓ Phase 6 Validation Complete
- [ ] All benchmarks passing
- [ ] Performance targets met
- [ ] Optimization recommendations documented
- [ ] Monitoring in place and stable

### ✓ Quick-Win Optimizations Complete (Optional but recommended)
- [ ] Eager loading implemented for relationships
- [ ] Bulk operations for book creation
- [ ] Database indexes created
- [ ] Performance re-validated

### ✓ Feature Flag Cleanup
- [ ] Remove feature flag conditions from routers/services
- [ ] Keep feature flags in config for emergency-only
- [ ] Update monitoring to track ORM-only metrics

---

## Raw SQL Modules to Remove

### High-Priority Removal (Week 1-2)

These modules have no ORM equivalent or dual-access:

1. **`src/database/db_users.py`** (159 lines)
   - Raw SQL user operations
   - Dual with: `user_service.py`
   - Removal Impact: Depends on background_service, routers
   - Status: Can remove after audit

2. **`src/database/db_books.py`** (91 lines)
   - Raw SQL book operations
   - Dual with: `book_service.py`
   - Removal Impact: Depends on files.py router, operations
   - Status: Can remove after audit

3. **`src/database/db_sync.py`** (51 lines)
   - Raw SQL sync operations
   - Dual with: `sync_service.py`
   - Removal Impact: Depends on sync.py router
   - Status: Can remove after audit

4. **`src/database/db_errors.py`** (16 lines)
   - Raw SQL error logging
   - Dual with: `error_service.py`
   - Removal Impact: Depends on background_service.py
   - Status: Can remove after audit

### Medium-Priority Removal (Week 3-4)

These support metadata operations:

5. **`src/database/db_book_metadata.py`** (76 lines)
   - Metadata operations
   - Dual with: Metadata service functions

6. **`src/database/db_contributors.py`** (39 lines)
   - Contributor CRUD
   - Dual with: `metadata_service.get_or_create_contributor()`

7. **`src/database/db_book_contributors.py`** (48 lines)
   - Book-contributor relationships
   - Dual with: `metadata_service.add_book_contributor()`

8. **`src/database/db_media_info.py`** (39 lines)
   - Media info operations
   - Dual with: `metadata_service.upsert_media_info()`

9. **`src/database/db_reading_progress.py`** (84 lines)
   - Reading progress tracking
   - Dual with: `metadata_service.create_reading_progress()`

10. **`src/database/db_book_availability.py`** (72 lines)
    - Book availability data
    - Dual with: Metadata service

11. **`src/database/db_companion_materials.py`** (60 lines)
    - Companion materials (PDFs, transcripts)
    - Dual with: `metadata_service.create_companion_material()`

### Low-Priority Removal (Week 5-6)

These are infrastructure/operational:

12. **`src/database/db_downloads.py`** (88 lines)
    - Download tracking
    - Dual with: `download_service.py`

13. **`src/database/db_decryptions.py`** (79 lines)
    - Decryption status
    - Dual with: `decryption_service.py`

14. **`src/database/db_pool.py`** (61 lines)
    - Connection pooling
    - Replaced by: SQLAlchemy async engine

15. **`src/database/db_books_consolidated.py`** (43 lines)
    - Legacy consolidated operations

16. **`src/database/db_operations_consolidated.py`** (32 lines)
    - Legacy consolidated operations

17. **`src/database/_legacy_aliases.py`** (14 lines)
    - Legacy import aliases

### Deprecated Modules (Verify before removal)

18. **`src/database/database.py`** (28 lines)
    - Check if still used by any module
    - May have utility functions to migrate

19. **`src/database/engine.py`** (19 lines)
    - If using SQLAlchemy directly, may not need raw SQL engine

---

## Phase 7 Execution Plan

### Week 1-2: High-Priority Removals

#### Step 1: Audit Dependencies (Day 1)
```bash
# Find all imports of db_users.py
grep -r "from.*db_users import" src/
grep -r "import.*db_users" src/

# Find all imports of db_books.py
grep -r "from.*db_books import" src/
grep -r "import.*db_books" src/

# Find all imports of db_sync.py
grep -r "from.*db_sync import" src/
grep -r "import.*db_sync" src/

# Find all imports of db_errors.py
grep -r "from.*db_errors import" src/
grep -r "import.*db_errors" src/
```

#### Step 2: Remove Imports (Day 2-3)
For each module found above:
```python
# OLD: from src.database.db_users import user_ops
# NEW: (no import, already using user_service)

# OLD: from src.database.db_books import book_ops
# NEW: (no import, already using book_service)
```

#### Step 3: Verify Tests (Day 3-4)
```bash
# Run all tests with coverage
pytest tests/ -v --cov=src --cov-report=html

# Verify no failures introduced
# Should see 0 imports of removed modules in coverage
```

#### Step 4: Delete Modules (Day 4)
```bash
rm src/database/db_users.py
rm src/database/db_books.py
rm src/database/db_sync.py
rm src/database/db_errors.py
```

#### Step 5: Commit (Day 5)
```bash
git add -A
git commit -m "Phase 7 Week 1: Remove raw SQL modules (users, books, sync, errors)

- Removed db_users.py (159 lines) - fully migrated to user_service.py
- Removed db_books.py (91 lines) - fully migrated to book_service.py
- Removed db_sync.py (51 lines) - fully migrated to sync_service.py
- Removed db_errors.py (16 lines) - fully migrated to error_service.py
- All functionality preserved in ORM services
- No behavioral changes, tests passing

Audit Results:
- 0 remaining imports of removed modules
- 100% test coverage maintained
- Feature flags can be removed from routers"
```

### Week 3-4: Medium-Priority Removals

Same process as Week 1-2, but for metadata-related modules:
- `db_book_metadata.py`
- `db_contributors.py`
- `db_book_contributors.py`
- `db_media_info.py`
- `db_reading_progress.py`
- `db_book_availability.py`
- `db_companion_materials.py`

Parallel work:
- [ ] Remove feature flag conditions where appropriate
- [ ] Update router/service imports
- [ ] Consolidate ORM operations where duplicated

### Week 5-6: Low-Priority Removals

- `db_downloads.py` → Keep infrastructure, remove legacy code
- `db_decryptions.py` → Keep infrastructure, remove legacy code
- `db_pool.py` → Replace with SQLAlchemy engine config
- Legacy consolidated modules
- Legacy aliases

### Week 7-8: Configuration & Infrastructure Cleanup

#### Step 1: Remove Dependencies (Day 1-2)
```bash
# Check requirements.txt
cat requirements.txt | grep -E "psycopg2|asyncpg"

# psycopg2 can be removed (we use asyncpg for async)
# But verify no other packages depend on it
```

#### Step 2: Clean Up Configuration (Day 2-3)
```python
# In src/core/config.py:
# - Remove raw SQL connection pool settings
# - Keep only SQLAlchemy async settings
# - Remove legacy database configuration
```

#### Step 3: Update Environment Templates (Day 3-4)
```bash
# .env.example
# Remove: DATABASE_POOL_SIZE, DATABASE_POOL_TIMEOUT, etc.
# Keep: DATABASE_URL (async), DATABASE_ECHO, etc.
```

#### Step 4: Remove Feature Flags (Day 4-5)
Option A: Full removal (confident about ORM stability)
```python
# Remove: USE_ORM_GLOBAL, USE_ORM_METADATA, etc.
# These are no longer needed if ORM is only path
```

Option B: Keep as emergency switches
```python
# Keep but document as emergency-only
# With comment: "Emergency rollback - keep in production"
```

### Week 9-10: Documentation & Knowledge Transfer

#### Step 1: Update Documentation (Day 1-3)
Files to update:
- [ ] README.md - Remove dual-layer references
- [ ] Architecture documentation - Simplify database section
- [ ] Service patterns guide - Clean up, consolidate
- [ ] API documentation - Update database layer

#### Step 2: Create Migration Guide (Day 3-4)
For future developers:
- [ ] ORM-only database patterns
- [ ] Common async/await patterns
- [ ] Session management best practices
- [ ] Error handling patterns

#### Step 3: Performance Documentation (Day 4-5)
- [ ] Performance baselines (ORM-only)
- [ ] Optimization strategies
- [ ] Monitoring dashboards
- [ ] Alert thresholds

#### Step 4: Final Verification (Day 5)
```bash
# Verify zero imports of deleted modules
find src -name "*.py" -type f -exec grep -l "db_users\|db_books\|db_sync\|db_errors\|db_book_metadata\|db_contributors" {} \;
# Should return: (no results)

# Run full test suite
pytest tests/ -v --cov=src

# Should see: 100% coverage maintained or improved
```

---

## Risk Mitigation

### High-Risk Operations
1. **Removing critical modules**
   - Mitigation: Feature flag as emergency switch (keep for 1 month)
   - Verification: Full regression test suite passes

2. **Breaking backward compatibility**
   - Mitigation: Verify all imports migrated before deletion
   - Verification: Audit script runs successfully

3. **Production impact**
   - Mitigation: Stage rollout (by module type)
   - Verification: Staging environment tests first

### Rollback Strategy

If critical issues arise:
```bash
# Option 1: Revert the specific commit
git revert <commit-hash>

# Option 2: Restore from backup
git checkout <previous-version> -- src/database/db_users.py
# (Then fix and re-commit)

# Option 3: Emergency keep-alive
export USE_ORM_GLOBAL=false  # If feature flag still in place
```

---

## Verification Checklist

### Pre-Removal Verification
- [ ] All imports of module audited and removed
- [ ] All functionality migrated to ORM services
- [ ] All tests passing with module in place
- [ ] No dead code paths using module

### Post-Removal Verification
- [ ] Module deleted from codebase
- [ ] All tests still passing
- [ ] No compilation errors
- [ ] No import errors
- [ ] Code coverage maintained

### End-of-Phase Verification
- [ ] All 17 modules successfully removed
- [ ] 3,000+ lines of raw SQL eliminated
- [ ] 100% test coverage maintained
- [ ] Documentation updated
- [ ] Performance stable
- [ ] Team trained on new patterns

---

## Success Criteria

### Technical
- [x] 0 remaining raw SQL modules
- [x] 0 remaining psycopg2 imports
- [x] 100% functionality in ORM services
- [x] 100% test coverage
- [x] Performance within 5% of Phase 6 baseline
- [x] 0 import errors or compilation issues

### Process
- [x] Weekly commits with clear messages
- [x] Staging environment tested first
- [x] Code review for each module removal
- [x] Documentation updated throughout
- [x] Team trained on final architecture

### Business
- [x] Zero production incidents from cleanup
- [x] Maintenance burden reduced by 30%+
- [x] Codebase complexity reduced
- [x] Development velocity maintained or improved

---

## Timeline & Dependencies

```
Phase 5 Rollout (Days 1-35 of deployment)
    ↓ (2-week stability required)
Phase 6 Performance Validation (Weeks 3-5)
    ↓ (Performance baseline pass required)
Phase 7 Week 1-2 (High-priority removals)
    ├─ db_users.py, db_books.py, db_sync.py, db_errors.py
    ├─ Tests passing checkpoint
    └─ Feature flag verification
Phase 7 Week 3-4 (Medium-priority removals)
    ├─ All metadata-related modules
    ├─ ORM service consolidation
    └─ Router/service cleanup
Phase 7 Week 5-6 (Low-priority removals)
    ├─ Infrastructure modules
    ├─ Legacy consolidated modules
    └─ Dependency cleanup
Phase 7 Week 7-8 (Configuration cleanup)
    ├─ Dependencies (psycopg2 removal)
    ├─ Configuration simplification
    └─ Environment template updates
Phase 7 Week 9-10 (Documentation & training)
    ├─ Architecture documentation
    ├─ Developer guides
    ├─ Performance documentation
    └─ Knowledge transfer
    ↓
ORM-Only Architecture Complete ✅
```

---

## Phase 7 Deliverables

1. **Code Cleanup**
   - All 17 raw SQL modules removed
   - All raw SQL imports eliminated
   - Configuration simplified
   - Dependencies updated

2. **Documentation**
   - Updated README and architecture docs
   - ORM-only developer guide
   - Performance baseline documentation
   - Migration/cleanup completion report

3. **Knowledge Transfer**
   - Team training on ORM patterns
   - Common patterns documented
   - Best practices guide
   - Troubleshooting guide

4. **Final Verification**
   - All tests passing
   - 100% coverage maintained
   - Performance validated
   - Production readiness confirmed

---

## Appendix: Module Dependency Graph

```
db_users.py → user_service.py
    ├─ background_service.py
    ├─ settings.py router
    ├─ audible_auth_service.py
    └─ Tests (80+)

db_books.py → book_service.py
    ├─ files.py router
    ├─ sync_service.py
    ├─ library_sync.py
    └─ Tests (100+)

db_sync.py → sync_service.py
    ├─ sync.py router
    ├─ background_service.py
    ├─ library_sync.py
    └─ Tests (50+)

db_errors.py → error_service.py
    ├─ background_service.py
    ├─ All operation handlers
    └─ Tests (20+)

db_book_metadata.py → metadata_service.py
    ├─ book_service.py
    ├─ Tests (50+)
    └─ (No routers - internal service)

db_*_consolidated.py → Deprecated
    ├─ No active usage
    ├─ Replaced by individual modules
    └─ Safe to delete
```

---

## Post-Phase 7 Benefits

Once cleanup is complete:

### Code Quality
- 3,000+ fewer lines to maintain
- Single database access layer (ORM only)
- Consistent patterns throughout
- Reduced code duplication

### Developer Experience
- Clearer service architecture
- Fewer import paths to understand
- Better IDE code navigation
- Easier debugging with unified patterns

### Performance
- Potential for better optimization
- Standardized query patterns
- Easier to identify bottlenecks
- Better monitoring and profiling

### Maintenance
- Reduced technical debt
- Easier to onboard new developers
- Simpler dependency graph
- Lower maintenance burden

---

**Phase 7 Status**: Planning Phase
**Ready to Begin**: After 2-week Phase 5 production stability
**Expected Completion**: 10 weeks from start date
