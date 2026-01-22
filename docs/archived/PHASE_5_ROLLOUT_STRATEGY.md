# Phase 5: ORM Migration Rollout Strategy

## Overview

This document outlines the gradual rollout strategy for the ORM migration in AudioBookSync. The approach uses feature flags to enable progressive deployment with easy rollback capabilities.

## Architecture

### Feature Flag System

**Location**: `src/core/feature_flags.py`

**Flags**:
- `USE_ORM_GLOBAL` - Master switch (emergency off)
- `USE_ORM_METADATA` - Metadata operations (low risk)
- `USE_ORM_USERS` - User operations (medium risk)
- `USE_ORM_SYNC` - Sync operations (medium risk)
- `USE_ORM_BOOKS` - Book operations (high risk)

**Monitoring Endpoints**:
- `GET /api/v1/feature-flags/status` - Current flag status and rollout stage
- `GET /api/v1/feature-flags/stats` - Usage statistics
- `POST /api/v1/feature-flags/stats/reset` - Reset monitoring stats

## Rollout Timeline

### Stage 1: Metadata Operations (Days 1-2)
**Risk Level**: ✅ LOW

**Enabled Flags**:
```bash
USE_ORM_METADATA=true
USE_ORM_USERS=false
USE_ORM_SYNC=false
USE_ORM_BOOKS=false
```

**Operations**:
- Get-or-create contributors
- JSONB custom metadata operations
- Media info upserts
- Badge operations
- Reading progress tracking

**Monitoring Focus**:
- Query performance (p50, p95, p99 latency)
- JSONB field handling edge cases
- NULL initialization behavior
- Database constraint violations

**Success Criteria**:
- Zero new errors in production
- < 15% performance regression
- < 1% error rate on metadata operations
- Database constraints working correctly

**Rollback Trigger**:
```bash
USE_ORM_GLOBAL=false
```

---

### Stage 2: User & Sync Operations (Days 3-4)
**Risk Level**: ⚠️ MEDIUM

**Enabled Flags**:
```bash
USE_ORM_METADATA=true
USE_ORM_USERS=true
USE_ORM_SYNC=true
USE_ORM_BOOKS=false
```

**Operations**:
- User creation and updates
- Audible auth JSON handling
- User credential storage/retrieval
- Sync history tracking
- Sync status updates

**Monitoring Focus**:
- Authentication flow correctness
- JSON field parsing
- Multi-field atomic updates
- Concurrent sync handling
- API endpoint performance

**Success Criteria**:
- All user operations succeed
- Credential storage/retrieval working
- Sync history accurately recorded
- < 20% performance regression
- Zero authentication errors

**Rollback Trigger**:
```bash
USE_ORM_SYNC=false
# or global:
USE_ORM_GLOBAL=false
```

---

### Stage 3: Book Operations (Days 5-7)
**Risk Level**: 🔴 HIGH

**Enabled Flags**:
```bash
USE_ORM_METADATA=true
USE_ORM_USERS=true
USE_ORM_SYNC=true
USE_ORM_BOOKS=true
```

**Operations**:
- Book creation and orchestration
- 7-table metadata coordination
- Contributor associations
- Media info integration
- Book search and retrieval

**Monitoring Focus**:
- 7-table transaction integrity
- Cascading operations
- Library synchronization
- Search performance
- Bulk operations

**Success Criteria**:
- Complex book metadata operations work
- All relationships maintained
- Library sync succeeds 100%
- Search performance acceptable
- Rollback time < 5 minutes

**Rollback Trigger**:
```bash
USE_ORM_BOOKS=false
# or full:
USE_ORM_GLOBAL=false
```

---

## Implementation Pattern

### Using Feature Flags in Services

```python
from src.core.feature_flags import is_orm_books_enabled, feature_flags
from src.database.db_books import book_ops  # Legacy SQL
from src.database.services import book_service  # ORM

async def get_user_books(user_id: str):
    """Get books with graceful fallback."""
    if is_orm_books_enabled():
        # Use ORM implementation
        async with get_db_session() as db:
            return await book_service.get_books_by_user(db, user_id)
    else:
        # Use legacy SQL implementation
        return book_ops.get_user_books(user_id)


async def add_book_with_metadata(user_id: str, book_data: dict):
    """Add book with fallback pattern."""
    try:
        if is_orm_books_enabled():
            async with get_db_session() as db:
                return await book_service.add_book_with_metadata(
                    db, user_id=user_id, **book_data
                )
        else:
            return book_ops.add_book_with_metadata(user_id, book_data)
    except Exception as e:
        logger.error(f"ORM operation failed: {e}. Falling back to SQL.")
        return book_ops.add_book_with_metadata(user_id, book_data)
```

### Using Fallback Wrapper

```python
from src.core.feature_flags import feature_flags, FeatureFlag

# Create wrapped function with automatic fallback
wrapped_func = feature_flags.with_fallback(
    FeatureFlag.BOOKS,
    orm_func=async_orm_implementation,
    sql_func=async_sql_implementation,
)

# Use wrapped function - automatically picks right implementation
result = await wrapped_func(user_id=user_id, data=book_data)
```

---

## Deployment Checklist

### Pre-Rollout Verification

- [ ] All Phase 4 tests passing
- [ ] Performance benchmarks established
- [ ] Rollback procedures documented
- [ ] Monitoring dashboards configured
- [ ] On-call team briefed

### Stage 1 Deployment (Metadata)

- [ ] Set `USE_ORM_METADATA=true`
- [ ] Monitor for 24 hours
- [ ] Check feature flag stats endpoint
- [ ] Verify no error rate increase
- [ ] Confirm query performance acceptable

### Stage 2 Deployment (Users/Sync)

- [ ] Set `USE_ORM_USERS=true`
- [ ] Set `USE_ORM_SYNC=true`
- [ ] Monitor for 24 hours
- [ ] Test user login/auth flows
- [ ] Verify sync operations work
- [ ] Check for credential issues

### Stage 3 Deployment (Books)

- [ ] Set `USE_ORM_BOOKS=true`
- [ ] Monitor for 48 hours
- [ ] Test full library sync
- [ ] Verify book metadata accuracy
- [ ] Check concurrent sync handling
- [ ] Monitor database connections

### Post-Rollout (Keep flags for 2 weeks)

- [ ] Continue monitoring for regressions
- [ ] Collect performance metrics
- [ ] Document lessons learned
- [ ] Plan Phase 6 benchmarking
- [ ] After 2 weeks, proceed to Phase 6

---

## Monitoring Dashboard

### Key Metrics

**Performance**:
```
Query Latency (ms):
- p50: < baseline + 15%
- p95: < baseline + 20%
- p99: < baseline + 25%

Throughput:
- Requests/sec: > 95% of baseline
- Connection pool: < 80% utilization
```

**Reliability**:
```
Error Rate:
- New errors: < 0.5%
- Timeouts: < 1%
- Constraint violations: 0

Success Rate:
- User operations: > 99.9%
- Sync operations: > 99.5%
- Book operations: > 99%
```

**Resource Usage**:
```
Memory:
- Increase: < 10%

Database Connections:
- Pool utilization: < 80%
- Connection time: < 100ms

CPU:
- Increase: < 5%
```

### Feature Flag Stats Endpoint

```bash
GET /api/v1/feature-flags/stats

Response:
{
  "USE_ORM_METADATA": {
    "enabled_count": 1250,
    "disabled_count": 5,
    "total_checks": 1255,
    "enabled_percentage": 99.6,
    "errors": 0
  },
  "USE_ORM_USERS": {
    "enabled_count": 500,
    "disabled_count": 0,
    "total_checks": 500,
    "enabled_percentage": 100,
    "errors": 0
  }
}
```

---

## Rollback Procedures

### Emergency Global Rollback (< 30 seconds)

```bash
# Set environment variable
export USE_ORM_GLOBAL=false

# Restart application(s)
systemctl restart audiobooksync-api
```

### Staged Rollback (selective operations)

```bash
# Rollback books only
export USE_ORM_BOOKS=false
systemctl restart audiobooksync-api

# Then after verification
export USE_ORM_SYNC=false
export USE_ORM_USERS=false
systemctl restart audiobooksync-api
```

### Rollback Verification

```bash
# Check current flag status
curl http://localhost:8000/api/v1/feature-flags/status

# Should show disabled flags:
{
  "global_enabled": true,
  "flags": {
    "metadata": true,
    "users": false,
    "sync": false,
    "books": false
  },
  "rollout_stage": "STAGE_1_METADATA"
}
```

---

## Failure Scenarios & Responses

### Scenario 1: High Error Rate on Metadata Operations

**Trigger**: Error rate > 5% for metadata operations

**Response**:
```bash
# Disable only metadata
export USE_ORM_METADATA=false
# System falls back to SQL automatically

# Investigate ORM service logs
grep "ERROR" logs/orm-metadata.log

# Fix issue and test
pytest tests/database/test_metadata_operations.py

# Re-enable after fix
export USE_ORM_METADATA=true
```

### Scenario 2: User Authentication Issues

**Trigger**: Login failures > 1%, auth errors in logs

**Response**:
```bash
# Emergency rollback
export USE_ORM_GLOBAL=false

# Investigate credential storage
grep "auth_json\|audible_" logs/orm-users.log

# Review user_service.get_audible_auth_json()
# Check JSON parsing logic

# Fix and re-enable
export USE_ORM_USERS=true
export USE_ORM_GLOBAL=true
```

### Scenario 3: Library Sync Failures

**Trigger**: Sync success rate drops below 95%

**Response**:
```bash
# Disable books operations
export USE_ORM_BOOKS=false

# Check sync logs for specific failures
grep "FAILED\|ERROR" logs/sync.log

# Verify database constraints
psql -d audiobooksync -c "SELECT * FROM books WHERE user_id = 'X';"

# Fix issue in book_service.add_book_with_metadata()

# Re-enable with monitoring
export USE_ORM_BOOKS=true
```

---

## Performance Benchmarking

### Baseline Measurements (Before Rollout)

Should be taken using SQL implementations:

```python
# Metadata operations
- get_or_create_contributor: < 10ms
- add_custom_metadata: < 5ms
- upsert_media_info: < 10ms

# User operations
- get_user_by_id: < 5ms
- update_audible_auth_json: < 20ms
- get_audible_auth_json: < 5ms

# Sync operations
- create_sync_history: < 10ms
- get_user_sync_history: < 30ms (for 50 syncs)
- update_sync_status: < 15ms

# Book operations
- get_books_by_user: < 50ms (for 100 books)
- add_book_with_metadata: < 100ms
- search_books: < 100ms (for 1000 books)
```

### Target ORM Performance (After Rollout)

Should be within acceptable overhead:

```
- Metadata: < 15ms (50% overhead acceptable)
- Users: < 25ms (25% overhead acceptable)
- Sync: < 50ms (66% overhead acceptable)
- Books: < 120ms (20% overhead acceptable)
```

### Regression Threshold

**Automatic Rollback Trigger**:
- Performance regression > 25% on critical paths
- Error rate > 1% on any operation
- Database connection pool exhaustion
- Memory leak detected (usage > 20% growth)

---

## Post-Rollout Checklist

After reaching 100% ORM (all flags enabled for 2 weeks):

- [ ] Zero production incidents related to ORM
- [ ] Performance metrics stable
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Team trained on ORM patterns
- [ ] Proceed to Phase 6 (Performance Validation)
- [ ] Plan Phase 7 (Cleanup & Deprecation)

---

## Environment Configuration Examples

### Development (All ORM enabled)

```bash
USE_ORM_GLOBAL=true
USE_ORM_METADATA=true
USE_ORM_USERS=true
USE_ORM_SYNC=true
USE_ORM_BOOKS=true
LOG_FEATURE_FLAGS=true
```

### Stage 1 (Metadata only)

```bash
USE_ORM_GLOBAL=true
USE_ORM_METADATA=true
USE_ORM_USERS=false
USE_ORM_SYNC=false
USE_ORM_BOOKS=false
LOG_FEATURE_FLAGS=true
```

### Stage 2 (Metadata + Users/Sync)

```bash
USE_ORM_GLOBAL=true
USE_ORM_METADATA=true
USE_ORM_USERS=true
USE_ORM_SYNC=true
USE_ORM_BOOKS=false
LOG_FEATURE_FLAGS=true
```

### Stage 3 (Full ORM)

```bash
USE_ORM_GLOBAL=true
USE_ORM_METADATA=true
USE_ORM_USERS=true
USE_ORM_SYNC=true
USE_ORM_BOOKS=true
LOG_FEATURE_FLAGS=false  # Can disable logging for production
```

### Emergency Rollback

```bash
USE_ORM_GLOBAL=false
# All operations fall back to SQL automatically
```

---

## Monitoring Commands

### Check Current Status

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/feature-flags/status
```

### Get Usage Stats

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/feature-flags/stats
```

### Reset Stats for New Benchmark

```bash
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/feature-flags/stats/reset
```

### Monitor Error Rate in Logs

```bash
# Metadata errors
tail -f logs/app.log | grep "ORM_METADATA.*ERROR"

# User operation errors
tail -f logs/app.log | grep "ORM_USERS.*ERROR"

# Feature flag decisions
tail -f logs/app.log | grep "Feature flag"
```

---

## Success Criteria Summary

| Phase | Timeline | ORM% | Risk | Success Metrics |
|-------|----------|------|------|-----------------|
| 1 | Days 1-2 | 25% | ✅ Low | No errors, < 15% latency increase |
| 2 | Days 3-4 | 50% | ⚠️ Medium | Auth works, < 20% latency increase |
| 3 | Days 5-7 | 100% | 🔴 High | Sync succeeds 100%, < 20% latency |
| Post | 2 weeks | 100% | ✅ Green | Zero regressions, ready for Phase 6 |

---

## Contact & Escalation

**Phase 5 Owner**: [Engineering Lead]
**On-Call**: [On-call Engineer]
**Escalation**: [Engineering Manager]

**Critical Issues**:
1. Call on-call immediately
2. Enable global rollback
3. Notify escalation contact
4. Gather logs and metrics

---

## Appendix: Feature Flag API Examples

### JavaScript/Fetch

```javascript
// Get current flag status
fetch('/api/v1/feature-flags/status', {
  headers: {'Authorization': `Bearer ${token}`}
}).then(r => r.json()).then(data => {
  console.log('Current rollout stage:', data.rollout_stage);
  console.log('ORM Books enabled:', data.flags.books);
});

// Get usage statistics
fetch('/api/v1/feature-flags/stats', {
  headers: {'Authorization': `Bearer ${token}`}
}).then(r => r.json()).then(stats => {
  console.log('Books error rate:', stats.USE_ORM_BOOKS.errors);
});
```

### Python/Requests

```python
import requests

# Get feature flag status
response = requests.get(
    'http://localhost:8000/api/v1/feature-flags/status',
    headers={'Authorization': f'Bearer {token}'}
)
status = response.json()
print(f"ORM enabled: {status['global_enabled']}")
print(f"Rollout stage: {status['rollout_stage']}")

# Get statistics
response = requests.get(
    'http://localhost:8000/api/v1/feature-flags/stats',
    headers={'Authorization': f'Bearer {token}'}
)
stats = response.json()
for flag, data in stats.items():
    print(f"{flag}: {data['enabled_percentage']}% enabled")
```

