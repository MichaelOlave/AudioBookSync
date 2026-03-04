#!/bin/bash

# AudioBookSync Terraform Quick Start Script
# This script helps you get started with deploying AudioBookSync to AWS

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║    AudioBookSync Terraform Quick Start                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"
echo ""

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}✗ Terraform not found. Install from https://www.terraform.io/downloads${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Terraform installed$(terraform version | head -1 | awk '{print $NF}')${NC}"
fi

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}✗ AWS CLI not found. Install from https://aws.amazon.com/cli/${NC}"
    exit 1
else
    echo -e "${GREEN}✓ AWS CLI installed${NC}"
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}✗ AWS credentials not configured. Run 'aws configure'${NC}"
    exit 1
else
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo -e "${GREEN}✓ AWS credentials configured (Account: $ACCOUNT_ID)${NC}"
fi

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker not found. Install from https://www.docker.com/products/docker-desktop${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Docker installed${NC}"
fi

echo ""

# Select environment
echo -e "${BLUE}Select deployment environment:${NC}"
echo "1) Development (smallest, fastest, cheapest)"
echo "2) Staging (medium, good for testing)"
echo "3) Production (largest, most reliable, most expensive)"
echo ""
read -p "Enter choice [1-3]: " env_choice

case $env_choice in
    1) ENV="dev" ;;
    2) ENV="staging" ;;
    3) ENV="production" ;;
    *) echo "Invalid choice"; exit 1 ;;
esac

ENV_PATH="environments/$ENV"

echo ""
echo -e "${BLUE}Building and pushing Docker image to ECR...${NC}"
echo ""

# Create ECR repository
echo "Creating ECR repository..."
aws ecr create-repository --repository-name audiobooksync --region us-east-1 2>/dev/null || true

# Get repository URI
ECR_URI="$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/audiobooksync:latest"

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
if [ ! -f "Dockerfile" ]; then
    echo -e "${RED}✗ Dockerfile not found in project root${NC}"
    echo -e "${YELLOW}Please ensure you're in the project root directory${NC}"
    exit 1
fi

docker build -t audiobooksync:latest -f Dockerfile .

# Login to ECR
echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com"

# Tag image
echo -e "${YELLOW}Tagging Docker image...${NC}"
docker tag audiobooksync:latest "$ECR_URI"

# Push image
echo -e "${YELLOW}Pushing Docker image to ECR...${NC}"
docker push "$ECR_URI"

echo -e "${GREEN}✓ Docker image pushed to ECR${NC}"
echo ""

# Update Terraform configuration
echo -e "${BLUE}Updating Terraform configuration...${NC}"

# Check if we need to update the image URI
if grep -q "PLACEHOLDER_IMAGE_URI" modules/ecs/main.tf; then
    echo -e "${YELLOW}Updating ECS task definition with ECR image URI...${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|PLACEHOLDER_IMAGE_URI|$ECR_URI|g" modules/ecs/main.tf
    else
        sed -i "s|PLACEHOLDER_IMAGE_URI|$ECR_URI|g" modules/ecs/main.tf
    fi
    echo -e "${GREEN}✓ Updated with image URI: $ECR_URI${NC}"
fi

echo ""

# Initialize Terraform
echo -e "${BLUE}Initializing Terraform for $ENV environment...${NC}"
cd "$ENV_PATH"
terraform init
cd - > /dev/null

echo -e "${GREEN}✓ Terraform initialized${NC}"
echo ""

# Plan deployment
echo -e "${BLUE}Planning infrastructure deployment...${NC}"
cd "$ENV_PATH"
terraform plan -var-file=terraform.tfvars -out=tfplan
cd - > /dev/null

echo ""
echo -e "${YELLOW}Review the plan above. If everything looks correct, run:${NC}"
echo ""
echo -e "${GREEN}cd $ENV_PATH && terraform apply tfplan${NC}"
echo ""
echo -e "${YELLOW}Deployment will take approximately 15-20 minutes.${NC}"
echo ""
echo -e "${BLUE}After deployment, run to get access information:${NC}"
echo ""
echo -e "${GREEN}cd $ENV_PATH && terraform output${NC}"
echo ""
echo -e "${BLUE}For more information, see:${NC}"
echo "- README.md - Comprehensive documentation"
echo "- DEPLOYMENT_GUIDE.md - Step-by-step deployment instructions"
echo "- Makefile - Useful commands for managing infrastructure"
echo ""
