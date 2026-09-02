output "cluster_name" {
  value = aws_eks_cluster.main.name
}
output "cluster_endpoint" {
  value     = aws_eks_cluster.main.endpoint
  sensitive = true
}
output "application_role_arn" {
  value = aws_iam_role.application.arn
}
output "runtime_secret_arn" {
  value = aws_secretsmanager_secret.runtime.arn
}
output "kms_key_arn" {
  value = aws_kms_key.platform.arn
}
output "postgres_endpoint" {
  value     = aws_db_instance.postgres.address
  sensitive = true
}
output "redis_endpoint" {
  value     = aws_elasticache_replication_group.redis.primary_endpoint_address
  sensitive = true
}
output "evidence_bucket" {
  value = aws_s3_bucket.evidence.bucket
}
output "waf_arn" {
  value = aws_wafv2_web_acl.edge.arn
}
output "api_ecr" {
  value = aws_ecr_repository.api.repository_url
}
output "frontend_ecr" {
  value = aws_ecr_repository.frontend.repository_url
}
