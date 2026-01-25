output "redis_endpoint" {
  description = "Redis replication group endpoint"
  value       = aws_elasticache_replication_group.redis.configuration_endpoint_address
}

output "redis_primary_endpoint" {
  description = "Redis primary endpoint"
  value       = aws_elasticache_replication_group.redis.primary_endpoint_address
}

output "redis_port" {
  description = "Redis port"
  value       = aws_elasticache_replication_group.redis.port
}

output "redis_replication_group_id" {
  description = "Redis replication group ID"
  value       = aws_elasticache_replication_group.redis.id
}
