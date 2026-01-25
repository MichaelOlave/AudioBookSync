resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "aws_secretsmanager_secret" "db_password" {
  name                    = "${var.name_prefix}-db-password"
  recovery_window_in_days = 7

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db_password.result
}

resource "aws_db_instance" "main" {
  identifier             = "${var.name_prefix}-postgres"
  engine                 = "postgres"
  engine_version         = var.engine_version
  instance_class         = var.instance_class
  allocated_storage      = var.allocated_storage
  storage_type           = "gp3"
  storage_encrypted      = true
  username               = "adminuser"
  password               = random_password.db_password.result
  db_name                = "audiobooksync"
  publicly_accessible    = false
  db_subnet_group_name   = var.db_subnet_group_name
  vpc_security_group_ids = [var.database_security_group]
  multi_az               = var.environment == "production" ? true : false
  skip_final_snapshot    = var.environment != "production"
  final_snapshot_identifier_prefix = "${var.name_prefix}-final-snapshot"

  backup_retention_period = var.enable_backup ? (var.environment == "production" ? 30 : 7) : 0
  backup_window           = "03:00-04:00"
  maintenance_window      = "mon:04:00-mon:05:00"

  enabled_cloudwatch_logs_exports = ["postgresql"]
  copy_tags_to_snapshot           = true

  deletion_protection = var.environment == "production" ? true : false

  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-postgres"
    }
  )

  depends_on = [
    aws_secretsmanager_secret_version.db_password
  ]
}

resource "aws_cloudwatch_metric_alarm" "database_cpu" {
  alarm_name          = "${var.name_prefix}-db-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Alert when RDS CPU exceeds 80%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}

resource "aws_cloudwatch_metric_alarm" "database_storage" {
  alarm_name          = "${var.name_prefix}-db-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 1000000000  # 1GB in bytes
  alarm_description   = "Alert when RDS free storage is below 1GB"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DBInstanceIdentifier = aws_db_instance.main.id
  }
}
