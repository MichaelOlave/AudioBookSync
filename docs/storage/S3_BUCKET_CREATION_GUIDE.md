# AWS S3 Bucket Creation Guide

This guide walks you through creating and configuring an S3 bucket for AudioBookSync.

## Prerequisites

- AWS Account with billing enabled
- IAM user with S3 permissions (or admin access)
- AWS Management Console access

## Step-by-Step: Create Bucket

### Step 1: Open S3 Console

1. Go to AWS Management Console: https://console.aws.amazon.com
2. Search for "S3" and click **S3** from the results
3. Click **Create bucket** (orange button)

### Step 2: Configure Bucket Name and Region

**Bucket Name:**
- Choose a globally unique name (S3 bucket names are global)
- Recommended format: `audiobooksync-{your-username}` or `audiobooks-{date}`
- Example: `audiobooksync-michael` or `audiobooks-2026-01-24`
- Click in the text field and type your bucket name

**Region:**
- Select the region closest to your users
- Common choices:
  - `us-east-1` - US East (N. Virginia) - default, cheapest
  - `us-west-2` - US West (Oregon)
  - `eu-west-1` - EU (Ireland)
  - `ap-southeast-1` - Asia Pacific (Singapore)
- If unsure, choose `us-east-1` (lowest cost)

Click **Next**

---

### Step 3: Disable Block Public Access (Keep It All Enabled)

**Block Public Access settings** - Keep all checkboxes **CHECKED** ✓

This is the most important security step! Leave defaults:
- ☑ Block all public access
- ☑ Ignore all ACLs
- ☑ Ignore bucket and object tags
- ☑ Block access to buckets with bucket policies that grant public access
- ☑ Block access to objects with public ACLs

These settings ensure your audiobooks are **private and secure**.

Click **Next**

---

### Step 4: Enable Versioning (Recommended)

**Versioning:** Choose **Enable**

This creates backup versions of files if you accidentally overwrite them.

Benefits:
- Recover accidentally deleted files
- Maintain audit trail of changes
- Small additional cost (~$0.023/GB/month for old versions)

*Optional: You can disable if you want to minimize costs, but versioning is recommended for production.*

Click **Next**

---

### Step 5: Enable Encryption

**Default encryption:**
- ☑ Enable (recommended)
- Encryption type: **SSE-S3** (default)

This encrypts audiobooks at rest automatically. No additional cost.

*Advanced: If you need customer-managed keys, choose **SSE-KMS** and select a KMS key, but this adds ~$0.03/10,000 requests cost.*

**Server-side encryption of objects in this bucket:**
- Keep **SSE-S3** selected

Click **Create bucket**

---

## Final Bucket Settings

Your bucket is now created! Verify these settings:

### ✅ Essential Settings

| Setting | Value | Why |
|---------|-------|-----|
| **Block Public Access** | All enabled | Private audiobooks |
| **Bucket ACL** | Private | Only your IAM user can access |
| **Encryption** | SSE-S3 enabled | Encrypt at rest |
| **Versioning** | Enabled | Backup old versions |
| **Object Ownership** | BucketOwnerEnforced | Better access control |

### ✅ Good-to-Have Settings

| Setting | Value | Why |
|---------|-------|-----|
| **Logging** | Enabled (optional) | Monitor access |
| **Lifecycle Policy** | Set rules | Move old files to cheaper storage |
| **CORS** | Optional | If using web upload |
| **Tags** | `env=production`, `app=audiobooksync` | Cost tracking & organization |

### ❌ Don't Enable These

| Setting | Why NOT |
|---------|---------|
| **Public Access** | Your audiobooks are private |
| **Object Lock** | Not needed for audiobooks |
| **MFA Delete** | Adds complexity, not necessary |
| **Transfer Acceleration** | Extra cost, not needed |

---

## Post-Creation Configuration

### 1. Enable Access Logging (Optional)

Access logging helps you monitor who downloads audiobooks.

1. Go to your bucket > **Properties** tab
2. Under "Server access logging" click **Edit**
3. Enable logging
4. Create a separate `logs` bucket for log files:
   - Create bucket named `{your-bucket-name}-logs`
   - Point logging to that bucket
5. Save

### 2. Set Lifecycle Policy (Optional - Reduces Costs)

Move old downloads to cheaper storage tiers.

1. Go to **Management** tab
2. Click **Create lifecycle rule**

**Example Rule: Archive old downloaded files**

```
Name: Archive old downloads
Apply to: Objects with prefix "downloaded/"
After 30 days: Move to Standard-IA (cheaper tier)
After 90 days: Move to Glacier (very cheap, slower retrieval)
```

This saves money on old encrypted files you might not need immediate access to.

### 3. Add Tags (Optional - Cost Tracking)

1. Go to **Properties** tab
2. Under "Tags" click **Edit**
3. Add tags:
   - Key: `Environment` | Value: `production` or `development`
   - Key: `Application` | Value: `AudioBookSync`
   - Key: `Owner` | Value: `your-name`

---

## Configure IAM User Permissions

Your IAM user needs specific S3 permissions. Create this policy:

### Step 1: Get Bucket Name

Copy your bucket name: `audiobooksync-michael` (example)

### Step 2: Create IAM Policy

1. Go to **IAM Console** → **Policies**
2. Click **Create policy**
3. Choose **JSON** tab
4. Paste this policy (replace `your-bucket-name`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBuckets",
      "Effect": "Allow",
      "Action": [
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation"
      ],
      "Resource": "arn:aws:s3:::*"
    },
    {
      "Sid": "AccessAudioBookSyncBucket",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketVersioning"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name"
    },
    {
      "Sid": "ManageObjects",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:GetObjectVersion"
      ],
      "Resource": "arn:aws:s3:::your-bucket-name/*"
    }
  ]
}
```

4. Click **Next**
5. Name it: `AudioBookSyncS3Access`
6. Click **Create policy**

### Step 3: Attach Policy to IAM User

1. Go to **IAM** → **Users**
2. Click your username
3. Click **Add permissions** → **Attach policies directly**
4. Search for `AudioBookSyncS3Access`
5. Click checkbox and attach

---

## Generate Access Keys

1. Go to **IAM** → **Users** → Your username
2. Click **Create access key**
3. Choose **Application running outside AWS**
4. Click **Next**
5. You'll see:
   - Access key ID: `AKIA...`
   - Secret access key: `wJalr...`

**⚠️ IMPORTANT:** Copy these immediately and store securely. You can't retrieve the secret key later.

---

## Configure AudioBookSync

### Option A: Environment Variables

```bash
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_DEFAULT_REGION="us-east-1"
```

### Option B: Update User Settings in AudioBookSync UI

1. Go to Settings → Storage
2. Click **AWS S3**
3. Enter:
   - Region: `us-east-1` (or your region)
   - Access Key: `AKIA...`
   - Secret Key: `wJalr...`
4. Click **Test Connection**
5. Click **Save**

---

## Verify Bucket Settings

### Via AWS Console

1. Go to your bucket
2. Check these tabs:

**Permissions:**
- Block public access: ✓ All enabled
- ACL: Private
- Bucket policy: Empty (default)

**Properties:**
- Default encryption: Enabled (SSE-S3)
- Versioning: Enabled (or Suspended)
- Server access logging: Enabled (optional)

**Management:**
- Lifecycle rules: Set if archiving (optional)

### Via AWS CLI

```bash
# List your buckets
aws s3 ls

# Check bucket encryption
aws s3api get-bucket-encryption --bucket your-bucket-name

# Check versioning
aws s3api get-bucket-versioning --bucket your-bucket-name

# Check public access block
aws s3api get-public-access-block --bucket your-bucket-name
```

---

## Cost Optimization

### Typical Costs for AudioBookSync

For 100 users with 50 books each (2.5TB storage):

| Metric | Cost |
|--------|------|
| Storage (2.5TB @ $0.023/GB) | ~$57/month |
| API Calls (uploads/downloads) | ~$10-25/month |
| Data Transfer (egress) | ~$200-500/month* |
| **Total** | **~$270-580/month** |

*Data transfer is the largest cost - see below for optimization

### Reduce Data Transfer Costs

**Option 1: CloudFront CDN (Recommended)**
- Caches audiobooks at edge locations
- Reduces egress costs by ~75%
- Adds ~$20-100/month but saves $150-400/month in transfer
- **Net savings: $50-380/month**

**Option 2: S3 Intelligent-Tiering**
- Automatically moves unused files to cheaper tiers
- Saves 20-40% on storage
- No retrieval delays

**Option 3: Regional Endpoints**
- If all users in one region, use that region
- Saves on cross-region transfer costs

---

## Troubleshooting

### "AccessDenied" When Testing Connection

**Solution:**
1. Verify IAM user has S3 permissions
2. Check access key ID and secret key are correct
3. Verify policy includes correct bucket name
4. Wait 1-2 minutes for IAM permissions to propagate

### "NoSuchBucket" Error

**Solution:**
1. Verify bucket name is spelled correctly
2. Verify bucket exists in the region you specified
3. Verify bucket is not in different region than configured

### High Data Transfer Costs

**Solutions:**
1. Enable CloudFront CDN
2. Check who's downloading frequently
3. Implement caching in application
4. Use S3 Intelligent-Tiering

### Upload/Download Slow

**Solutions:**
1. Choose region closer to users
2. Enable S3 Transfer Acceleration
3. Use multi-part upload for large files
4. Check internet connection speed

---

## Security Checklist

✅ **Before going to production:**

- [ ] Block all public access is enabled
- [ ] Encryption (SSE-S3 or SSE-KMS) is enabled
- [ ] Versioning is enabled
- [ ] IAM user has only necessary permissions
- [ ] Access keys are stored securely (use AWS Secrets Manager)
- [ ] MFA is enabled on root account
- [ ] Logging is enabled to track access
- [ ] Lifecycle policy is set for cost optimization
- [ ] CloudFront CDN is configured (optional but recommended)
- [ ] Regular backups are being taken
- [ ] Tags are set for cost tracking

---

## Related Documentation

- [S3 Setup Guide](./S3_SETUP_GUIDE.md) - How to configure AudioBookSync to use S3
- [MinIO vs S3 Comparison](./MINIO_VS_S3_COMPARISON.md) - Choose the right storage
- [Storage Adapter Usage](../architecture/STORAGE_ADAPTER_USAGE.md) - How to use storage in code

---

## Quick Reference

### Default Settings (Recommended)

```
Bucket Name:           audiobooksync-{username}
Region:                us-east-1
Block Public Access:   ✓ All enabled
Encryption:            SSE-S3 (enabled)
Versioning:            Enabled
Logging:               Optional
Lifecycle:             Optional
```

### Common Regions

| Region | Name | Use Case |
|--------|------|----------|
| `us-east-1` | US East (N. Virginia) | US users, lowest cost |
| `us-west-2` | US West (Oregon) | US West Coast users |
| `eu-west-1` | EU (Ireland) | European users |
| `ap-southeast-1` | Asia Pacific (Singapore) | Asian users |

Start with `us-east-1` if unsure!
