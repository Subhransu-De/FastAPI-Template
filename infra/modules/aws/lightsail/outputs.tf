output "service_name" {
  description = "Lightsail service name."
  value       = aws_lightsail_container_service.this.name
}
output "service_url" {
  description = "Public HTTPS endpoint, available after deployment."
  value       = aws_lightsail_container_service.this.url
  depends_on  = [aws_lightsail_container_service_deployment_version.this]
}
