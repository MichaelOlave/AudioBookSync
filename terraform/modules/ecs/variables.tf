variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "container_port" {
  description = "Port on which the app container listens"
  type        = number
}

variable "container_cpu" {
  description = "CPU units for ECS task"
  type        = number
}

variable "container_memory" {
  description = "Memory in MB for ECS task"
  type        = number
}

variable "desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "ecs_security_group" {
  description = "ECS security group ID"
  type        = string
}

variable "target_group_arn" {
  description = "ALB target group ARN"
  type        = string
}

variable "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ECS task role ARN"
  type        = string
}

variable "database_host" {
  description = "Database host endpoint"
  type        = string
}

variable "database_port" {
  description = "Database port"
  type        = number
}

variable "database_name" {
  description = "Database name"
  type        = string
}

variable "redis_endpoint" {
  description = "Redis endpoint"
  type        = string
}

variable "s3_bucket_name" {
  description = "S3 bucket name"
  type        = string
}

variable "cloudwatch_log_group" {
  description = "CloudWatch log group name"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
