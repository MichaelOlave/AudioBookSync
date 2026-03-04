output "alb_dns_name" {
  description = "DNS name of the load balancer"
  value       = module.alb.alb_dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = module.ecs.service_name
}

output "rds_endpoint" {
  description = "RDS database endpoint"
  value       = module.rds.database_endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = module.elasticache.redis_endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name for object storage"
  value       = module.s3.bucket_name
}

output "s3_bucket_region" {
  description = "S3 bucket region"
  value       = module.s3.bucket_region
}

output "vpc_id" {
  description = "VPC ID"
  value       = module.vpc.vpc_id
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for ECS"
  value       = module.ecs.cloudwatch_log_group
}

output "application_url" {
  description = "URL to access the application"
  value       = "http://${module.alb.alb_dns_name}"
}
