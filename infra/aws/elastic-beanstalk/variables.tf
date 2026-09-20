variable "project_name" {
  type        = string
  description = "Resource name prefix."
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,28}$", var.project_name))
    error_message = "Use 2-29 lowercase letters, digits or hyphens, starting with a letter."
  }
}
variable "environment" {
  type        = string
  description = "Resource name suffix."
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,8}[a-z0-9]$", var.environment))
    error_message = "Use 2-10 lowercase letters, digits or hyphens, starting with a letter and ending with a letter or digit."
  }
}
variable "environment_variables" {
  type        = map(string)
  description = "Literal application settings; values enter Terraform state."
  sensitive   = true
  default     = {}
}
variable "tags" {
  type        = map(string)
  description = "Resource tags."
  default     = {}
}
variable "health_check_path" {
  type        = string
  description = "Unauthenticated health route."
  default     = "/health"
  validation {
    condition     = startswith(var.health_check_path, "/")
    error_message = "Health path must start with /."
  }
}
variable "source_bundle" {
  type        = object({ bucket = string, key = string, version_label = string })
  description = "Existing S3 ZIP with Dockerrun.aws.json at its root, in the deployment region; use a unique immutable key and version."
}
variable "solution_stack_name" {
  type        = string
  description = "Exact AL2023 Docker platform version available in the deployment region."
  validation {
    condition     = can(regex("^64bit Amazon Linux 2023 .* running Docker$", var.solution_stack_name))
    error_message = "Use an Amazon Linux 2023 Docker solution stack."
  }
}
variable "vpc_id" {
  type        = string
  description = "VPC with routes to the registry, AWS APIs, PostgreSQL and OIDC."
  validation {
    condition     = can(regex("^vpc-[a-f0-9]+$", var.vpc_id))
    error_message = "Supply a VPC ID."
  }
}
variable "subnet_ids" {
  type        = list(string)
  description = "Public subnets with internet routing for this deployment recipe."
  validation {
    condition     = length(distinct(var.subnet_ids)) >= (var.environment_type == "LoadBalanced" ? 2 : 1) && alltrue([for id in var.subnet_ids : can(regex("^subnet-[a-f0-9]+$", id))])
    error_message = "Supply at least one subnet ID, or two distinct subnets in different Availability Zones for LoadBalanced."
  }
}
variable "instance_type" {
  type        = string
  description = "EC2 instance type compatible with the Docker image."
  default     = "t3.micro"
}
variable "environment_type" {
  type        = string
  description = "SingleInstance avoids a load balancer; LoadBalanced enables scaling."
  default     = "SingleInstance"
  validation {
    condition     = contains(["SingleInstance", "LoadBalanced"], var.environment_type)
    error_message = "Choose SingleInstance or LoadBalanced."
  }
}
variable "min_instances" {
  type        = number
  description = "Minimum instances; SingleInstance requires one."
  default     = 1
  validation {
    condition     = var.min_instances >= 1 && floor(var.min_instances) == var.min_instances
    error_message = "Minimum must be a positive integer."
  }
}
variable "max_instances" {
  type        = number
  description = "Maximum instances; SingleInstance requires one."
  default     = 1
  validation {
    condition     = var.max_instances >= var.min_instances && floor(var.max_instances) == var.max_instances && (var.environment_type != "SingleInstance" || (var.min_instances == 1 && var.max_instances == 1))
    error_message = "Maximum must be an integer >= minimum; SingleInstance requires min=max=1."
  }
}
variable "certificate_arn" {
  type        = string
  description = "Optional ACM certificate for LoadBalanced HTTPS; SingleInstance exposes HTTP only."
  default     = null
  validation {
    condition     = var.certificate_arn == null || var.environment_type == "LoadBalanced"
    error_message = "HTTPS certificate requires LoadBalanced."
  }
}
variable "container_port" {
  type        = number
  description = "Must match the port in the Docker source bundle."
  default     = 80
  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535 && floor(var.container_port) == var.container_port
    error_message = "Use an integer port from 1 to 65535."
  }
}
variable "secret_environment" {
  type        = map(string)
  description = "Environment name to full Secrets Manager or SSM ARN; Beanstalk resolves at instance bootstrap, outside Terraform state."
  default     = {}
  validation {
    condition     = alltrue([for arn in values(var.secret_environment) : can(regex("^arn:[^:]+:(secretsmanager|ssm):[^:]+:[0-9]{12}:(secret:|parameter/).+$", arn))])
    error_message = "Supply full Secrets Manager or SSM ARNs."
  }
}
variable "secret_kms_key_arns" {
  type        = set(string)
  description = "Customer-managed KMS keys required to decrypt referenced secrets."
  default     = []
}
variable "log_retention_days" {
  type        = number
  description = "Streamed CloudWatch log retention."
  default     = 7
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365], var.log_retention_days)
    error_message = "Choose a supported retention period."
  }
}
variable "aws_region" {
  type        = string
  description = "AWS deployment region."
  default     = "us-east-1"
}
variable "domain_name" {
  description = "Custom DNS name matching the ACM certificate; configure its CNAME to the Beanstalk cname output."
  type        = string
  default     = null
  validation {
    condition     = (var.domain_name == null) == (var.certificate_arn == null)
    error_message = "Supply domain_name and certificate_arn together."
  }
}
