provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      var.additional_tags,
      {
        Environment = var.environment
        ManagedBy   = "terraform"
        Project     = var.project_name
      },
    )
  }
}
