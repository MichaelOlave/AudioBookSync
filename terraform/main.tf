module "iam" {
  source = "./modules/iam"

  name_prefix = local.name_prefix
  environment = var.environment

  tags = local.common_tags
}

module "vpc" {
  source = "./modules/vpc"

  name_prefix = local.name_prefix
  environment = var.environment
  vpc_cidr    = var.vpc_cidr

  tags = local.common_tags
}

module "s3" {
  source = "./modules/s3"

  name_prefix = local.name_prefix
  environment = var.environment

  tags = local.common_tags
}

module "rds" {
  source = "./modules/rds"

  name_prefix              = local.name_prefix
  environment              = var.environment
  vpc_id                   = module.vpc.vpc_id
  db_subnet_group_name     = module.vpc.db_subnet_group_name
  database_security_group  = module.vpc.database_security_group
  engine_version           = var.database_engine_version
  instance_class           = var.database_instance_class
  allocated_storage        = var.database_allocated_storage
  enable_backup            = var.enable_backup

  tags = local.common_tags

  depends_on = [module.vpc]
}

module "elasticache" {
  source = "./modules/elasticache"

  name_prefix                = local.name_prefix
  environment                = var.environment
  subnet_group_name          = module.vpc.elasticache_subnet_group_name
  elasticache_security_group = module.vpc.elasticache_security_group
  node_type                  = var.redis_node_type

  tags = local.common_tags

  depends_on = [module.vpc]
}

module "alb" {
  source = "./modules/alb"

  name_prefix = local.name_prefix
  environment = var.environment
  vpc_id      = module.vpc.vpc_id
  subnets     = module.vpc.public_subnet_ids
  alb_security_group = module.vpc.alb_security_group

  tags = local.common_tags

  depends_on = [module.vpc]
}

module "ecs" {
  source = "./modules/ecs"

  name_prefix                    = local.name_prefix
  environment                    = var.environment
  container_port                 = var.container_port
  container_cpu                  = var.container_cpu
  container_memory               = var.container_memory
  desired_count                  = var.desired_count
  vpc_id                         = module.vpc.vpc_id
  private_subnet_ids             = module.vpc.private_subnet_ids
  ecs_security_group             = module.vpc.ecs_security_group
  target_group_arn               = module.alb.target_group_arn
  ecs_task_execution_role_arn    = module.iam.ecs_task_execution_role_arn
  ecs_task_role_arn              = module.iam.ecs_task_role_arn
  database_host                  = module.rds.database_endpoint
  database_port                  = module.rds.database_port
  database_name                  = module.rds.database_name
  redis_endpoint                 = module.elasticache.redis_endpoint
  s3_bucket_name                 = module.s3.bucket_name
  cloudwatch_log_group           = local.name_prefix

  tags = local.common_tags

  depends_on = [module.rds, module.elasticache, module.alb, module.s3, module.iam]
}
