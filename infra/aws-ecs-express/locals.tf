locals {
  service_name   = coalesce(var.service_name, "${var.project_name}-${var.environment}")
  log_group_name = "/aws/ecs/${local.service_name}"
  container_environment = merge(
    var.environment_variables,
    { PORT = tostring(var.container_port) },
  )

  secrets_manager_arns = toset([
    for arn in values(var.secrets) : arn
    if strcontains(arn, ":secretsmanager:")
  ])
  ssm_parameter_arns = toset(concat(
    [
      for arn in values(var.secrets) : arn
      if strcontains(arn, ":ssm:")
    ],
    var.repository_credentials_parameter_arn == null ? [] : [var.repository_credentials_parameter_arn],
  ))

  managed_policy_prefix = "arn:${data.aws_partition.current.partition}:iam::aws:policy"
}
