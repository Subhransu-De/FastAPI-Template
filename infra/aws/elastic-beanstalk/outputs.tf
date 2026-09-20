output "application_name" {
  description = "application name."
  value       = module.service.application_name
}
output "service_name" {
  description = "service name."
  value       = module.service.service_name
}
output "cname" {
  description = "cname."
  value       = module.service.cname
}
output "service_url" {
  description = "service url."
  value       = module.service.service_url
}
