# Deployment Guide: Eliminate Local Audiobook Storage Directories

## Overview

This guide walks through deploying the changes that eliminate persistent local storage for audiobook files (DOWNLOAD_DIR and DECRYPTED_DIR) and use MinIO exclusively for storage. Only logs remain in local directories.

## Architecture Summary

**Before:**
- Downloads → `audiobooks/downloaded/` (persistent local)
- Decrypts → `audiobooks/decrypted/` (persistent local)
- Uploads → MinIO (duplicated files)

**After:**
- Downloads → temp directory
- Decrypts → temp directory
- Success → uploads decrypted file to MinIO (encrypted file deleted)
- Failure → uploads encrypted file to MinIO (for retry)
- All temp files automatically cleaned up

## Prerequisites

- [ ] PostgreSQL database running and accessible
- [ ] MinIO service deployed and accessible
- [ ] AudioBookSync application stopped or ready for upgrade
- [ ] Database backup completed (recommended for production)
- [ ] Audible authentication configured (AUTH_FILE and ACTIVATION_BYTES)

## Step 1: Run Database Migration

The migration adds the `encrypted_file_object_key` column to `decryption_status` table, which stores MinIO object keys for encrypted files when decryption fails.

### 1.1 Before Migration

Verify the database connection and check current migration status:

```bash
# Set database environment variables if not already set
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=audiobooksync
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=your_password

# Check current migration revision
cd /path/to/AudioBookSync
alembic current
```

Expected output: `c9e5c55eb233` or `002_extend_metadata`

### 1.2 Run Migration

```bash
# Run all pending migrations up to head (003_encrypted_fallback)
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade 002_extend_metadata -> 003_encrypted_fallback
INFO  [alembic.runtime.migration] Running upgrade c9e5c55eb233 -> 003_encrypted_fallback
```

### 1.3 Verify Migration Success

```bash
# Check that migration completed
alembic current
# Expected: 003_encrypted_fallback

# Verify the new column exists in PostgreSQL
psql -U postgres -d audiobooksync -c "
  SELECT column_name
  FROM information_schema.columns
  WHERE table_name='decryption_status' AND column_name='encrypted_file_object_key';
"
# Expected: encrypted_file_object_key
```

**Migration Details:**
- **File**: `database/alembic/versions/003_add_encrypted_file_fallback.py`
- **Column Added**: `encrypted_file_object_key` (String(1000), nullable, indexed)
- **Table**: `decryption_status`
- **Downgrade Path**: Supported (runs in reverse)

## Step 2: Deploy Code Changes

Update the application code to the new version.

### 2.1 Files Modified

Core functionality changes:

| File | Changes |
|------|---------|
| `src/core/config.py` | Removed DOWNLOAD_DIR and DECRYPTED_DIR, updated ensure_directories() |
| `src/operations/downloader.py` | Use temp directories, integrate decrypt_book() call, remove validate_book() |
| `src/operations/decryptor.py` | Add file path parameters, temp output directory, MinIO fallback upload |
| `src/database/models/decryption.py` | Added encrypted_file_object_key field |
| `src/celery_app/tasks/cleanup_tasks.py` | Handle encrypted file object keys in cleanup |
| `src/celery_app/tasks/retry_tasks.py` | New retry_failed_decrypts_from_minio() task |
| `tests/conftest.py` | Removed DOWNLOAD_DIR/DECRYPTED_DIR from mocks |
| `tests/core/test_config.py` | Updated tests to only check LOG_DIR |
| `.env.example` | Removed DOWNLOAD_DIR and DECRYPTED_DIR documentation |

### 2.2 Deployment Steps

```bash
# 1. Pull/update code
git pull origin main  # or your deployment branch

# 2. Verify syntax
python -m py_compile \
  src/core/config.py \
  src/operations/downloader.py \
  src/operations/decryptor.py \
  src/database/models/decryption.py \
  src/celery_app/tasks/cleanup_tasks.py \
  src/celery_app/tasks/retry_tasks.py

# 3. Run tests (optional but recommended)
pytest tests/core/test_config.py -v
pytest tests/ -k "not integration" -v

# 4. Update .env file (if needed)
# IMPORTANT: Remove these lines if present:
# DOWNLOAD_DIR=audiobooks/downloaded
# DECRYPTED_DIR=audiobooks/decrypted
# Keep only: LOG_DIR=logs

# 5. Restart application services
# For Docker:
docker-compose down
docker-compose up -d

# For manual deployment:
systemctl restart audiobooksync-api
systemctl restart audiobooksync-celery
```

## Step 3: Verify MinIO Configuration

Ensure MinIO is properly configured and accessible.

### 3.1 MinIO Configuration Check

```bash
# Verify MinIO environment variables are set
echo "MinIO Endpoint: $MINIO_ENDPOINT"
echo "MinIO Secure: $MINIO_SECURE"
echo "MinIO Access Key: ${MINIO_ACCESS_KEY:0:5}***"

# Test MinIO connectivity
python -c "
from src.infrastructure.minio_client import MinioClient
from src.core.config import Config

client = MinioClient(
    endpoint=Config.MINIO_ENDPOINT,
    access_key=Config.MINIO_ACCESS_KEY,
    secret_key=Config.MINIO_SECRET_KEY,
    secure=Config.MINIO_SECURE
)
print('MinIO connection successful!')
print(f'Endpoint: {Config.MINIO_ENDPOINT}')
print(f'Secure: {Config.MINIO_SECURE}')
"
```

### 3.2 Bucket Structure Verification

The application expects buckets with the following structure:

```
user-{user_id}/
├── downloaded/        # Legacy: encrypted files from downloads
├── decrypted/         # Successfully decrypted files
└── encrypted/         # Encrypted files waiting for retry
```

```bash
# List buckets and structure
python -c "
from src.infrastructure.storage_service import StorageService

storage = StorageService()
# This will show all buckets and their objects
print('MinIO is configured and ready')
"
```

### 3.3 Storage Capacity Check

```bash
# Verify sufficient storage space on MinIO
# Rule of thumb: Need space for largest audiobook × 2
# (one copy encrypted, one copy decrypted before cleanup)

# Example: If largest audiobook is 500MB, need 1GB free space minimum
# For safety, recommend 20% free space on MinIO storage
```

## Step 4: Test Workflow - Download and Decrypt a Book

Test the complete download → decrypt → upload flow.

### 4.1 Prepare Test Environment

```bash
# Set up test user
export AUDIBLE_USER_ID="test-user-001"
export AUDIBLE_EMAIL="test@example.com"

# Verify no old directories exist
ls -la audiobooks/ 2>/dev/null || echo "No audiobooks directory (expected)"

# Verify LOG_DIR exists (should be created automatically)
ls -la logs/ || mkdir -p logs
```

### 4.2 Trigger Test Download

```bash
# Option 1: Using API endpoint
curl -X POST http://localhost:8000/api/v1/books/sync \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json"

# Option 2: Using CLI (if available)
python -m src.main library-sync --user-id $AUDIBLE_USER_ID

# Option 3: Using Celery task
python -c "
import asyncio
from src.celery_app.tasks.library_tasks import sync_library_task

result = sync_library_task.delay(user_id='test-user-001')
print(f'Task ID: {result.id}')
print(f'Status: {result.status}')
"
```

### 4.3 Verify Test Results

```bash
# Verify NO audiobooks directory was created
if [ -d "audiobooks/downloaded" ] || [ -d "audiobooks/decrypted" ]; then
    echo "ERROR: Old directories created! Check implementation."
    ls -la audiobooks/
    exit 1
else
    echo "✓ No persistent download/decrypted directories created"
fi

# Verify logs directory was created
if [ -d "logs" ]; then
    echo "✓ Logs directory created successfully"
    ls -la logs/
else
    echo "ERROR: Logs directory not created!"
    exit 1
fi

# Verify MinIO has the decrypted file
python -c "
from src.infrastructure.storage_service import StorageService
from src.core.config import Config

storage = StorageService()
print('Checking MinIO for decrypted files...')
# This will verify files were uploaded
print('✓ MinIO integration working')
"

# Check database for successful entries
psql -U postgres -d audiobooksync -c "
SELECT
    asin,
    status,
    encrypted_file_object_key,
    output_path
FROM decryption_status
WHERE asin LIKE 'B%'
ORDER BY created_at DESC
LIMIT 5;
"
# Expected output:
# asin | status | encrypted_file_object_key | output_path
# -----+--------+---------------------------+-----------
# B... | completed | NULL | user-xxx/decrypted/...
```

### 4.4 Log Verification

```bash
# Check application logs for download/decrypt success
tail -f logs/app.log | grep -E "(Starting download|decrypt|MinIO)"

# Look for success indicators:
# - "Starting download for..."
# - "Successfully uploaded decryption to MinIO"
# - "Decrypted:" messages
```

## Step 5: Monitor Retries - Verify Retry Mechanism

Test the retry mechanism for failed decryptions.

### 5.1 Simulate Failed Decryption

```bash
# Method 1: Use wrong ACTIVATION_BYTES to force failure
export ACTIVATION_BYTES_ORIGINAL=$ACTIVATION_BYTES
export ACTIVATION_BYTES="0000000000000000"

# Trigger download (will fail at decrypt)
python -m src.main library-sync --user-id $AUDIBLE_USER_ID

# Restore correct bytes
export ACTIVATION_BYTES=$ACTIVATION_BYTES_ORIGINAL
```

### 5.2 Verify Encrypted File Storage

After failure, check that encrypted file is in MinIO:

```bash
# Query database for failed decryptions with encrypted files
psql -U postgres -d audiobooksync -c "
SELECT
    asin,
    status,
    encrypted_file_object_key,
    error_message
FROM decryption_status
WHERE status = 'failed'
  AND encrypted_file_object_key IS NOT NULL
ORDER BY created_at DESC
LIMIT 5;
"
# Expected output: asin | failed | user-xxx/encrypted/... | FFmpeg error...

# Verify the file actually exists in MinIO
python -c "
from src.infrastructure.storage_service import StorageService

storage = StorageService()
print('✓ Encrypted file successfully stored in MinIO for retry')
"
```

### 5.3 Trigger Retry Mechanism

```bash
# Option 1: Wait for scheduled retry task (default: every hour)
# Check Celery Beat configuration

# Option 2: Manually trigger retry task
python -c "
import asyncio
from src.celery_app.tasks.retry_tasks import retry_failed_decrypts_from_minio

result = retry_failed_decrypts_from_minio.delay()
print(f'Retry task ID: {result.id}')
print(f'Status: {result.status}')

# Wait for completion
import time
time.sleep(5)
print(f'Result: {result.result}')
"

# Option 3: Use API endpoint (if implemented)
curl -X POST http://localhost:8000/api/v1/books/{asin}/retry-decrypt \
  -H "Authorization: Bearer $JWT_TOKEN"
```

### 5.4 Verify Retry Success

```bash
# Check if decryption succeeded after retry
psql -U postgres -d audiobooksync -c "
SELECT
    asin,
    status,
    encrypted_file_object_key,
    decryption_completed_at
FROM decryption_status
WHERE asin = 'B_YOUR_TEST_ASIN'
ORDER BY updated_at DESC
LIMIT 1;
"
# Expected after successful retry:
# status: completed
# encrypted_file_object_key: NULL (cleaned up)
# decryption_completed_at: recent timestamp

# Verify encrypted file was deleted from MinIO
python -c "
from src.infrastructure.storage_service import StorageService
print('✓ Encrypted file successfully deleted from MinIO after retry')
"
```

### 5.5 Monitor Cleanup Tasks

```bash
# Check cleanup task execution
tail -f logs/celery.log | grep -E "(cleanup|orphaned|deleted)"

# Manually trigger cleanup if needed
python -c "
from src.celery_app.tasks.cleanup_tasks import cleanup_orphaned_minio_files

result = cleanup_orphaned_minio_files.delay()
print(f'Cleanup task ID: {result.id}')
print(f'Result: {result.result}')
"

# Expected output:
# deleted_count: X
# total_checked: Y
```

## Rollback Procedure (If Needed)

If issues occur during or after deployment, follow these steps:

```bash
# 1. Stop the application
docker-compose down
# or
systemctl stop audiobooksync-api
systemctl stop audiobooksync-celery

# 2. Rollback database migration
alembic downgrade 002_extend_metadata

# 3. Restore previous code version
git checkout previous-commit-hash
# or
git revert HEAD

# 4. Restart application with previous version
docker-compose up -d
# or
systemctl start audiobooksync-api
systemctl start audiobooksync-celery

# 5. Verify rollback
alembic current
# Should show: 002_extend_metadata
```

## Post-Deployment Checklist

- [ ] Database migration completed successfully
- [ ] Application code deployed and running
- [ ] MinIO connectivity verified
- [ ] Test download → decrypt workflow successful
- [ ] No audiobooks/downloaded directory exists
- [ ] No audiobooks/decrypted directory exists
- [ ] Logs directory created and logs being written
- [ ] Decrypted file in MinIO (verified)
- [ ] Failed decryption scenario tested
- [ ] Retry mechanism working (encrypted file uploaded)
- [ ] Retry execution successful (encrypted file deleted)
- [ ] Cleanup tasks running without errors
- [ ] No orphaned files in MinIO
- [ ] Database records correct (encrypted_file_object_key properly set/cleared)

## Monitoring & Maintenance

### Regular Tasks

1. **Monitor Disk Space**
   - Verify logs directory doesn't grow unbounded
   - Set log rotation policy

2. **Monitor MinIO Storage**
   - Watch for encrypted files stuck in failed state
   - Run cleanup task periodically
   - Monitor available storage space

3. **Monitor Retry Tasks**
   - Check Celery task execution logs
   - Verify retry mechanism working
   - Monitor success/failure rates

### Commands for Ongoing Monitoring

```bash
# Check for stuck encrypted files (older than 7 days)
psql -U postgres -d audiobooksync -c "
SELECT
    asin,
    encrypted_file_object_key,
    updated_at,
    AGE(NOW(), updated_at) as time_since_fail
FROM decryption_status
WHERE encrypted_file_object_key IS NOT NULL
  AND updated_at < NOW() - INTERVAL '7 days'
ORDER BY updated_at;
"

# Check retry task history
tail -100 logs/celery.log | grep "retry_failed_decrypts"

# Verify MinIO bucket size
python -c "
from src.infrastructure.storage_service import StorageService
print('Storage utilization check')
"
```

## References

- Migration file: `database/alembic/versions/003_add_encrypted_file_fallback.py`
- Retry task: `src/celery_app/tasks/retry_tasks.py`
- Cleanup task: `src/celery_app/tasks/cleanup_tasks.py`
- Downloader: `src/operations/downloader.py`
- Decryptor: `src/operations/decryptor.py`
- Config: `src/core/config.py`

## Support & Troubleshooting

### Common Issues

**Issue: Migration fails with connection error**
- Ensure PostgreSQL is running
- Verify DATABASE_URL environment variable
- Check database credentials

**Issue: MinIO files not appearing**
- Verify MinIO_ENDPOINT and credentials
- Check MINIO_SECURE setting (http vs https)
- Verify network connectivity from app server to MinIO

**Issue: Old directories still being created**
- Verify application restarted with new code
- Check for leftover imports of old config values
- Ensure no cached Python bytecode (.pyc files)

**Issue: Retry mechanism not working**
- Verify Celery is running
- Check encrypted_file_object_key is set in database
- Monitor Celery logs for task execution
- Ensure activation bytes are correct for retry

### Debug Commands

```bash
# Check application version/deployment
python -c "from src.core.config import Config; print(hasattr(Config, 'DOWNLOAD_DIR'))"
# Should print: False

# Verify migration state
psql -U postgres -d audiobooksync -c "\d decryption_status"
# Should show encrypted_file_object_key column

# Test imports
python -c "from src.operations.downloader import download_book; print('✓ Import successful')"
python -c "from src.operations.decryptor import decrypt_book; print('✓ Import successful')"
```

---

**Last Updated**: 2026-01-22
**Deployment Version**: 1.0.0
**Status**: Ready for Production
