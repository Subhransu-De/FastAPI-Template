variable "aws_region" {
  description = "Region for the state bucket."
  type        = string
  default     = "us-east-1"
}
variable "access_log_bucket" {
  description = "Optional existing S3 access-log destination in the same account and region, with log-delivery permissions. Null disables access logging."
  type        = string
  default     = null
}
variable "bucket_name_prefix" {
  description = "Bucket name prefix; the AWS account ID, region and -an suffix are appended automatically."
  type        = string
  default     = "tfstate"
  validation {
    condition     = can(regex("^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", var.bucket_name_prefix)) && length(var.bucket_name_prefix) + length(var.aws_region) + 17 <= 63 && !anytrue([for prefix in ["xn--", "sthree-", "amzn-s3-demo-"] : startswith(var.bucket_name_prefix, prefix)])
    error_message = "Use lowercase letters, digits and interior hyphens, avoid AWS-reserved prefixes, and keep the complete bucket name within 63 characters."
  }
}
