locals {
  name = "${var.project_name}-${var.environment}"
  tags = merge(var.tags, { Project = var.project_name, Environment = var.environment })
}
data "aws_secretsmanager_secret_version" "environment" {
  for_each  = var.secrets_manager_environment
  secret_id = each.value
}
data "aws_ssm_parameter" "environment" {
  for_each        = var.ssm_environment
  name            = each.value
  with_decryption = true
}
resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = var.log_retention_days
  tags              = local.tags
}
resource "aws_iam_role" "this" {
  name = "${local.name}-lambda"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "lambda.amazonaws.com" } }]
  })
  tags = local.tags
}
resource "aws_iam_role_policy" "logs" {
  name = "write-function-logs"
  role = aws_iam_role.this.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.this.arn}:*"
    }]
  })
}
resource "aws_lambda_function" "this" {
  function_name                  = local.name
  role                           = aws_iam_role.this.arn
  package_type                   = "Image"
  image_uri                      = var.image
  architectures                  = [var.architecture]
  memory_size                    = var.memory_size
  timeout                        = var.timeout
  reserved_concurrent_executions = var.reserved_concurrency
  environment {
    variables = merge(var.environment_variables,
      { for key, secret in data.aws_secretsmanager_secret_version.environment : key => secret.secret_string },
      { for key, parameter in data.aws_ssm_parameter.environment : key => parameter.value },
      {
        APP_HOST                               = "0.0.0.0"
        PORT                                   = tostring(var.container_port)
        AWS_LWA_PORT                           = tostring(var.container_port)
        AWS_LWA_READINESS_CHECK_PATH           = var.health_check_path
        AWS_LWA_READINESS_CHECK_HEALTHY_STATUS = "200"
        AWS_LWA_INVOKE_MODE                    = "buffered"
        AWS_LWA_ASYNC_INIT                     = "true"
        PYTHONDONTWRITEBYTECODE                = "1"
    })
  }
  tags       = local.tags
  depends_on = [aws_iam_role_policy.logs]
}
resource "aws_lambda_function_url" "this" {
  function_name      = aws_lambda_function.this.function_name
  authorization_type = var.authorization_type
  invoke_mode        = "BUFFERED"
}
resource "aws_lambda_permission" "public_url" {
  count                  = var.authorization_type == "NONE" ? 1 : 0
  statement_id           = "PublicFunctionUrl"
  function_name          = aws_lambda_function.this.function_name
  action                 = "lambda:InvokeFunctionUrl"
  principal              = "*"
  function_url_auth_type = "NONE"
}
resource "aws_lambda_permission" "public_invoke" {
  count                    = var.authorization_type == "NONE" ? 1 : 0
  statement_id             = "PublicInvokeViaUrlOnly"
  function_name            = aws_lambda_function.this.function_name
  action                   = "lambda:InvokeFunction"
  principal                = "*"
  invoked_via_function_url = true
}
