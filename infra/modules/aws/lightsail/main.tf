resource "aws_lightsail_container_service" "this" {
  name  = "${var.project_name}-${var.environment}"
  power = var.power
  scale = var.scale
  tags  = merge(var.tags, { Project = var.project_name, Environment = var.environment })
}

resource "aws_lightsail_container_service_deployment_version" "this" {
  service_name = aws_lightsail_container_service.this.name
  container {
    container_name = "app"
    image          = var.image
    environment = merge(var.environment_variables, {
      APP_HOST = "0.0.0.0"
      PORT     = tostring(var.container_port)
    })
    ports = { (tostring(var.container_port)) = "HTTP" }
  }
  public_endpoint {
    container_name = "app"
    container_port = var.container_port
    health_check {
      path                = var.health_check_path
      success_codes       = "200"
      healthy_threshold   = var.health_check.healthy_threshold
      unhealthy_threshold = var.health_check.unhealthy_threshold
      interval_seconds    = var.health_check.interval_seconds
      timeout_seconds     = var.health_check.timeout_seconds
    }
  }
}
