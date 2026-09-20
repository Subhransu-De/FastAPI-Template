module "lightsail" {
  source                = "../../modules/aws/lightsail"
  project_name          = var.project_name
  environment           = var.environment
  image                 = var.image
  power                 = var.power
  scale                 = var.scale
  container_port        = var.container_port
  health_check_path     = var.health_check_path
  health_check          = var.health_check
  environment_variables = var.environment_variables
  tags                  = var.tags
}
