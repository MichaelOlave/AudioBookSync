# AudioBookSync Terraform Configuration

This directory contains Terraform configuration for deploying AudioBookSync infrastructure on AWS.

## Architecture Overview

The Terraform configuration sets up a production-ready infrastructure with:

- **VPC**: Custom VPC with public, private, and database subnets across 2 availability zones
- **ECS Fargate**: Containerized FastAPI backend with auto-scaling
- **RDS**: PostgreSQL 16 database with automated backups and monitoring
- **ElastiCache**: Redis cluster with multi-AZ and automatic failover
- **S3**: Object storage for audiobook files with versioning and lifecycle policies
- **ALB**: Application Load Balancer for traffic distribution
- **CloudWatch**: Comprehensive monitoring and alarms

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **Terraform** >= 1.0 (install from https://www.terraform.io/downloads)
3. **AWS CLI** configured with credentials (optional but recommended)
4. **Docker** image pushed to ECR (for ECS deployment)
5. Estimated costs:
   - Dev: ~$40-50/month
   - Staging: ~$80-100/month
   - Production: ~$150-200/month

## Project Structure

```
terraform/
├── terraform.tf              # Provider and backend configuration
├── main.tf                   # Main module orchestration
├── variables.tf              # Root-level variables
├── outputs.tf                # Root-level outputs
├── locals.tf                 # Local values
├── README.md                 # This file
│
├── modules/                  # Reusable infrastructure modules
│   ├── vpc/                  # VPC, subnets, security groups
│   ├── rds/                  # PostgreSQL database
│   ├── elasticache/          # Redis cache cluster
│   ├── s3/                   # Object storage bucket
│   ├── alb/                  # Application load balancer
│   ├── ecs/                  # Fargate container service
│   └── iam/                  # IAM roles and policies
│
└── environments/             # Environment-specific configurations
    ├── dev/
    │   └── terraform.tfvars
    ├── staging/
    │   └── terraform.tfvars
    └── production/
        └── terraform.tfvars
```

## Quick Start

### 1. Initialize Terraform

```bash
cd terraform/environments/dev
terraform init
```

### 2. Review the Plan

```bash
terraform plan -var-file=terraform.tfvars
```

### 3. Apply the Configuration

```bash
terraform apply -var-file=terraform.tfvars
```

### 4. Get Outputs

```bash
terraform output
```

## Environment-Specific Deployment

### Development

```bash
cd terraform/environments/dev
terraform init
terraform plan
terraform apply
```

**Characteristics:**
- Single task instance
- No backups
- Smaller instance types (t3.micro)
- Lower cost for testing

### Staging

```bash
cd terraform/environments/staging
terraform init
terraform plan
terraform apply
```

**Characteristics:**
- 2 task instances
- Automated backups enabled
- Medium instance types (t3.small)
- Production-like configuration for testing

### Production

```bash
cd terraform/environments/production
terraform init
terraform plan
terraform apply
```

**Characteristics:**
- 3 task instances with auto-scaling
- Multi-AZ RDS with 30-day backup retention
- Larger instance types (t3.medium)
- Deletion protection enabled
- Critical service tagging

## Remote State Management

### Enable Remote State (Recommended)

Before deploying to production, set up remote state:

1. Create S3 bucket and DynamoDB table for state locking:

```bash
aws s3api create-bucket \
  --bucket audiobooksync-terraform-state-$(aws sts get-caller-identity --query Account --output text) \
  --region us-east-1

aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5
```

2. Uncomment the backend configuration in `terraform.tf`:

```hcl
backend "s3" {
  bucket         = "audiobooksync-terraform-state-YOUR_ACCOUNT_ID"
  key            = "terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "terraform-locks"
}
```

3. Run `terraform init` to migrate state.

## Important Configuration Notes

### 1. ECR Image URI (CRITICAL)

The ECS task definition currently uses a placeholder image URI. You must:

1. Build and push your Docker image to ECR:

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build image
docker build -t audiobooksync:latest .

# Tag image for ECR
docker tag audiobooksync:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/audiobooksync:latest

# Push to ECR
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/audiobooksync:latest
```

2. Update the image URI in `modules/ecs/main.tf`:

```hcl
image = "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/audiobooksync:latest"
```

### 2. Database Password

The database password is automatically generated and stored in AWS Secrets Manager. Retrieve it:

```bash
aws secretsmanager get-secret-value \
  --secret-id audiobooksync-dev-db-password \
  --query SecretString \
  --output text
```

### 3. Environment Variables

The ECS task automatically configures:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection endpoint
- `AWS_BUCKET_NAME`: S3 bucket name
- `ENVIRONMENT`: Set to "production"

Add additional environment variables by updating the `environment` block in `modules/ecs/main.tf`.

### 4. Sensitive Data

Never commit sensitive information. Examples:
- AWS credentials
- Database passwords
- API keys
- JWT secrets

These should be stored in AWS Secrets Manager and accessed by the ECS task role.

## Monitoring and Logging

### CloudWatch Logs

All ECS logs are sent to CloudWatch:

```bash
# View recent logs
aws logs tail /ecs/audiobooksync-dev --follow

# Tail logs by stream
aws logs tail /ecs/audiobooksync-dev --stream-names ecs/app
```

### CloudWatch Alarms

The infrastructure includes alarms for:
- RDS CPU utilization > 80%
- RDS free storage < 1GB
- Redis CPU utilization > 75%
- Redis memory usage > 90%
- ALB target response time > 2 seconds
- ALB unhealthy hosts

View alarms in the AWS Console or with:

```bash
aws cloudwatch describe-alarms --alarm-names "audiobooksync-*"
```

## Scaling Configuration

### Auto-Scaling (ECS)

Tasks automatically scale based on:
- CPU utilization target: 70%
- Memory utilization target: 80%
- Min tasks: 1 (dev) / 2 (staging) / 3 (production)
- Max tasks: 10

Modify in `modules/ecs/main.tf`:

```hcl
resource "aws_autoscaling_policy" "ecs_policy_cpu" {
  target_value = 70.0  # Adjust this
}
```

### Database Scaling

For production, consider upgrading RDS instance class:

```hcl
# In environments/production/terraform.tfvars
database_instance_class = "db.t3.large"
```

## Cost Optimization

### Development Environment
- Use t3.micro instances (free tier eligible)
- Disable backups
- Single task instance

### Staging Environment
- Use t3.small for testing
- 7-day backup retention

### Production Environment
- Use t3.medium or larger
- 30-day backup retention
- Multi-AZ for high availability
- Reserved instances (RIs) for 40% cost savings

## Terraform Commands Reference

```bash
# Initialize working directory
terraform init

# Format configuration files
terraform fmt -recursive

# Validate configuration
terraform validate

# Plan infrastructure changes
terraform plan

# Apply infrastructure changes
terraform apply

# Destroy infrastructure (USE WITH CAUTION)
terraform destroy

# List all resources
terraform state list

# Show resource details
terraform state show module.rds.aws_db_instance.main

# Export outputs
terraform output -json > outputs.json
```

## Troubleshooting

### Issue: "Error creating DB instance"
- Check RDS subnet group configuration
- Verify security group rules allow port 5432
- Check storage allocation is >= 20 GB

### Issue: "ECS task fails to start"
- Verify ECR image URI is correct
- Check ECS task execution role permissions
- Review CloudWatch logs for errors
- Ensure VPC and security groups are properly configured

### Issue: "ALB shows unhealthy targets"
- Check ECS security group allows port 8000
- Verify FastAPI application starts correctly
- Check container logs in CloudWatch
- Verify health check endpoint is responding

### Issue: "Cannot connect to database from ECS"
- Verify database security group allows port 5432 from ECS security group
- Check RDS is in same VPC as ECS
- Verify database username and password
- Check database subnet group includes all subnets

## Security Best Practices

1. **Enable S3 Block Public Access** ✓ (configured)
2. **Use encryption at rest** ✓ (S3 and RDS configured)
3. **Enable Multi-AZ for production** ✓ (configured)
4. **Use IAM roles instead of access keys** ✓ (configured)
5. **Enable CloudWatch monitoring** ✓ (configured)
6. **Restrict security group ingress** ✓ (configured)
7. **Use AWS Secrets Manager** ✓ (for database password)
8. **Enable VPC Flow Logs** (recommended)
9. **Enable CloudTrail** (recommended)
10. **Use WAF on ALB** (recommended for production)

## Maintenance

### Database Backups

Automated backups:
- Dev: Disabled
- Staging: 7-day retention
- Production: 30-day retention

Manual snapshot:
```bash
aws rds create-db-snapshot \
  --db-instance-identifier audiobooksync-production-postgres \
  --db-snapshot-identifier audiobooksync-snapshot-$(date +%Y%m%d)
```

### Updates and Patches

- Enable `auto_minor_version_upgrade` ✓ (configured)
- Maintenance window: Monday 04:00-05:00 UTC
- Apply critical patches immediately

### Cost Monitoring

```bash
# Estimate monthly costs (requires AWS Cost Explorer)
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-02-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost"
```

## Additional Resources

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [AWS RDS Documentation](https://docs.aws.amazon.com/rds/)
- [AWS ElastiCache Documentation](https://docs.aws.amazon.com/elasticache/)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review CloudWatch logs and metrics
3. Check Terraform plan output for resource issues
4. Consult AWS documentation for service-specific issues

---

**Last Updated:** January 2025
**Version:** 1.0.0
