output "service_name" {
  description = "service name."
  value       = module.service.service_name
}
output "service_url" {
  description = "service url."
  value       = module.service.service_url
}
output "log_group_name" {
  description = "log group name."
  value       = module.service.log_group_name
}
