output "application_name" {
  description = "Beanstalk application name."
  value       = aws_elastic_beanstalk_application.this.name
}
output "service_name" {
  description = "Beanstalk environment name."
  value       = aws_elastic_beanstalk_environment.this.name
}
output "cname" {
  description = "Beanstalk environment DNS name."
  value       = aws_elastic_beanstalk_environment.this.cname
}
output "service_url" {
  description = "Environment endpoint; configure certificate DNS and OIDC redirects before production use."
  value       = var.certificate_arn == null ? "http://${aws_elastic_beanstalk_environment.this.cname}" : "https://${var.domain_name}"
}
