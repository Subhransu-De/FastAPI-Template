variable "project_name" {
  type        = string
  description = "Resource name prefix."
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,29}$", var.project_name))
    error_message = "Use 2-30 lowercase letters, digits or hyphens, starting with a letter."
  }
}
variable "environment" {
  type        = string
  description = "Resource name suffix."
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,9}$", var.environment))
    error_message = "Use 2-10 lowercase letters, digits or hyphens, starting with a letter."
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
variable "image" {
  type        = string
  description = "Private ECR image containing Lambda Web Adapter; use a digest from the same region."
  validation {
    condition     = can(regex("^[0-9]{12}\\.dkr\\.ecr\\.[a-z0-9-]+\\.amazonaws\\.com(\\.cn)?/[^@]+@sha256:[a-f0-9]{64}$", var.image))
    error_message = "Use a private ECR image URI pinned by sha256 digest."
  }
}
variable "container_port" {
  type        = number
  description = "Unprivileged HTTP port used by the app and adapter."
  default     = 8080
  validation {
    condition     = var.container_port >= 1024 && var.container_port <= 65535 && floor(var.container_port) == var.container_port
    error_message = "Use an integer port from 1024 to 65535."
  }
}
variable "memory_size" {
  type        = number
  description = "Lambda memory in MB."
  default     = 512
  validation {
    condition     = var.memory_size >= 128 && var.memory_size <= 10240 && floor(var.memory_size) == var.memory_size
    error_message = "Memory must be an integer from 128 to 10240."
  }
}
variable "timeout" {
  type        = number
  description = "Maximum invocation duration in seconds."
  default     = 30
  validation {
    condition     = var.timeout >= 1 && var.timeout <= 900 && floor(var.timeout) == var.timeout
    error_message = "Timeout must be an integer from 1 to 900."
  }
}
variable "architecture" {
  type        = string
  description = "Must match the single-architecture image."
  default     = "x86_64"
  validation {
    condition     = contains(["x86_64", "arm64"], var.architecture)
    error_message = "Choose x86_64 or arm64."
  }
}
variable "authorization_type" {
  type        = string
  description = "AWS_IAM requires signed requests; NONE exposes the URL publicly and relies on app authentication."
  default     = "AWS_IAM"
  validation {
    condition     = contains(["AWS_IAM", "NONE"], var.authorization_type)
    error_message = "Choose AWS_IAM or NONE."
  }
}
variable "reserved_concurrency" {
  type        = number
  description = "Maximum parallel executions; -1 uses the account pool."
  default     = 2
  validation {
    condition     = var.reserved_concurrency >= -1 && floor(var.reserved_concurrency) == var.reserved_concurrency
    error_message = "Use -1 or a nonnegative integer."
  }
}
variable "log_retention_days" {
  type        = number
  description = "CloudWatch log retention."
  default     = 7
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365], var.log_retention_days)
    error_message = "Choose a supported retention period."
  }
}
variable "secrets_manager_environment" {
  type        = map(string)
  description = "Environment name to secret ARN; Terraform reads SecretString and stores it in state. Binary secrets are unsupported."
  default     = {}
}
variable "ssm_environment" {
  type        = map(string)
  description = "Environment name to SSM parameter name; Terraform decrypts values into state. The Terraform caller needs read and KMS permissions."
  default     = {}
}
variable "aws_region" {
  type        = string
  description = "AWS deployment region."
  default     = "us-east-1"
}
