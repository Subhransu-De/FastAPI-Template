module "service" {
  source                      = "../../modules/aws/lambda-web-adapter"
  project_name                = var.project_name
  environment                 = var.environment
  environment_variables       = var.environment_variables
  tags                        = var.tags
  health_check_path           = var.health_check_path
  image                       = var.image
  container_port              = var.container_port
  memory_size                 = var.memory_size
  timeout                     = var.timeout
  architecture                = var.architecture
  authorization_type          = var.authorization_type
  reserved_concurrency        = var.reserved_concurrency
  log_retention_days          = var.log_retention_days
  secrets_manager_environment = var.secrets_manager_environment
  ssm_environment             = var.ssm_environment
}
