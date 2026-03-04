# AWS S3 Storage Setup Guide

This guide explains how to configure AudioBookSync to use AWS S3 for file storage instead of MinIO.

## Overview

The S3StorageAdapter implements the FileStoragePort interface using AWS S3 as the backend storage. It provides the same functionality as MinIOStorageAdapter but uses AWS S3 buckets instead.

## Prerequisites

1. AWS Account with permissions to create S3 buckets
2. AWS credentials (access key and secret key)
3. AWS region preference (default: us-east-1)

## Configuration

### Step 1: Set Up AWS Credentials

Choose one of the following methods:

#### Option A: Environment Variables (Development)

```bash
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"  # Optional
```

#### Option B: AWS Credentials File (Development)

Create or edit `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = your-access-key-id
aws_secret_access_key = your-secret-access-key

[production]
aws_access_key_id = your-prod-access-key
aws_secret_access_key = your-prod-secret-key
```

#### Option C: IAM Role (Production - EC2/ECS/Lambda)

When running on AWS infrastructure, attach an IAM role to your instance/container/function with the required S3 permissions. No credentials configuration needed.

### Step 2: Create IAM User (Development)

In AWS Management Console:

1. Go to IAM → Users → Create user (e.g., `audiobook-sync-dev`)
2. Attach policy: `AmazonS3FullAccess` (for development)
3. Create access keys
4. Use the keys in credentials file or environment variables

### Step 3: Update Application Code

In your application startup code, replace MinIOStorageAdapter with S3StorageAdapter:

**Before (MinIO):**
```python
from src.adapters.storage.minio_storage_adapter import MinIOStorageAdapter

storage = MinIOStorageAdapter()
```

**After (S3):**
```python
from src.adapters.storage.s3_storage_adapter import S3StorageAdapter

# Use default region (us-east-1)
storage = S3StorageAdapter()

# Or specify a region
storage = S3StorageAdapter(region_name="us-west-2")
```

### Step 4: Configure as Dependency Injection (Recommended)

For better testability, use dependency injection in your routers/services:

```python
from fastapi import Depends
from src.ports.file_storage_port import FileStoragePort
from src.adapters.storage.s3_storage_adapter import S3StorageAdapter

def get_storage() -> FileStoragePort:
    """Dependency injection for storage."""
    return S3StorageAdapter(region_name="us-east-1")

@router.get("/audiobook/{asin}")
async def stream_audiobook(
    asin: str,
    storage: FileStoragePort = Depends(get_storage),
):
    # Use storage port interface
    data = storage.stream_file(user_id, object_key)
    ...
```

## Bucket Structure

S3StorageAdapter creates per-user buckets with the following structure:

```
user-{user_id}/
├── downloaded/
│   ├── {asin}.aax      # Encrypted audiobook from Audible
│   └── {asin}.aax      # (multiple ASINs)
└── decrypted/
    ├── {title}.m4b     # Decrypted audiobook
    └── {title}.m4b     # (multiple titles)
```

Example for user "550e8400-e29b-41d4-a716-446655440000":

```
user-550e8400-e29b-41d4-a716-446655440000/
├── downloaded/
│   ├── B084L6Z6M3.aax
│   └── B08KFJY7D9.aax
└── decrypted/
    ├── Project Hail Mary.m4b
    └── The Way of Kings.m4b
```

## Cost Estimation

### Storage Pricing (us-east-1)

- **Standard Storage**: $0.023 per GB/month
- **Transfer Out**: $0.09 per GB (after 1GB free)
- **API Calls**: $0.0004 per 1,000 GET requests, $0.005 per 1,000 PUT requests

### Example Calculation

For 100 users with 50 books each (average 500MB per book):

```
Storage: 100 users × 50 books × 500MB = 2.5TB
Monthly cost: 2.5TB × $0.023 = ~$57.50

Transfers: Assuming 10 downloads/month per user per book
Monthly requests: 100 × 50 × 10 = 50,000 downloads
Download cost: 50,000 × 500MB × $0.09/GB = ~$2,250 (significant!)

Total estimate: ~$2,300/month for transfer costs
```

**Optimization Tips:**
- Use CloudFront CDN to cache popular audiobooks (cheaper egress)
- Use S3 Intelligent-Tiering for archival
- Consider S3 One Zone-IA for non-critical backups

## IAM Policy (Least Privilege - Recommended)

For production, use this more restrictive policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CreateUserBuckets",
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:ListBucket",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::user-*"
    },
    {
      "Sid": "ManageUserBucketObjects",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::user-*",
        "arn:aws:s3:::user-*/*"
      ]
    }
  ]
}
```

## Monitoring and Logging

### Enable S3 Access Logging

```python
import boto3

s3 = boto3.client('s3')

# Create logging bucket
s3.create_bucket(Bucket='audiobook-sync-logs')

# Enable logging for user bucket
s3.put_bucket_logging(
    Bucket='user-550e8400-e29b-41d4-a716-446655440000',
    BucketLoggingStatus={
        'LoggingEnabled': {
            'TargetBucket': 'audiobook-sync-logs',
            'TargetPrefix': 'logs/'
        }
    }
)
```

### CloudWatch Metrics

S3 automatically publishes metrics to CloudWatch:

- NumberOfObjects
- BucketSizeBytes
- AllStorageBytes (including non-current versions)

View in AWS CloudWatch Console → S3

## Lifecycle Policies

### Archive Old Files

```python
s3.put_bucket_lifecycle_configuration(
    Bucket='user-550e8400-e29b-41d4-a716-446655440000',
    LifecycleConfiguration={
        'Rules': [
            {
                'ID': 'archive-old-downloads',
                'Status': 'Enabled',
                'Prefix': 'downloaded/',
                'Transitions': [
                    {
                        'Days': 30,
                        'StorageClass': 'STANDARD_IA'  # Infrequent Access
                    },
                    {
                        'Days': 90,
                        'StorageClass': 'GLACIER'  # Cold storage
                    }
                ]
            }
        ]
    }
)
```

## Troubleshooting

### "NoSuchBucket" Error

The bucket doesn't exist or you don't have permission to access it.

**Solution:**
- Ensure AWS credentials are correct
- Check IAM permissions include `s3:CreateBucket`
- Verify bucket name format: `user-{user_id}`

### "AccessDenied" Error

IAM user doesn't have required permissions.

**Solution:**
- Attach S3 policy to IAM user
- Use least privilege policy above
- Check credentials are for correct IAM user

### "SignatureDoesNotMatch" Error

AWS credentials are incorrect or expired.

**Solution:**
- Verify AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
- Check credentials file formatting
- Generate new access keys if needed

### High Data Transfer Costs

Large amounts of data being downloaded.

**Solution:**
- Enable CloudFront CDN for frequently accessed files
- Implement caching headers in application
- Use S3 request metrics to identify hot files
- Consider Intelligent-Tiering for less-accessed data

## Migration from MinIO to S3

### Step 1: Inventory Files in MinIO

```python
from src.adapters.storage.minio_storage_adapter import MinIOStorageAdapter

minio = MinIOStorageAdapter()
# List all objects across all user buckets
```

### Step 2: Copy to S3

```bash
# Use AWS DataSync or S3 Transfer Acceleration
aws s3 sync s3://minio-export/ s3://user-bucket/ \
  --source-region us-east-1 \
  --region us-east-1
```

### Step 3: Verify and Switch

1. Verify all files copied to S3
2. Test with S3StorageAdapter
3. Switch application to use S3StorageAdapter
4. Deprecate MinIO

### Step 4: Cleanup

1. Archive MinIO backups
2. Decommission MinIO infrastructure

## Related Documentation

- [Hexagonal Architecture](../architecture/HEXAGONAL_ARCHITECTURE.md) - Overview of storage adapters
- [MinIO Setup Guide](./MINIO_SETUP_GUIDE.md) - Alternative to S3
- AWS S3 Documentation: https://docs.aws.amazon.com/s3/
- boto3 Documentation: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html
