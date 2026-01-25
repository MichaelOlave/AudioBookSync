output "database_endpoint" {
  description = "RDS database endpoint"
  value       = aws_db_instance.main.endpoint
}

output "database_address" {
  description = "RDS database address (hostname only)"
  value       = aws_db_instance.main.address
}

output "database_port" {
  description = "RDS database port"
  value       = aws_db_instance.main.port
}

output "database_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "database_username" {
  description = "RDS database username"
  value       = aws_db_instance.main.username
}

output "db_password_secret_arn" {
  description = "ARN of the secret containing the database password"
  value       = aws_secretsmanager_secret.db_password.arn
}
