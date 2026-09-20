output "service_name" {
  description = "Lambda function name."
  value       = aws_lambda_function.this.function_name
}
output "service_url" {
  description = "HTTPS Function URL; AWS_IAM requires SigV4 signing."
  value       = aws_lambda_function_url.this.function_url
}
output "log_group_name" {
  description = "Function CloudWatch log group."
  value       = aws_cloudwatch_log_group.this.name
}
