# Terraform Setup for AudioBookSync - Summary

This document summarizes the Terraform infrastructure-as-code setup added to AudioBookSync for AWS deployment.

## What Was Added

A complete production-ready Terraform configuration has been added to the `terraform/` directory that enables you to:

1. **Deploy AudioBookSync to AWS** with all required infrastructure
2. **Manage multiple environments** (dev, staging, production)
3. **Automate infrastructure changes** with version control
4. **Scale applications** automatically based on demand
5. **Monitor infrastructure** with CloudWatch alarms

## Infrastructure Architecture

The Terraform configuration deploys:

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS                                   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  VPC (10.0.0.0/16 - 10.2.0.0/16)                    │   │
│  │                                                       │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  Public Subnets (ALB)                       │    │   │
│  │  │  ┌──────────────────────────────────────┐   │    │   │
│  │  │  │  ALB (Load Balancer)                 │   │    │   │
│  │  │  │  - Port 80 (HTTP)                    │   │    │   │
│  │  │  │  - Health Checks                     │   │    │   │
│  │  │  └──────────────────────────────────────┘   │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │                        ↓                            │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  Private Subnets (ECS + Redis)              │    │   │
│  │  │  ┌──────────────────────────────────────┐   │    │   │
│  │  │  │  ECS Fargate Cluster                 │   │    │   │
│  │  │  │  - FastAPI Tasks (1-10)              │   │    │   │
│  │  │  │  - Auto-scaling                      │   │    │   │
│  │  │  │  - CloudWatch Logs                   │   │    │   │
│  │  │  └──────────────────────────────────────┘   │    │   │
│  │  │  ┌──────────────────────────────────────┐   │    │   │
│  │  │  │  ElastiCache Redis                   │   │    │   │
│  │  │  │  - Multi-AZ Replication              │   │    │   │
│  │  │  │  - Automatic Failover                │   │    │   │
│  │  │  └──────────────────────────────────────┘   │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │                        ↓                            │   │
│  │  ┌─────────────────────────────────────────────┐    │   │
│  │  │  Database Subnets                          │    │   │
│  │  │  ┌──────────────────────────────────────┐   │    │   │
│  │  │  │  RDS PostgreSQL (Multi-AZ)           │   │    │   │
│  │  │  │  - Automated Backups                 │   │    │   │
│  │  │  │  - Encryption at Rest                │   │    │   │
│  │  │  │  - Enhanced Monitoring               │   │    │   │
│  │  │  └──────────────────────────────────────┘   │    │   │
│  │  └─────────────────────────────────────────────┘    │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  S3 Storage                                 │   │   │
│  │  │  - Versioning Enabled                       │   │   │
│  │  │  - Encryption                               │   │   │
│  │  │  - Lifecycle Policies                       │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
terraform/
├── terraform.tf                    # Provider & backend config
├── main.tf                         # Module orchestration
├── variables.tf                    # Root variables
├── outputs.tf                      # Root outputs
├── locals.tf                       # Local values
├── README.md                       # Full documentation
├── DEPLOYMENT_GUIDE.md             # Step-by-step deployment
├── Makefile                        # Useful commands
├── quickstart.sh                   # Quick start script
├── .gitignore                      # Git ignore rules
│
├── modules/
│   ├── vpc/                        # Network infrastructure
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── rds/                        # PostgreSQL database
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── elasticache/                # Redis cache
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── s3/                         # Object storage
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── alb/                        # Load balancer
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── ecs/                        # Container orchestration
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── iam/                        # Identity & access
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
└── environments/
    ├── dev/
    │   └── terraform.tfvars        # Dev environment config
    ├── staging/
    │   └── terraform.tfvars        # Staging environment config
    └── production/
        └── terraform.tfvars        # Production environment config
```

## Key Features

### Infrastructure Features

- **Auto-Scaling**: ECS tasks scale based on CPU/memory (70%/80% thresholds)
- **High Availability**: Multi-AZ deployment for RDS and Redis
- **Security**:
  - VPC with private/public subnets
  - Security groups with least-privilege rules
  - Encryption at rest (S3, RDS)
  - IAM roles and policies
  - AWS Secrets Manager for database passwords
- **Monitoring**:
  - CloudWatch logs for all services
  - CloudWatch alarms for critical metrics
  - Container Insights for ECS
- **Backups**:
  - Automated RDS backups (7-30 days depending on environment)
  - S3 versioning and lifecycle policies

### Environment Configurations

| Feature | Dev | Staging | Production |
|---------|-----|---------|-----------|
| ECS Tasks | 1 | 2 | 3 (auto-scaling to 10) |
| RDS Instance | t3.micro | t3.small | t3.medium |
| Redis Node | cache.t3.micro | cache.t3.small | cache.t3.medium |
| Backups | Disabled | 7 days | 30 days |
| Multi-AZ | No | Optional | Yes |
| Cost/Month | $40-50 | $80-100 | $150-200 |

## Getting Started

### Option 1: Quick Start (Recommended)

```bash
cd terraform
bash quickstart.sh
```

This script will:
1. Check prerequisites (Terraform, AWS CLI, Docker)
2. Build and push Docker image to ECR
3. Update Terraform configuration
4. Initialize Terraform
5. Create a deployment plan

### Option 2: Manual Setup

1. **Install prerequisites**: Terraform, AWS CLI, Docker
2. **Configure AWS credentials**: `aws configure`
3. **Build and push Docker image**:
   ```bash
   docker build -t audiobooksync:latest .
   aws ecr create-repository --repository-name audiobooksync
   # Push to ECR and update ECS task definition
   ```
4. **Initialize Terraform**:
   ```bash
   cd terraform/environments/dev
   terraform init
   ```
5. **Plan deployment**:
   ```bash
   terraform plan -var-file=terraform.tfvars
   ```
6. **Apply configuration**:
   ```bash
   terraform apply -var-file=terraform.tfvars
   ```

## Important Next Steps

### CRITICAL: Update ECS Task Definition

Edit `terraform/modules/ecs/main.tf` and replace:
```hcl
image = "PLACEHOLDER_IMAGE_URI"
```

With your ECR image URI:
```hcl
image = "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/audiobooksync:latest"
```

### Setup Remote State (for teams)

Enable S3 backend for state management:

1. Create S3 bucket and DynamoDB table
2. Uncomment backend configuration in `terraform.tf`
3. Run `terraform init` to migrate state

## Common Commands

### Using Make

```bash
# Plan for development
make plan ENV=dev

# Apply staging configuration
make apply ENV=staging

# Destroy development environment
make destroy ENV=dev

# Format all Terraform files
make fmt

# Validate configuration
make validate
```

### Using Terraform Directly

```bash
cd terraform/environments/dev

# Initialize
terraform init

# Plan
terraform plan -var-file=terraform.tfvars

# Apply
terraform apply -var-file=terraform.tfvars

# Destroy
terraform destroy -var-file=terraform.tfvars

# Get outputs
terraform output
```

## Accessing Your Deployment

After deployment completes:

```bash
cd terraform/environments/dev
terraform output

# Output will show:
# alb_dns_name = "audiobooksync-dev-alb-XXXXX.us-east-1.elb.amazonaws.com"
# application_url = "http://audiobooksync-dev-alb-XXXXX.us-east-1.elb.amazonaws.com"
```

Visit the application URL in your browser. Allow 2-5 minutes for targets to become healthy.

## Monitoring

### View Logs

```bash
# Tail ECS application logs
aws logs tail /ecs/audiobooksync-dev --follow

# View specific container
aws logs tail /ecs/audiobooksync-dev --stream-names ecs/app
```

### Check Health

```bash
# List tasks
aws ecs list-tasks --cluster audiobooksync-dev-cluster

# Describe task
aws ecs describe-tasks \
  --cluster audiobooksync-dev-cluster \
  --tasks <task-arn>

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn <target-group-arn>
```

## Cost Estimation

**Development Environment**
- ECS: $5-10/month
- RDS: $15-20/month
- ElastiCache: $10-15/month
- S3: <$1/month
- ALB: $16/month
- **Total: $46-62/month**

**Production Environment**
- ECS: $25-30/month
- RDS: $50-60/month
- ElastiCache: $30-40/month
- S3: $5-10/month
- ALB: $16/month
- **Total: $126-156/month**

*Note: Costs vary by region and usage. Use AWS Cost Calculator for accurate estimates.*

## Scaling Recommendations

### When to Scale Up

- CPU utilization consistently > 80%
- Memory utilization consistently > 90%
- Database query times > 2 seconds
- Request latency > 1 second

### How to Scale

1. **ECS Tasks**: Modify `desired_count` in environment tfvars
2. **RDS**: Upgrade instance class
3. **Redis**: Upgrade node type
4. **Auto-scaling**: Configure in `modules/ecs/main.tf`

## Troubleshooting

### Targets Unhealthy

1. Check ECS task logs
2. Verify security group allows port 8000
3. Ensure database connectivity
4. Check Redis connectivity

### High Costs

1. Review CloudWatch metrics
2. Downsize non-critical environments
3. Enable Reserved Instances
4. Review S3 lifecycle policies

### Connection Issues

1. Verify security groups
2. Check RDS/Redis endpoints
3. Review ALB target group health
4. Check route tables and NAT gateways

## Documentation

- **README.md** - Comprehensive Terraform documentation
- **DEPLOYMENT_GUIDE.md** - Complete deployment walkthrough
- **Makefile** - Available commands with examples
- **terraform/modules/*/main.tf** - Inline comments explaining resources

## Support

For issues:
1. Check relevant documentation in `terraform/` directory
2. Review CloudWatch logs and metrics
3. Consult AWS documentation
4. Check Terraform state: `terraform state show`
5. Review security group rules and IAM policies

## Next Steps

1. Deploy to development environment first
2. Test application thoroughly
3. Set up CI/CD pipeline (GitHub Actions, etc.)
4. Configure SSL/TLS certificates (ACM)
5. Set up monitoring dashboards
6. Plan backup and disaster recovery
7. Deploy to staging for testing
8. Deploy to production when ready

---

**Last Updated:** January 2025
**Terraform Version:** >= 1.0
**AWS Provider Version:** >= 5.0
