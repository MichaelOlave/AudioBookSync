# Phase 6: Performance Validation & Benchmarking

## Overview

**Phase 6** focuses on comprehensive performance measurement, analysis, and optimization of the ORM implementation. This phase runs **after** Phase 5 rollout is complete and feature flags have been stable for 2 weeks.

**Timeline**: 1-2 weeks
**Key Deliverables**: Performance reports, optimization recommendations, validated baselines

## Performance Validation Architecture

### Tools Created

**Performance Framework** (`src/core/performance.py`):
- `PerformanceProfiler` - Profile async functions with memory tracking
- `BenchmarkComparison` - Compare ORM vs SQL implementations
- `LoadTester` - Test performance under concurrent load

**Benchmark Tests** (`tests/performance/test_orm_vs_sql_benchmarks.py`):
- Metadata operations benchmarks
- User operations benchmarks
- Sync operations benchmarks
- Book operations benchmarks
- Load testing scenarios

**Report Generator** (`src/core/performance_report.py`):
- HTML and JSON report generation
- Regression detection
- Optimization recommendations

## Running Benchmarks

### Installation

```bash
# Install performance testing dependencies
pip install pytest-benchmark pytest-asyncio
```

### Run All Benchmarks

```bash
# Run complete benchmark suite
pytest tests/performance/test_orm_vs_sql_benchmarks.py -v --benchmark-only

# With timing output
pytest tests/performance/test_orm_vs_sql_benchmarks.py -v --benchmark-only -s
```

### Run Specific Benchmark Category

```bash
# Metadata operations only
pytest tests/performance/test_orm_vs_sql_benchmarks.py::TestMetadataPerformance -v

# User operations only
pytest tests/performance/test_orm_vs_sql_benchmarks.py::TestUserPerformance -v

# Sync operations only
pytest tests/performance/test_orm_vs_sql_benchmarks.py::TestSyncPerformance -v

# Book operations only
pytest tests/performance/test_orm_vs_sql_benchmarks.py::TestBookPerformance -v

# Load tests only
pytest tests/performance/test_orm_vs_sql_benchmarks.py::TestLoadPerformance -v
```

### Run Single Benchmark

```bash
# One specific test
pytest tests/performance/test_orm_vs_sql_benchmarks.py::TestMetadataPerformance::test_get_or_create_contributor_orm_vs_sql -v
```

## Baseline Performance Targets

### Target Overhead by Operation

| Operation | Baseline | ORM Target | Max Acceptable |
|-----------|----------|-----------|-----------------|
| **Metadata** |
| get_or_create_contributor | 10ms | 11ms | 15ms |
| upsert_media_info | 10ms | 11ms | 15ms |
| add_custom_metadata | 5ms | 6ms | 10ms |
| add_badge | 5ms | 6ms | 10ms |
| **Users** |
| get_user_by_id | 5ms | 5ms | 10ms |
| update_audible_auth_json | 20ms | 23ms | 30ms |
| clear_audible_auth | 10ms | 12ms | 20ms |
| **Sync** |
| create_sync_history | 10ms | 12ms | 15ms |
| get_user_sync_history | 30ms | 35ms | 50ms |
| update_sync_status | 15ms | 18ms | 25ms |
| **Books** |
| get_books_by_user | 50ms | 55ms | 60ms |
| search_books | 100ms | 115ms | 150ms |
| add_book_with_metadata | 100ms | 120ms | 150ms |

### Success Criteria

✅ **PASS Phase 6 if**:
- Average overhead across all operations ≤ 20%
- No operation exceeds 30% overhead
- Error rate < 0.5% on ORM operations
- Load test success rate > 99%
- Memory usage within 15% of SQL

❌ **FAIL Phase 6 if**:
- Average overhead > 25%
- Any operation > 40% overhead
- Error rate > 1%
- Load test success rate < 95%
- Memory usage > 25% above SQL

## Performance Measurement Process

### Step 1: Establish Baselines

**Before optimization:**

```bash
# Create baseline directory
mkdir -p reports/baselines

# Run benchmarks with current implementation
pytest tests/performance/test_orm_vs_sql_benchmarks.py \
  --benchmark-only \
  -v > reports/baselines/initial_results.txt

# Export to JSON for analysis
pytest tests/performance/test_orm_vs_sql_benchmarks.py \
  --benchmark-json=reports/baselines/initial.json
```

### Step 2: Identify Bottlenecks

```python
from src.core.performance import BenchmarkComparison
from src.core.performance_report import PerformanceReport

# Analyze results
comparison = BenchmarkComparison()
report = PerformanceReport()

# Add benchmarks
for test_name, results in comparison.results.items():
    report.add_benchmark(test_name, results[-1])

# Generate HTML report
report.generate_html_report("performance_report.html")

# View recommendations
for rec in report.generate_report()["recommendations"]:
    print(rec)
```

### Step 3: Profile Hot Paths

```python
from src.core.performance import profiler

# Profile specific operation
result, metrics = await profiler.profile(
    orm_book_service.add_book_with_metadata,
    db=db_session,
    asin="B123",
    user_id="user-id",
    title="Test",
    book_data={...},
    operation_name="add_book_with_metadata"
)

# View metrics
print(f"Duration: {metrics.duration_ms:.2f}ms")
print(f"Memory delta: {metrics.memory_delta_bytes / 1024:.1f}KB")
```

### Step 4: Monitor Production Metrics

```bash
# Real-time performance monitoring in logs
tail -f logs/app.log | grep "PERF\|query_time"

# Extract performance data
grep "duration_ms" logs/app.log | jq -r '.duration_ms' > perf_data.txt

# Analyze with tools
python scripts/analyze_performance.py perf_data.txt
```

## Query Optimization Guide

### Issue 1: N+1 Queries

**Symptom**: Book operations take 100ms+ with 50+ queries

**Detection**:
```python
# Enable query logging
Config.LOG_QUERIES = True

# Run operation and count queries in logs
# If count(queries) >> count(objects), likely N+1
```

**Solution**:
```python
# Before: N+1 query
for book in books:
    author_count = await metadata_service.count_contributors(db, book.asin)

# After: Batch query
book_authors = await metadata_service.get_contributors_for_books(
    db, [b.asin for b in books]
)
```

### Issue 2: Missing Indexes

**Symptom**: Search queries taking 200ms+

**Detection**:
```sql
-- Check query plans
EXPLAIN ANALYZE
SELECT * FROM books WHERE title ILIKE '%test%' AND user_id = 'user-id'

-- Look for "Sequential Scan" - indicates missing index
```

**Solution**:
```sql
-- Add indexes
CREATE INDEX idx_books_user_title ON books(user_id, title);
CREATE INDEX idx_books_title_gin ON books USING GIN(to_tsvector('english', title));
```

### Issue 3: Inefficient Relationships

**Symptom**: Getting books with authors takes 50ms+ per book

**Detection**:
```python
# Before: Lazy loading
book = await book_service.get_book_by_asin(db, "B123")
contributors = await book.awaitable_attrs.contributors  # Extra query!

# Check logs - should see N queries for N books
```

**Solution**:
```python
# After: Eager loading with joinedload
from sqlalchemy.orm import selectinload

books = await book_service.get_books_by_user(
    db=db_session,
    user_id=user_id,
    options=[selectinload(Book.contributors)]  # Load in one query
)
```

### Issue 4: Bulk Operations

**Symptom**: Adding 100 books takes 10+ seconds

**Detection**:
```python
# Slow: Individual inserts
for book_data in books:
    await book_service.add_book(db, **book_data)

# Creates 100 separate transactions
```

**Solution**:
```python
# Fast: Bulk insert
from sqlalchemy import insert

stmt = insert(Book).values([
    {"asin": b["asin"], "user_id": user_id, ...}
    for b in books
])
await db.execute(stmt)
```

## Performance Monitoring Dashboard

### Setup Prometheus Metrics

```python
# src/core/metrics.py
from prometheus_client import Histogram, Counter

# Timing histograms
orm_duration = Histogram(
    'orm_operation_duration_ms',
    'ORM operation duration in milliseconds',
    ['operation']
)

sql_duration = Histogram(
    'sql_operation_duration_ms',
    'SQL operation duration in milliseconds',
    ['operation']
)

# Error counters
orm_errors = Counter(
    'orm_operation_errors_total',
    'ORM operation errors',
    ['operation', 'error_type']
)

# Usage
with orm_duration.labels(operation='get_books').time():
    books = await book_service.get_books_by_user(db, user_id)
```

### Grafana Dashboards

**Create dashboard with**:
- ORM vs SQL duration comparison
- Error rate by operation
- p50, p95, p99 latency percentiles
- Memory usage over time
- Query count by operation

## Regression Detection

### Automatic Regression Alerts

```python
from src.core.performance_report import PerformanceReport, PerformanceBaseline

report = PerformanceReport()

# Set baselines
report.set_baseline(
    "get_books_by_user",
    PerformanceBaseline(
        operation_name="get_books_by_user",
        duration_ms=50.0,
        acceptable_overhead_pct=20.0,
        regression_threshold_pct=15.0
    )
)

# Check for regression
regression = report.check_regression(
    "get_books_by_user",
    benchmark_result
)

if regression:
    logger.warning(f"REGRESSION: {regression}")
    # Alert team
    notify_team(regression)
```

### Manual Regression Analysis

```bash
# Compare current vs baseline
python scripts/compare_baselines.py \
  reports/baselines/initial.json \
  reports/current.json \
  --threshold 15

# Shows which operations regressed
```

## Performance Report Templates

### HTML Report Generation

```python
from src.core.performance_report import PerformanceReport

report = PerformanceReport()

# Add all benchmark results
for result in all_benchmarks:
    report.add_benchmark(result['test_name'], result)

# Set baselines
for baseline in baselines_list:
    report.set_baseline(baseline.name, baseline)

# Generate report
report.generate_html_report("phase6_report.html")
```

### Report Contents

**Summary Section**:
- Total tests run
- % within acceptable range
- % over threshold
- Regressions detected

**Detailed Results**:
- Per-operation metrics
- ORM vs SQL duration
- Overhead percentage
- Error rates
- Memory usage

**Optimization Recommendations**:
- Priority issues
- Specific recommendations
- Expected improvement

**Regression Details**:
- Tests that regressed
- Baseline vs current
- Percentage change

## Optimization Checklist

### Before Optimization

- [ ] Collect baseline metrics
- [ ] Generate performance report
- [ ] Identify top 3 bottlenecks
- [ ] Set optimization targets

### During Optimization

- [ ] Profile hot paths
- [ ] Implement change
- [ ] Re-benchmark
- [ ] Verify improvement
- [ ] Check for regressions

### After Optimization

- [ ] Compare to baseline
- [ ] Update documentation
- [ ] Commit changes with metrics
- [ ] Update performance report

## Common Optimizations by Operation

### Metadata Operations

**Issue**: `add_custom_metadata` slow (> 10ms)

**Optimization**:
```python
# Use atomic update
from sqlalchemy import text

await db.execute(
    text("""
        UPDATE book_metadata_json
        SET custom_metadata = jsonb_set(
            custom_metadata,
            '{key}',
            '\"value\"'::jsonb
        )
        WHERE asin = :asin
    """),
    {"asin": asin, "key": key, "value": value}
)
```

### User Operations

**Issue**: `update_audible_auth_json` slow (> 30ms)

**Optimization**:
```python
# Batch updates
stmt = update(User).values(
    audible_auth_json=new_auth,
    audible_email=new_email
).where(User.user_id == user_id)
await db.execute(stmt)
```

### Book Operations

**Issue**: `add_book_with_metadata` slow (> 150ms)

**Optimization**:
```python
# Use SQLAlchemy bulk insert
from sqlalchemy.dialects.postgresql import insert

# Bulk insert contributors
values = [{"name": a, "type": t} for a, t in authors]
stmt = insert(Contributor).values(values)\
    .on_conflict_do_nothing()
await db.execute(stmt)
```

## Performance Targets Summary

| Phase | Metric | Target | Status |
|-------|--------|--------|--------|
| Phase 6 Day 1 | Establish Baselines | ✓ Done | ✅ |
| Phase 6 Day 2-3 | Run Benchmarks | Complete suite | ⏳ |
| Phase 6 Day 4-5 | Analyze Results | Report generated | ⏳ |
| Phase 6 Day 6-7 | Optimize | Overhead ≤ 20% | ⏳ |
| Phase 6 Day 8-10 | Validate | All tests pass | ⏳ |
| Post Phase 6 | Document | Update guidelines | ⏳ |

## Phase 6 Deliverables Checklist

- ✅ Performance measurement framework
- ✅ Benchmark test suite
- ✅ Report generation tools
- ✅ Performance guide (this document)
- ⏳ Baseline measurements
- ⏳ Performance reports
- ⏳ Optimization recommendations
- ⏳ Updated performance documentation

## Next Steps

After Phase 6 completes:

1. **Validation**: Verify all performance targets met
2. **Documentation**: Update architecture docs with performance characteristics
3. **Transition**: Prepare for Phase 7 cleanup
4. **Monitoring**: Set up continuous performance monitoring

## Key Files

- **Performance Framework**: `src/core/performance.py`
- **Report Generator**: `src/core/performance_report.py`
- **Benchmark Tests**: `tests/performance/test_orm_vs_sql_benchmarks.py`
- **This Guide**: `PHASE_6_PERFORMANCE_GUIDE.md`

---

**Phase 6 Owner**: Engineering Lead
**Timeline**: 1-2 weeks after Phase 5 stabilization

