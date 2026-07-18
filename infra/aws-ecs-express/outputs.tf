output "cluster_name" {
  description = "ECS cluster that owns the Express Mode service."
  value       = aws_ecs_cluster.app.name
}

output "endpoint_url" {
  description = "Managed HTTPS endpoint. This is known after the service is created."
  value       = try(aws_ecs_express_gateway_service.app.ingress_paths[0].endpoint, null)
}

output "log_group_name" {
  description = "CloudWatch log group receiving application logs."
  value       = aws_cloudwatch_log_group.app.name
}

output "service_arn" {
  description = "ARN identifying the ECS Express Mode service."
  value       = aws_ecs_express_gateway_service.app.service_arn
}

output "service_name" {
  description = "Name of the ECS Express Mode service."
  value       = aws_ecs_express_gateway_service.app.service_name
}

output "task_role_arn" {
  description = "Least-privilege IAM role assumed by application tasks."
  value       = aws_iam_role.task.arn
}
