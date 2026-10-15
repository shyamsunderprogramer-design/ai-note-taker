# outputs.tf — Post-apply machine-readable outputs for the ANT AWS stack.
#
# Consume via `terraform output -json` or `terraform output <name>`.
# These are the values a follow-up CI step (or a developer running
# `aws eks update-kubeconfig` against a fresh cluster) needs.

# Output: cluster_name — EKS cluster name (full name, environment-suffixed)
output "cluster_name" {
  description = "EKS cluster name (suffixed with environment)"
  value       = module.eks.cluster_name
}

# Output: cluster_endpoint — EKS API server endpoint (kubectl target)
output "cluster_endpoint" {
  description = "EKS Kubernetes API server endpoint"
  value       = module.eks.cluster_endpoint
}

# Output: cluster_certificate_authority_data — EKS CA cert (base64, for kubeconfig)
output "cluster_certificate_authority_data" {
  description = "EKS cluster CA certificate (base64-encoded) for kubeconfig"
  value       = module.eks.cluster_certificate_authority_data
}

# Output: vpc_id — VPC ID (for peering, additional subnets, or external resources)
output "vpc_id" {
  description = "VPC ID hosting the EKS cluster and RDS"
  value       = module.vpc.vpc_id
}

# Output: vpc_cidr — echoes the input var; useful for downstream security groups
output "vpc_cidr" {
  description = "VPC CIDR block"
  value       = var.vpc_cidr
}

# Output: ecr_backend_repository_url — ECR URL for the backend image (the value that broke the orphan var)
output "ecr_backend_repository_url" {
  description = "ECR repository URL for the ant-backend image"
  value       = aws_ecr_repository.backend.repository_url
}

# Output: ecr_electron_repository_url — ECR URL for the Electron desktop image
output "ecr_electron_repository_url" {
  description = "ECR repository URL for the ant-electron image"
  value       = aws_ecr_repository.electron.repository_url
}

# Output: rds_endpoint — RDS Postgres endpoint (host:port)
output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint (host:port) for DATABASE_URL"
  value       = module.rds.db_instance_endpoint
}

# Output: s3_data_bucket — S3 bucket for application data (recordings, exports)
output "s3_data_bucket" {
  description = "S3 bucket name for application data uploads"
  value       = aws_s3_bucket.data.bucket
}

# Output: s3_logs_bucket — S3 bucket for S3 access logs (reused by replication log targets)
output "s3_logs_bucket" {
  description = "S3 bucket name for access logs"
  value       = aws_s3_bucket.logs.bucket
}

# Output: backend_irsa_role_arn — IAM role ARN for the backend ServiceAccount (IRSA)
output "backend_irsa_role_arn" {
  description = "IAM role ARN for the ant-backend ServiceAccount (IRSA) — used for Workload Identity"
  value       = module.backend_irsa.iam_role_arn
}
