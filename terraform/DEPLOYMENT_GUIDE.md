# AudioBookSync AWS Deployment Guide

Complete step-by-step guide to deploy AudioBookSync to AWS using Terraform.

## Prerequisites

### 1. Install Required Tools

**macOS (Homebrew):**
```bash
brew install terraform aws-cli docker
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y terraform awscli docker.io
```

**Windows:**
Download from:
- Terraform: https://www.terraform.io/downloads
- AWS CLI: https://aws.amazon.com/cli/
- Docker Desktop: https://www.docker.com/products/docker-desktop

### 2. AWS Account Setup

1. Create an AWS account if you don't have one
2. Create an IAM user with programmatic access:
   - Console: AWS → IAM → Users → Add User
   - Enable "Programmatic access"
   - Attach policy: `AdministratorAccess` (for initial setup)
3. Save the Access Key ID and Secret Access Key

### 3. Configure AWS CLI

```bash
aws configure
# Enter:
# AWS Access Key ID: [YOUR_ACCESS_KEY]
# AWS Secret Access Key: [YOUR_SECRET_KEY]
# Default region: us-east-1
# Default output format: json
```

Verify configuration:
```bash
aws sts get-caller-identity
```

### 4. Docker Setup

Verify Docker is running:
```bash
docker --version
docker run hello-world
```

## Step 1: Build and Push Docker Image

### 1.1 Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name audiobooksync \
  --region us-east-1
```

Note the repository URI (e.g., `123456789012.dkr.ecr.us-east-1.amazonaws.com/audiobooksync`)

### 1.2 Build Docker Image

From the project root:

```bash
docker build -t audiobooksync:latest .
```

### 1.3 Tag Image for ECR

Replace `123456789012` with your AWS Account ID:

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-east-1
docker tag audiobooksync:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/audiobooksync:latest
```

### 1.4 Login to ECR

```bash
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### 1.5 Push Image to ECR

```bash
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/audiobooksync:latest
```

Verify the image was pushed:
```bash
aws ecr describe-images --repository-name audiobooksync
```

## Step 2: Update Terraform Configuration

### 2.1 Update ECS Task Definition

Edit `terraform/modules/ecs/main.tf` and replace:

```hcl
image = "PLACEHOLDER_IMAGE_URI"
```

With your ECR image URI:

```hcl
image = "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/audiobooksync:latest"
```

Example:
```hcl
image = "123456789012.dkr.ecr.us-east-1.amazonaws.com/audiobooksync:latest"
```

### 2.2 Review Environment-Specific Settings

Choose your deployment environment and review the variables:

**Development:**
```bash
cat terraform/environments/dev/terraform.tfvars
```

**Staging:**
```bash
cat terraform/environments/staging/terraform.tfvars
```

**Production:**
```bash
cat terraform/environments/production/terraform.tfvars
```

## Step 3: Deploy Infrastructure

### 3.1 Initialize Terraform (Development)

```bash
cd terraform/environments/dev
terraform init
```

Output should show: "Terraform has been successfully initialized!"

### 3.2 Plan Deployment

```bash
terraform plan -var-file=terraform.tfvars
```

Review the planned resources. Look for:
- VPC, Subnets, Security Groups
- RDS Database instance
- ElastiCache Redis cluster
- ALB and Target Groups
- ECS Cluster, Service, Task Definition
- IAM Roles

### 3.3 Apply Configuration

```bash
terraform apply -var-file=terraform.tfvars
```

When prompted, type `yes` to confirm.

This will take approximately 15-20 minutes to complete.

### 3.4 Get Outputs

```bash
terraform output
```

You'll see:
```
alb_dns_name = "audiobooksync-dev-alb-1234567890.us-east-1.elb.amazonaws.com"
application_url = "http://audiobooksync-dev-alb-1234567890.us-east-1.elb.amazonaws.com"
ecs_cluster_name = "audiobooksync-dev-cluster"
rds_endpoint = "audiobooksync-dev-postgres.c8d4o7r8q9.us-east-1.rds.amazonaws.com:5432"
s3_bucket_name = "audiobooksync-dev-storage-123456789012"
```

## Step 4: Verify Deployment

### 4.1 Check ECS Service

```bash
# Get cluster name
CLUSTER=$(terraform output -raw ecs_cluster_name)

# Get service name
SERVICE=$(terraform output -raw ecs_service_name)

# Check service status
aws ecs describe-services \
  --cluster $CLUSTER \
  --services $SERVICE \
  --query 'services[0].[serviceName,runningCount,desiredCount]' \
  --output text
```

Wait for `runningCount` to equal `desiredCount`.

### 4.2 Check ALB Health

```bash
ALB_NAME=$(terraform output -raw alb_dns_name | cut -d- -f1-3)

aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw target_group_arn) \
  --query 'TargetHealthDescriptions[*].[Target.Id,TargetHealth.State]' \
  --output table
```

Wait for targets to show `healthy` state.

### 4.3 Access Application

Once targets are healthy, visit the application:

```bash
# Get ALB DNS name
ALB_URL=$(terraform output -raw application_url)
echo "Visit: $ALB_URL"
```

Open in browser: http://your-alb-dns-name

### 4.4 Check Logs

```bash
# Tail application logs
aws logs tail /ecs/audiobooksync-dev --follow
```

## Step 5: Database Initialization

### 5.1 Get Database Credentials

```bash
# Database endpoint
DB_HOST=$(terraform output -raw rds_endpoint | cut -d: -f1)
echo "Database Host: $DB_HOST"

# Database password
DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id audiobooksync-dev-db-password \
  --query SecretString \
  --output text)

# Database name
echo "Database Name: audiobooksync"
echo "Database User: adminuser"
echo "Database Port: 5432"
```

### 5.2 Run Database Migrations

You can run migrations via the ECS task by executing a command in the container.

Alternatively, if you have psql installed locally:

```bash
psql -h $DB_HOST -U adminuser -d audiobooksync -c "SELECT version();"
```

For Alembic migrations:

```bash
# Connect to the running ECS task and run:
alembic upgrade head
```

## Step 6: Configure SSL/TLS (Optional but Recommended)

The current setup uses HTTP. For production, add HTTPS:

### 6.1 Request SSL Certificate (ACM)

```bash
aws acm request-certificate \
  --domain-name yourdomain.com \
  --subject-alternative-names www.yourdomain.com \
  --validation-method DNS
```

### 6.2 Update ALB Listener

Add HTTPS listener to the ALB with the certificate.

### 6.3 Update Terraform

Add HTTPS listener configuration to `modules/alb/main.tf`.

## Step 7: Scale to Production

When ready to deploy to production:

### 7.1 Create Production Environment

```bash
cd terraform/environments/production
terraform init
```

### 7.2 Review Production Settings

Key differences from development:
- 3 ECS tasks (instead of 1)
- Multi-AZ RDS with 30-day backups
- Larger instance types (t3.medium)
- Deletion protection enabled

### 7.3 Deploy Production

```bash
terraform plan -var-file=terraform.tfvars
terraform apply -var-file=terraform.tfvars
```

## Monitoring and Maintenance

### View Metrics

```bash
# ECS task metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=audiobooksync-production-service \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Average
```

### View Alarms

```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix audiobooksync \
  --query 'MetricAlarms[*].[AlarmName,StateValue]' \
  --output table
```

## Troubleshooting

### Issue: Targets Unhealthy

1. Check logs:
   ```bash
   aws logs tail /ecs/audiobooksync-dev --follow
   ```

2. Verify security groups:
   ```bash
   aws ec2 describe-security-groups \
     --group-ids <ecs-security-group-id>
   ```

3. Check if application is responding:
   ```bash
   # Get a running task
   TASK_IP=$(aws ecs describe-tasks \
     --cluster audiobooksync-dev-cluster \
     --tasks $(aws ecs list-tasks --cluster audiobooksync-dev-cluster --query 'taskArns[0]' --output text) \
     --query 'tasks[0].attachments[0].details[?name==`privateIPv4Address`].value' \
     --output text)

   # Test health endpoint
   curl http://$TASK_IP:8000/health
   ```

### Issue: Database Connection Failed

1. Verify security group allows RDS traffic:
   ```bash
   aws ec2 describe-security-groups \
     --group-ids <rds-security-group-id>
   ```

2. Check RDS status:
   ```bash
   aws rds describe-db-instances \
     --db-instance-identifier audiobooksync-dev-postgres \
     --query 'DBInstances[0].[DBInstanceIdentifier,DBInstanceStatus]'
   ```

3. Verify database credentials:
   ```bash
   psql -h <db-host> -U adminuser -d audiobooksync
   ```

### Issue: High Costs

1. Check resource utilization:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/RDS \
     --metric-name CPUUtilization \
     --dimensions Name=DBInstanceIdentifier,Value=audiobooksync-dev-postgres \
     --start-time 2024-01-01T00:00:00Z \
     --end-time 2024-01-02T00:00:00Z \
     --period 3600 \
     --statistics Average
   ```

2. Consider downsizing non-critical environments

3. Enable Reserved Instances for production

## Cleanup

### Destroy Development Environment

```bash
cd terraform/environments/dev
terraform destroy -var-file=terraform.tfvars
```

**Warning**: This will permanently delete all resources including databases and data!

### Before Destroying Production

1. Create final RDS snapshot:
   ```bash
   aws rds create-db-snapshot \
     --db-instance-identifier audiobooksync-production-postgres \
     --db-snapshot-identifier audiobooksync-final-snapshot-$(date +%Y%m%d-%H%M%S)
   ```

2. Export important data from S3:
   ```bash
   aws s3 sync s3://audiobooksync-production-storage-123456789012 ./backup/
   ```

3. Then destroy:
   ```bash
   cd terraform/environments/production
   terraform destroy -var-file=terraform.tfvars
   ```

## Next Steps

1. Set up CI/CD pipeline (GitHub Actions, GitLab CI, etc.)
2. Configure auto-scaling policies
3. Set up backup and disaster recovery
4. Configure CloudFlare Tunnel for secure access
5. Set up monitoring dashboards
6. Implement cost optimization strategies

## Support Resources

- [AWS Documentation](https://docs.aws.amazon.com/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)
- [AudioBookSync GitHub](https://github.com/yourusername/audiobooksync)

---

**Last Updated:** January 2025
