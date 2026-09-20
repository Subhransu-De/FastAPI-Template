output "bucket_name" {
  description = "State bucket for deployment backends."
  value       = aws_s3_bucket.state.id
}
