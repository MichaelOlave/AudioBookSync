locals {
  name_prefix = "${var.app_name}-${var.environment}"

  common_tags = {
    Project     = "AudioBookSync"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
