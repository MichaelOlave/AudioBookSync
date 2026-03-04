resource "aws_elasticache_replication_group" "redis" {
  replication_group_description = "Redis for ${var.name_prefix}"
  engine                        = "redis"
  engine_version               = "7.0"
  node_type                    = var.node_type
  num_cache_clusters           = 2  # Primary + 1 replica for failover
  parameter_group_name         = aws_elasticache_parameter_group.redis.name
  port                         = 6379
  subnet_group_name            = var.subnet_group_name
  security_group_ids           = [var.elasticache_security_group]
  automatic_failover_enabled   = true
  multi_az_enabled             = true
  at_rest_encryption_enabled   = true
  transit_encryption_enabled   = false  # Set to true if using Redis AUTH
  apply_immediately            = false
  auto_minor_version_upgrade   = true
  maintenance_window           = "mon:03:00-mon:04:00"
  snapshot_retention_limit     = 5
  snapshot_window              = "02:00-03:00"
  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.redis_slow_log.name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
    enabled          = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-redis"
    }
  )
}

resource "aws_elasticache_parameter_group" "redis" {
  family = "redis7"
  name   = "${var.name_prefix}-redis-pg"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "redis_slow_log" {
  name              = "/aws/elasticache/${var.name_prefix}-slow-log"
  retention_in_days = 7

  tags = merge(
    var.tags,
    {
      Name = "${var.name_prefix}-redis-slow-log"
    }
  )
}

resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "${var.name_prefix}-redis-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 75
  alarm_description   = "Alert when Redis CPU exceeds 75%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis.id
  }
}

resource "aws_cloudwatch_metric_alarm" "redis_memory" {
  alarm_name          = "${var.name_prefix}-redis-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DatabaseMemoryUsagePercentage"
  namespace           = "AWS/ElastiCache"
  period              = 300
  statistic           = "Average"
  threshold           = 90
  alarm_description   = "Alert when Redis memory usage exceeds 90%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    ReplicationGroupId = aws_elasticache_replication_group.redis.id
  }
}
