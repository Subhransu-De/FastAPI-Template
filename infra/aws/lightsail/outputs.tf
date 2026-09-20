output "service_name" {
  description = "Lightsail service name."
  value       = module.lightsail.service_name
}
output "service_url" {
  description = "Public HTTPS endpoint."
  value       = module.lightsail.service_url
}
