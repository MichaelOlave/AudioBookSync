# Feature Flags - Quick Reference Guide

## For Developers

### Check if Feature is Enabled

```python
from src.core.feature_flags import (
    is_orm_metadata_enabled,
    is_orm_users_enabled,
    is_orm_sync_enabled,
    is_orm_books_enabled,
    is_orm_disabled,
)

# In your code
if is_orm_books_enabled():
    # Use ORM implementation
    books = await orm_book_service.get_books_by_user(db, user_id)
else:
    # Use SQL implementation
    books = sql_book_ops.get_user_books(user_id)
```

### Add Fallback to Your Service

```python
from src.core.feature_flags import is_orm_books_enabled
from loguru import logger

async def my_operation(db, *args, **kwargs):
    """My operation with ORM/SQL fallback."""
    try:
        if is_orm_books_enabled():
            # Try ORM first
            result = await orm_service.my_operation(db, *args, **kwargs)
            return result
        else:
            # Use SQL
            result = sql_ops.my_operation(*args, **kwargs)
            return result
    except Exception as e:
        logger.error(f"ORM failed: {e}. Falling back to SQL...")
        # Try SQL as fallback
        return sql_ops.my_operation(*args, **kwargs)
```

### Reference Implementation

See: `src/database/services/book_service_with_fallback.py`

## For Operators / DevOps

### Check Current Status

```bash
# Get current flag status
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/feature-flags/status

# Response shows which stage we're in:
# STAGE_1_METADATA
# STAGE_2_USERS_SYNC
# STAGE_3_FULL_ORM
```

### Check Statistics

```bash
# Get usage and error stats
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/feature-flags/stats
```

### Enable Next Stage

**Stage 1**: Metadata (Low Risk)
```bash
export USE_ORM_METADATA=true
systemctl restart audiobooksync-api
```

**Stage 2**: Users & Sync (Medium Risk)
```bash
export USE_ORM_USERS=true
export USE_ORM_SYNC=true
systemctl restart audiobooksync-api
```

**Stage 3**: Books (High Risk)
```bash
export USE_ORM_BOOKS=true
systemctl restart audiobooksync-api
```

### Emergency Rollback

```bash
# FASTEST: Global disable
export USE_ORM_GLOBAL=false
systemctl restart audiobooksync-api

# PARTIAL: Disable specific operation
export USE_ORM_BOOKS=false
systemctl restart audiobooksync-api
```

### Monitor Performance

```bash
# Watch logs for feature flag decisions
tail -f logs/app.log | grep "Using ORM\|Using SQL\|fallback"

# Check error rate
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/feature-flags/stats | \
  jq '.USE_ORM_BOOKS.errors'
```

## Environment Variables

| Variable | Default | Stage | Purpose |
|----------|---------|-------|---------|
| `USE_ORM_GLOBAL` | `true` | All | Master switch (emergency off) |
| `USE_ORM_METADATA` | `false` | 1 | Metadata operations |
| `USE_ORM_USERS` | `false` | 2 | User operations |
| `USE_ORM_SYNC` | `false` | 2 | Sync operations |
| `USE_ORM_BOOKS` | `false` | 3 | Book operations |
| `LOG_FEATURE_FLAGS` | `false` | Dev | Verbose logging (disable in prod) |

## Deployment Checklist

### Before Stage 1
- [ ] All Phase 4 tests passing: `pytest tests/api/ -v`
- [ ] Baseline performance measured
- [ ] Alerting configured for error rate
- [ ] On-call team briefed
- [ ] Rollback procedure tested

### Stage 1 (Metadata)
- [ ] `USE_ORM_METADATA=true`
- [ ] Monitor 24 hours
- [ ] Error rate < 0.5%
- [ ] Performance < 15% overhead
- [ ] Proceed to Stage 2

### Stage 2 (Users/Sync)
- [ ] `USE_ORM_USERS=true`, `USE_ORM_SYNC=true`
- [ ] Monitor 24 hours
- [ ] Auth flows working
- [ ] Sync success rate > 99%
- [ ] Proceed to Stage 3

### Stage 3 (Books)
- [ ] `USE_ORM_BOOKS=true`
- [ ] Monitor 48 hours
- [ ] Full sync succeeds 100%
- [ ] Book searches working
- [ ] Performance acceptable

### Post-Rollout (Keep for 2 weeks)
- [ ] Continuous monitoring
- [ ] Zero new production issues
- [ ] Performance stable
- [ ] Proceed to Phase 6

## Troubleshooting

### High Error Rate

```bash
# Check what's failing
curl http://localhost:8000/api/v1/feature-flags/stats | jq '.[] | select(.errors > 0)'

# Disable that operation
export USE_ORM_BOOKS=false
systemctl restart audiobooksync-api

# Check logs for details
grep "ERROR\|Exception" logs/app.log | tail -20
```

### Performance Regression

```bash
# Check current performance
curl http://localhost:8000/api/v1/feature-flags/stats | jq '.USE_ORM_BOOKS'

# If > 25% slower, disable
export USE_ORM_BOOKS=false
systemctl restart audiobooksync-api

# Investigate ORM queries
# Review logs for slow queries
```

### Fallback Loop (ORM fails, SQL fails)

```bash
# Emergency global disable
export USE_ORM_GLOBAL=false
systemctl restart audiobooksync-api

# Contact engineering team
# Issue is likely in both ORM and SQL implementations
```

## Useful Commands

```bash
# Reset stats for clean benchmark
curl -X POST -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/feature-flags/stats/reset

# Monitor live log stream
tail -f logs/app.log | grep -E "ORM|fallback|Feature flag"

# Check all feature flags at once
for flag in USE_ORM_GLOBAL USE_ORM_METADATA USE_ORM_USERS USE_ORM_SYNC USE_ORM_BOOKS; do
  echo -n "$flag: "
  printenv $flag || echo "false"
done

# Container log monitoring
docker logs -f audiobooksync-api | grep "Feature flag"
```

## Performance Baselines

Expected latency with < 20% overhead:

| Operation | Baseline | Target |
|-----------|----------|--------|
| Metadata (get_or_create) | 10ms | 11ms |
| Users (get by id) | 5ms | 6ms |
| Sync (create) | 10ms | 12ms |
| Books (get by user) | 50ms | 60ms |

Alert if exceeds target by > 5ms or 25%.

## Key Documentation Files

- **Main Strategy**: `PHASE_5_ROLLOUT_STRATEGY.md`
- **Implementation**: `PHASE_5_IMPLEMENTATION_SUMMARY.md`
- **Code Examples**: `src/database/services/book_service_with_fallback.py`
- **API Reference**: See endpoints in `src/api/routers/feature_flags.py`

## Support

| Issue | Contact | Action |
|-------|---------|--------|
| Can't enable flag | DevOps | Check env vars, restart service |
| Error rate high | Engineering | Check logs, consider rollback |
| Performance bad | Engineering | Review queries, consider rollback |
| Emergency | On-call | Set `USE_ORM_GLOBAL=false` |

---

**Questions?** See the full Phase 5 documentation or ask engineering team.

