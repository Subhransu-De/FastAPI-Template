variable "project_name" {
  description = "Lowercase service-name prefix; combined name must fit 63 characters."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9]*(-[a-z0-9]+)*$", var.project_name)) && length(var.project_name) <= 40
    error_message = "Use 1-40 lowercase letters, digits and single interior hyphens, starting with a letter."
  }
}
variable "environment" {
  description = "Environment suffix for the service name."
  type        = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9]*(-[a-z0-9]+)*$", var.environment)) && length(var.environment) <= 22
    error_message = "Use 1-22 lowercase letters, digits and single interior hyphens, starting with a letter."
  }
}
variable "image" {
  description = "Public registry image with a release tag or digest. Do not reuse mutable tags."
  type        = string
  validation {
    condition     = can(regex("^\\S+(:[^/:]+|@sha256:[a-f0-9]{64})$", var.image)) && !endswith(var.image, ":latest")
    error_message = "Supply a public image with an explicit release tag or digest, not latest."
  }
}
variable "power" {
  description = "Lightsail compute power per node."
  type        = string
  default     = "micro"
  validation {
    condition     = contains(["nano", "micro", "small", "medium", "large", "xlarge"], var.power)
    error_message = "Choose a supported Lightsail power."
  }
}
variable "scale" {
  description = "Number of container service nodes."
  type        = number
  default     = 1
  validation {
    condition     = var.scale >= 1 && var.scale <= 20 && floor(var.scale) == var.scale
    error_message = "Scale must be an integer from 1 to 20."
  }
}
variable "container_port" {
  description = "HTTP listener port; also sets the application's PORT environment variable."
  type        = number
  default     = 80
  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535 && floor(var.container_port) == var.container_port
    error_message = "Port must be an integer from 1 to 65535."
  }
}
variable "health_check_path" {
  description = "Unauthenticated HTTP health route."
  type        = string
  default     = "/health"
  validation {
    condition     = startswith(var.health_check_path, "/")
    error_message = "Health path must begin with /."
  }
}
variable "health_check" {
  description = "Lightsail health policy; only HTTP 200 is accepted."
  type = object({
    healthy_threshold   = optional(number, 2)
    unhealthy_threshold = optional(number, 2)
    interval_seconds    = optional(number, 10)
    timeout_seconds     = optional(number, 5)
  })
  default = {}
  validation {
    condition = alltrue([
      for value in [var.health_check.healthy_threshold, var.health_check.unhealthy_threshold] :
      value >= 2 && value <= 10 && floor(value) == value
    ]) && var.health_check.interval_seconds >= 5 && var.health_check.interval_seconds <= 300 && floor(var.health_check.interval_seconds) == var.health_check.interval_seconds && var.health_check.timeout_seconds >= 2 && var.health_check.timeout_seconds <= 60 && floor(var.health_check.timeout_seconds) == var.health_check.timeout_seconds && var.health_check.timeout_seconds < var.health_check.interval_seconds
    error_message = "Thresholds: integers 2-10; interval: 5-300; timeout: 2-60 and less than interval."
  }
}
variable "environment_variables" {
  description = "Literal app settings, stored in Terraform state. ARNs are not resolved as secrets. APP_HOST and PORT are managed by the module."
  type        = map(string)
  sensitive   = true
  default     = {}
}
variable "tags" {
  description = "Additional service tags."
  type        = map(string)
  default     = {}
}
variable "aws_region" {
  description = "AWS region supporting Lightsail Container Service."
  type        = string
  default     = "us-east-1"
}
