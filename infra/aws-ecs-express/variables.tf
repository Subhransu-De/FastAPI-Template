variable "additional_tags" {
  description = "Additional tags applied to taggable resources. Project, Environment, and ManagedBy are enforced by the provider."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for key in keys(var.additional_tags) : !startswith(lower(key), "aws:")])
    error_message = "additional_tags keys must not use the reserved aws: prefix."
  }
}

variable "autoscaling_metric" {
  description = "Metric used by ECS Express Mode target tracking."
  type        = string
  default     = "AVERAGE_CPU"

  validation {
    condition     = contains(["AVERAGE_CPU", "AVERAGE_MEMORY", "REQUEST_COUNT_PER_TARGET"], var.autoscaling_metric)
    error_message = "autoscaling_metric must be AVERAGE_CPU, AVERAGE_MEMORY, or REQUEST_COUNT_PER_TARGET."
  }
}

variable "autoscaling_target_value" {
  description = "Target value for the selected autoscaling metric."
  type        = number
  default     = 60

  validation {
    condition = (
      var.autoscaling_target_value > 0 &&
      (var.autoscaling_metric == "REQUEST_COUNT_PER_TARGET" || var.autoscaling_target_value <= 100)
    )
    error_message = "autoscaling_target_value must be greater than zero and at most 100 for CPU or memory metrics."
  }
}

variable "aws_region" {
  description = "AWS Region in which to deploy the service."
  type        = string
  default     = "ap-south-1"

  validation {
    condition     = can(regex("^[a-z]{2}(-[a-z]+)+-[0-9]+$", var.aws_region))
    error_message = "aws_region must be a valid AWS Region identifier."
  }
}

variable "container_image" {
  description = "Container image URI. Use an immutable digest for production deployments."
  type        = string

  validation {
    condition     = length(trimspace(var.container_image)) > 0
    error_message = "container_image must not be empty."
  }
}

variable "container_port" {
  description = "TCP port exposed by the FastAPI container. Use an unprivileged port for this non-root image."
  type        = number
  default     = 8080

  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535
    error_message = "container_port must be between 1 and 65535."
  }
}

variable "cpu" {
  description = "Fargate CPU units allocated to the task."
  type        = number
  default     = 256

  validation {
    condition     = contains([256, 512, 1024, 2048, 4096], var.cpu)
    error_message = "cpu must be one of 256, 512, 1024, 2048, or 4096."
  }
}

variable "environment" {
  description = "Short deployment environment name used in names and tags."
  type        = string
  default     = "dev"

  validation {
    condition     = length(var.environment) <= 12 && can(regex("^[a-z][a-z0-9-]*$", var.environment))
    error_message = "environment must start with a lowercase letter, contain only lowercase letters, digits, or hyphens, and be at most 12 characters."
  }
}

variable "environment_variables" {
  description = "Non-secret environment variables passed to the container. Use secrets for sensitive values."
  type        = map(string)
  default     = {}

  validation {
    condition     = alltrue([for key in keys(var.environment_variables) : can(regex("^[A-Za-z_][A-Za-z0-9_]*$", key))])
    error_message = "environment_variables keys must be valid environment variable names."
  }
}

variable "health_check_path" {
  description = "HTTP path used by the managed target group health check."
  type        = string
  default     = "/health"

  validation {
    condition     = startswith(var.health_check_path, "/") && !strcontains(var.health_check_path, "?")
    error_message = "health_check_path must start with / and must not include a query string."
  }
}

variable "log_group_kms_key_arn" {
  description = "Optional customer-managed KMS key ARN for CloudWatch Logs encryption. The key policy must permit the regional CloudWatch Logs service."
  type        = string
  default     = null

  validation {
    condition     = var.log_group_kms_key_arn == null || can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/", var.log_group_kms_key_arn))
    error_message = "log_group_kms_key_arn must be a KMS key ARN."
  }
}

variable "log_retention_days" {
  description = "CloudWatch Logs retention in days."
  type        = number
  default     = 30

  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653], var.log_retention_days)
    error_message = "log_retention_days must be a value supported by CloudWatch Logs."
  }
}

variable "max_task_count" {
  description = "Maximum number of tasks used by autoscaling."
  type        = number
  default     = 4

  validation {
    condition     = var.max_task_count >= 1 && var.max_task_count >= var.min_task_count
    error_message = "max_task_count must be at least one and greater than or equal to min_task_count."
  }
}

variable "memory" {
  description = "Memory in MiB allocated to the Fargate task."
  type        = number
  default     = 512

  validation {
    condition = contains(lookup({
      256  = [512, 1024, 2048]
      512  = [1024, 2048, 3072, 4096]
      1024 = [2048, 3072, 4096, 5120, 6144, 7168, 8192]
      2048 = [4096, 5120, 6144, 7168, 8192]
      4096 = [8192]
    }, var.cpu, []), var.memory)
    error_message = "cpu and memory must form a valid Fargate task size supported by ECS Express Mode."
  }
}

variable "min_task_count" {
  description = "Minimum number of tasks maintained by the service."
  type        = number
  default     = 1

  validation {
    condition     = var.min_task_count >= 1
    error_message = "min_task_count must be at least one."
  }
}

variable "project_name" {
  description = "Project identifier used in names and tags."
  type        = string
  default     = "fastapi-template"

  validation {
    condition     = length(var.project_name) <= 24 && can(regex("^[a-z][a-z0-9-]*$", var.project_name))
    error_message = "project_name must start with a lowercase letter, contain only lowercase letters, digits, or hyphens, and be at most 24 characters."
  }
}

variable "secrets" {
  description = "Map of environment variable names to Secrets Manager secret ARNs or SSM parameter ARNs. Secret values never enter Terraform configuration or state."
  type        = map(string)
  default     = {}

  validation {
    condition = alltrue([
      for arn in values(var.secrets) :
      can(regex("^arn:[^:]+:secretsmanager:[^:]+:[0-9]{12}:secret:.+", arn)) ||
      can(regex("^arn:[^:]+:ssm:[^:]+:[0-9]{12}:parameter/.+", arn))
    ])
    error_message = "Each secrets value must be a Secrets Manager secret ARN or SSM parameter ARN."
  }

  validation {
    condition     = alltrue([for key in keys(var.secrets) : can(regex("^[A-Za-z_][A-Za-z0-9_]*$", key))])
    error_message = "secrets keys must be valid environment variable names."
  }
}

variable "secrets_kms_key_arns" {
  description = "Customer-managed KMS key ARNs needed to decrypt configured secrets."
  type        = set(string)
  default     = []

  validation {
    condition = alltrue([
      for arn in var.secrets_kms_key_arns : can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/", arn))
    ])
    error_message = "Every secrets_kms_key_arns value must be a KMS key ARN."
  }
}

variable "security_group_ids" {
  description = "Optional security groups for the service. When omitted, ECS Express Mode creates managed security groups."
  type        = set(string)
  default     = []

  validation {
    condition     = alltrue([for id in var.security_group_ids : can(regex("^sg-[0-9a-f]+$", id))])
    error_message = "Every security_group_ids value must be an AWS security group ID."
  }
}

variable "service_name" {
  description = "Optional ECS service name. Defaults to project_name-environment."
  type        = string
  default     = null

  validation {
    condition     = var.service_name == null || (length(var.service_name) <= 40 && can(regex("^[a-zA-Z0-9][a-zA-Z0-9_-]*$", var.service_name)))
    error_message = "service_name must contain only letters, digits, underscores, or hyphens and be at most 40 characters."
  }
}

variable "subnet_ids" {
  description = "Optional subnet IDs. Supply at least two; otherwise ECS Express Mode uses default public subnets."
  type        = set(string)
  default     = []

  validation {
    condition     = length(var.subnet_ids) == 0 || length(var.subnet_ids) >= 2
    error_message = "subnet_ids must be empty or contain at least two subnet IDs."
  }

  validation {
    condition     = alltrue([for id in var.subnet_ids : can(regex("^subnet-[0-9a-f]+$", id))])
    error_message = "Every subnet_ids value must be an AWS subnet ID."
  }
}
