output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = aws_subnet.private[*].id
}

output "database_subnet_ids" {
  description = "IDs of database subnets"
  value       = aws_subnet.database[*].id
}

output "alb_security_group" {
  description = "ALB security group ID"
  value       = aws_security_group.alb.id
}

output "ecs_security_group" {
  description = "ECS security group ID"
  value       = aws_security_group.ecs.id
}

output "database_security_group" {
  description = "Database security group ID"
  value       = aws_security_group.database.id
}

output "elasticache_security_group" {
  description = "ElastiCache security group ID"
  value       = aws_security_group.elasticache.id
}

output "db_subnet_group_name" {
  description = "Database subnet group name"
  value       = aws_db_subnet_group.main.name
}

output "elasticache_subnet_group_name" {
  description = "ElastiCache subnet group name"
  value       = aws_elasticache_subnet_group.main.name
}
