.PHONY: help init plan apply destroy fmt validate

# Set default environment to dev if not specified
ENV ?= dev
ENV_PATH := environments/$(ENV)
TFVARS := $(ENV_PATH)/terraform.tfvars

help:
	@echo "AudioBookSync Terraform Management"
	@echo "===================================="
	@echo ""
	@echo "Available commands:"
	@echo "  make init ENV=<env>       - Initialize Terraform (default: dev)"
	@echo "  make plan ENV=<env>       - Plan infrastructure changes"
	@echo "  make apply ENV=<env>      - Apply infrastructure changes"
	@echo "  make destroy ENV=<env>    - Destroy infrastructure (USE WITH CAUTION)"
	@echo "  make fmt                  - Format all Terraform files"
	@echo "  make validate             - Validate all Terraform files"
	@echo "  make output ENV=<env>     - Show outputs for environment"
	@echo "  make logs ENV=<env>       - Tail CloudWatch logs"
	@echo "  make cost ENV=<env>       - Show cost estimate (terraform >= 1.5)"
	@echo ""
	@echo "Environments: dev, staging, production"
	@echo ""
	@echo "Examples:"
	@echo "  make plan ENV=production"
	@echo "  make apply ENV=staging"
	@echo "  make destroy ENV=dev"

init:
	@echo "Initializing Terraform for $(ENV) environment..."
	@cd $(ENV_PATH) && terraform init

plan:
	@echo "Planning infrastructure changes for $(ENV) environment..."
	@cd $(ENV_PATH) && terraform plan -var-file=$(TFVARS)

apply:
	@echo "Applying infrastructure changes for $(ENV) environment..."
	@echo "WARNING: This will create/modify AWS resources!"
	@cd $(ENV_PATH) && terraform apply -var-file=$(TFVARS)

destroy:
	@echo "WARNING: This will DESTROY all infrastructure for $(ENV) environment!"
	@echo "Press Ctrl+C to cancel..."
	@sleep 5
	@cd $(ENV_PATH) && terraform destroy -var-file=$(TFVARS)

fmt:
	@echo "Formatting Terraform files..."
	@terraform fmt -recursive .

validate:
	@echo "Validating Terraform configuration..."
	@terraform validate

output:
	@echo "Outputs for $(ENV) environment:"
	@cd $(ENV_PATH) && terraform output

logs:
	@echo "Tailing CloudWatch logs for $(ENV) environment..."
	@aws logs tail /ecs/audiobooksync-$(ENV) --follow

state-list:
	@echo "Resources in $(ENV) environment:"
	@cd $(ENV_PATH) && terraform state list

state-show:
	@echo "State for $(ENV) environment:"
	@cd $(ENV_PATH) && terraform state show

refresh:
	@echo "Refreshing state for $(ENV) environment..."
	@cd $(ENV_PATH) && terraform refresh -var-file=$(TFVARS)

clean:
	@echo "Cleaning Terraform cache..."
	@find . -type d -name .terraform -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name '*.tfstate*' -delete 2>/dev/null || true
	@echo "Clean complete"

# Advanced targets

import-resource:
	@echo "Usage: make import-resource ENV=<env> RESOURCE=<resource_type> ID=<resource_id>"
	@echo "Example: make import-resource ENV=dev RESOURCE=aws_instance.example ID=i-1234567890abcdef0"
	@cd $(ENV_PATH) && terraform import -var-file=$(TFVARS) $(RESOURCE) $(ID)

taint:
	@echo "Usage: make taint ENV=<env> RESOURCE=<resource_address>"
	@echo "Example: make taint ENV=dev RESOURCE=module.vpc.aws_vpc.main"
	@cd $(ENV_PATH) && terraform taint $(RESOURCE)

untaint:
	@echo "Usage: make untaint ENV=<env> RESOURCE=<resource_address>"
	@cd $(ENV_PATH) && terraform untaint $(RESOURCE)

# Utility targets

lock:
	@echo "Acquiring state lock for $(ENV) environment..."
	@cd $(ENV_PATH) && terraform lock

unlock:
	@echo "WARNING: This can cause state corruption if infrastructure is being modified!"
	@cd $(ENV_PATH) && terraform force-unlock

inspect:
	@echo "Inspecting current state for $(ENV) environment..."
	@cd $(ENV_PATH) && terraform state list && echo "" && terraform state show

# Documentation

docs:
	@echo "Generating Terraform documentation..."
	@command -v terraform-docs >/dev/null 2>&1 || (echo "terraform-docs not installed. Install with: brew install terraform-docs"; exit 1)
	@terraform-docs markdown table . > TERRAFORM_DOCS.md

# CI/CD helpers

validate-all:
	@echo "Validating all environments..."
	@for env in dev staging production; do \
		echo "Validating $$env..."; \
		cd environments/$$env && terraform validate && cd ../../; \
	done

plan-all:
	@echo "Planning all environments..."
	@for env in dev staging production; do \
		echo "Planning $$env..."; \
		cd environments/$$env && terraform plan -var-file=terraform.tfvars && cd ../../; \
	done
