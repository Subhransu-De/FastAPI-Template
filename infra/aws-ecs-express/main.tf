resource "aws_cloudwatch_log_group" "app" {
  name              = local.log_group_name
  retention_in_days = var.log_retention_days
  kms_key_id        = var.log_group_kms_key_arn
}

resource "aws_ecs_cluster" "app" {
  name = local.service_name
}

resource "aws_ecs_express_gateway_service" "app" {
  cluster                 = aws_ecs_cluster.app.name
  cpu                     = tostring(var.cpu)
  execution_role_arn      = aws_iam_role.execution.arn
  health_check_path       = var.health_check_path
  infrastructure_role_arn = aws_iam_role.infrastructure.arn
  memory                  = tostring(var.memory)
  service_name            = local.service_name
  wait_for_steady_state   = true

  primary_container {
    container_port = var.container_port
    image          = var.container_image

    aws_logs_configuration {
      log_group         = aws_cloudwatch_log_group.app.name
      log_stream_prefix = "app"
    }

    dynamic "environment" {
      for_each = local.container_environment

      content {
        name  = environment.key
        value = environment.value
      }
    }

    dynamic "secret" {
      for_each = var.secrets

      content {
        name       = secret.key
        value_from = secret.value
      }
    }
  }

  dynamic "network_configuration" {
    for_each = length(var.subnet_ids) == 0 && length(var.security_group_ids) == 0 ? [] : [true]

    content {
      security_groups = length(var.security_group_ids) == 0 ? null : var.security_group_ids
      subnets         = length(var.subnet_ids) == 0 ? null : var.subnet_ids
    }
  }

  scaling_target {
    auto_scaling_metric       = var.autoscaling_metric
    auto_scaling_target_value = var.autoscaling_target_value
    max_task_count            = var.max_task_count
    min_task_count            = var.min_task_count
  }

  lifecycle {
    precondition {
      condition     = length(setintersection(toset(keys(local.container_environment)), toset(keys(var.secrets)))) == 0
      error_message = "An environment variable name cannot appear in both environment_variables and secrets."
    }
  }

  # The current AWS provider requires these dependencies so policies remain
  # attached until the managed service finishes draining during deletion.
  depends_on = [
    aws_iam_role_policy_attachment.execution,
    aws_iam_role_policy_attachment.infrastructure,
    aws_iam_role_policy.execution_kms,
    aws_iam_role_policy.execution_secrets_manager,
    aws_iam_role_policy.execution_ssm,
  ]
}
