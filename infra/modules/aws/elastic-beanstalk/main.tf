locals {
  name = "${var.project_name}-${var.environment}"
  tags = merge(var.tags, { Project = var.project_name, Environment = var.environment })
  settings = concat([
    { namespace = "aws:elasticbeanstalk:environment", name = "EnvironmentType", value = var.environment_type },
    { namespace = "aws:elasticbeanstalk:environment", name = "ServiceRole", value = aws_iam_role.service.arn },
    { namespace = "aws:autoscaling:launchconfiguration", name = "IamInstanceProfile", value = aws_iam_instance_profile.this.name },
    { namespace = "aws:autoscaling:launchconfiguration", name = "DisableIMDSv1", value = "true" },
    { namespace = "aws:autoscaling:launchconfiguration", name = "RootVolumeType", value = "gp3" },
    { namespace = "aws:autoscaling:launchconfiguration", name = "RootVolumeSize", value = "10" },
    { namespace = "aws:ec2:instances", name = "InstanceTypes", value = var.instance_type },
    { namespace = "aws:ec2:vpc", name = "VPCId", value = var.vpc_id },
    { namespace = "aws:ec2:vpc", name = "Subnets", value = join(",", var.subnet_ids) },
    { namespace = "aws:ec2:vpc", name = "AssociatePublicIpAddress", value = "true" },
    { namespace = "aws:elasticbeanstalk:application", name = "Application Healthcheck URL", value = var.health_check_path },
    { namespace = "aws:elasticbeanstalk:cloudwatch:logs", name = "StreamLogs", value = "true" },
    { namespace = "aws:elasticbeanstalk:cloudwatch:logs", name = "DeleteOnTerminate", value = "true" },
    { namespace = "aws:elasticbeanstalk:cloudwatch:logs", name = "RetentionInDays", value = tostring(var.log_retention_days) }
    ], var.environment_type == "LoadBalanced" ? [
    { namespace = "aws:elasticbeanstalk:environment", name = "LoadBalancerType", value = "application" },
    { namespace = "aws:ec2:vpc", name = "ELBSubnets", value = join(",", var.subnet_ids) },
    { namespace = "aws:autoscaling:asg", name = "MinSize", value = tostring(var.min_instances) },
    { namespace = "aws:autoscaling:asg", name = "MaxSize", value = tostring(var.max_instances) },
    { namespace = "aws:elasticbeanstalk:environment:process:default", name = "HealthCheckPath", value = var.health_check_path }
    ] : [], var.certificate_arn != null ? [
    { namespace = "aws:elbv2:listener:443", name = "ListenerEnabled", value = "true" },
    { namespace = "aws:elbv2:listener:443", name = "Protocol", value = "HTTPS" },
    { namespace = "aws:elbv2:listener:443", name = "SSLCertificateArns", value = var.certificate_arn },
    { namespace = "aws:elbv2:listener:default", name = "ListenerEnabled", value = "false" }
  ] : [])
}
data "aws_partition" "current" {}
data "aws_subnet" "load_balancer" {
  for_each = var.environment_type == "LoadBalanced" ? toset(var.subnet_ids) : toset([])
  id       = each.value
}
resource "aws_iam_role" "service" {
  name = "${local.name}-eb-service"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "elasticbeanstalk.amazonaws.com" } }]
  })
  tags = local.tags
}
resource "aws_iam_role_policy_attachment" "health" {
  role       = aws_iam_role.service.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSElasticBeanstalkEnhancedHealth"
}
resource "aws_iam_role" "instance" {
  name = "${local.name}-eb-instance"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "ec2.amazonaws.com" } }]
  })
  tags = local.tags
}
resource "aws_iam_role_policy_attachment" "web" {
  role       = aws_iam_role.instance.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/AWSElasticBeanstalkWebTier"
}
resource "aws_iam_role_policy" "bundle" {
  role = aws_iam_role.instance.id
  name = "read-source-bundle"
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = ["s3:GetObject"], Resource = "arn:${data.aws_partition.current.partition}:s3:::${var.source_bundle.bucket}/${var.source_bundle.key}" }]
  })
}
resource "aws_iam_role_policy" "secrets" {
  count = length(var.secret_environment) > 0 ? 1 : 0
  role  = aws_iam_role.instance.id
  name  = "read-app-secrets"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = concat([{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue", "ssm:GetParameter"]
      Resource = values(var.secret_environment)
      }], length(var.secret_kms_key_arns) > 0 ? [{
      Effect   = "Allow"
      Action   = ["kms:Decrypt"]
      Resource = tolist(var.secret_kms_key_arns)
    }] : [])
  })
}
resource "aws_iam_instance_profile" "this" {
  name = "${local.name}-eb"
  role = aws_iam_role.instance.name
  tags = local.tags
}
resource "aws_elastic_beanstalk_application" "this" {
  name = local.name
  tags = local.tags
}
resource "aws_elastic_beanstalk_application_version" "this" {
  name        = var.source_bundle.version_label
  application = aws_elastic_beanstalk_application.this.name
  bucket      = var.source_bundle.bucket
  key         = var.source_bundle.key
  tags        = local.tags
  lifecycle {
    create_before_destroy = true
  }
}
resource "aws_elastic_beanstalk_environment" "this" {
  name                = local.name
  application         = aws_elastic_beanstalk_application.this.name
  version_label       = aws_elastic_beanstalk_application_version.this.name
  solution_stack_name = var.solution_stack_name
  tier                = "WebServer"
  lifecycle {
    precondition {
      condition     = var.environment_type != "LoadBalanced" || length(distinct([for subnet in data.aws_subnet.load_balancer : subnet.availability_zone_id])) >= 2
      error_message = "LoadBalanced requires subnets in at least two Availability Zones."
    }
  }
  setting {
    namespace = "aws:elasticbeanstalk:healthreporting:system"
    name      = "SystemType"
    value     = "enhanced"
  }
  dynamic "setting" {
    for_each = local.settings
    content {
      namespace = setting.value.namespace
      name      = setting.value.name
      value     = setting.value.value
    }
  }
  dynamic "setting" {
    for_each = merge(var.environment_variables, { APP_HOST = "0.0.0.0", PORT = tostring(var.container_port) })
    content {
      namespace = "aws:elasticbeanstalk:application:environment"
      name      = setting.key
      value     = setting.value
    }
  }
  dynamic "setting" {
    for_each = var.secret_environment
    content {
      namespace = "aws:elasticbeanstalk:application:environmentsecrets"
      name      = setting.key
      value     = setting.value
    }
  }
  tags       = local.tags
  depends_on = [aws_iam_role_policy_attachment.health, aws_iam_role_policy_attachment.web, aws_iam_role_policy.bundle, aws_iam_role_policy.secrets]
}
