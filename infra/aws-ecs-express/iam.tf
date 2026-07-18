data "aws_partition" "current" {}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      identifiers = ["ecs-tasks.amazonaws.com"]
      type        = "Service"
    }
  }
}

data "aws_iam_policy_document" "ecs_infrastructure_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    effect  = "Allow"

    principals {
      identifiers = ["ecs.amazonaws.com"]
      type        = "Service"
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.service_name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  description        = "Allows ECS to pull the application image, inject secrets, and write logs."
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "${local.managed_policy_prefix}/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets_manager" {
  count = length(local.secrets_manager_arns) == 0 ? 0 : 1

  name = "read-secrets-manager-values"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadConfiguredSecrets"
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = sort(tolist(local.secrets_manager_arns))
    }]
  })
}

resource "aws_iam_role_policy" "execution_ssm" {
  count = length(local.ssm_parameter_arns) == 0 ? 0 : 1

  name = "read-ssm-parameters"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ReadConfiguredParameters"
      Effect   = "Allow"
      Action   = ["ssm:GetParameters"]
      Resource = sort(tolist(local.ssm_parameter_arns))
    }]
  })
}

resource "aws_iam_role_policy" "execution_kms" {
  count = length(var.secrets_kms_key_arns) == 0 ? 0 : 1

  name = "decrypt-configured-secrets"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "DecryptConfiguredSecrets"
      Effect   = "Allow"
      Action   = ["kms:Decrypt"]
      Resource = sort(tolist(var.secrets_kms_key_arns))
    }]
  })
}

resource "aws_iam_role" "infrastructure" {
  name               = "${local.service_name}-infrastructure"
  assume_role_policy = data.aws_iam_policy_document.ecs_infrastructure_assume_role.json
  description        = "Allows ECS Express Mode to manage load balancing, networking, scaling, certificates, and logs."
}

resource "aws_iam_role_policy_attachment" "infrastructure" {
  role       = aws_iam_role.infrastructure.name
  policy_arn = "${local.managed_policy_prefix}/service-role/AmazonECSInfrastructureRoleforExpressGatewayServices"
}
