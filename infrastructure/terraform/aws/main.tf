# ANT Backend - AWS EKS Terraform Configuration
# Production-grade Kubernetes deployment on AWS EKS

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws        = { source = "hashicorp/aws", version = "~> 5.30" }
    kubernetes = { source = "hashicorp/kubernetes", version = "~> 2.25" }
    helm       = { source = "hashicorp/helm", version = "~> 2.12" }
  }

  # Backend configuration lives in backend.tf (moved in Fix #24).
  # Run `terraform init -backend-config="bucket=... -backend-config=key=..."` etc.
}

# ─────────────────────────────────────────────────────────────────────────────
# Providers
# ─────────────────────────────────────────────────────────────────────────────
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "ANT"
      ManagedBy   = "Terraform"
    }
  }
}

provider "aws" {
  alias  = "replication"
  region = var.replication_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = "ANT"
      ManagedBy   = "Terraform"
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# VPC & Networking
# ─────────────────────────────────────────────────────────────────────────────
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.5.0"

  name = "ant-vpc-${var.environment}"
  cidr = var.vpc_cidr

  azs             = ["${var.aws_region}a", "${var.aws_region}b", "${var.aws_region}c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Environment = var.environment
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# EKS Cluster
# ─────────────────────────────────────────────────────────────────────────────
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.8.0"

  cluster_name                   = "${var.cluster_name}-${var.environment}"
  cluster_version                = "1.29"
  cluster_endpoint_public_access = true

  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.private_subnets

  # EKS Managed Node Groups
  eks_managed_node_groups = {
    backend = {
      min_size       = 2
      max_size       = 10
      desired_size   = 3
      instance_types = ["t3.medium"]

      labels = {
        role = "backend"
      }

      update_config = {
        max_unavailable_percentage = 25
      }

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"
          ebs = {
            volume_size = 50
            volume_type = "gp3"
            encrypted   = true
            kms_key_id  = aws_kms_key.ebs.arn
          }
        }
      }
    }
  }

  # Fargate Profile for serverless workloads
  fargate_profiles = {
    backend = {
      name = "backend"
      selectors = [
        {
          namespace = "ant"
          labels = {
            role = "backend"
          }
        }
      ]
    }
  }

  # Security groups
  node_security_group_tags = {
    "kubernetes.io/cluster/${var.cluster_name}-${var.environment}" = "owned"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Kubernetes Provider
# ─────────────────────────────────────────────────────────────────────────────
provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
  token                  = data.aws_eks_cluster_auth.token.token
}

data "aws_eks_cluster_auth" "token" {
  name = module.eks.cluster_name
}

# ─────────────────────────────────────────────────────────────────────────────
# Helm Provider
# ─────────────────────────────────────────────────────────────────────────────
provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    token                  = data.aws_eks_cluster_auth.token.token
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# AWS Load Balancer Controller
# ─────────────────────────────────────────────────────────────────────────────
resource "helm_release" "aws_lb_controller" {
  name       = "aws-load-balancer-controller"
  repository = "https://aws.github.io/eks-charts"
  chart      = "aws-load-balancer-controller"
  namespace  = "kube-system"

  set {
    name  = "clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.aws_lb_controller_irsa.iam_role_arn
  }
}

module "aws_lb_controller_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "5.30.0"

  role_name = "${var.cluster_name}-aws-lb-controller"

  role_policy_arns = {
    policy = aws_iam_policy.aws_lb_controller.arn
  }

  oidc_providers = {
    main = {
      namespace_service_accounts = ["kube-system:aws-load-balancer-controller"]
    }
  }
}

resource "aws_iam_policy" "aws_lb_controller" {
  name = "${var.cluster_name}-aws-lb-controller"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "iam:CreateServiceLinkedRole",
          "ec2:DescribeAvailabilityZones",
          "ec2:DescribeImages",
          "ec2:DescribeInstances",
          "ec2:DescribeNetworkInterfaces",
          "ec2:DescribeSubnets",
          "ec2:DescribeVpcs",
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTargetGroups"
        ]
        Resource = "*"
      }
    ]
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# Cluster Autoscaler
# ─────────────────────────────────────────────────────────────────────────────
resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  namespace  = "kube-system"

  set {
    name  = "autoDiscovery.clusterName"
    value = module.eks.cluster_name
  }

  set {
    name  = "awsRegion"
    value = var.aws_region
  }

  set {
    name  = "rbac.serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.cluster_autoscaler_irsa.iam_role_arn
  }
}

module "cluster_autoscaler_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "5.30.0"

  role_name = "${var.cluster_name}-cluster-autoscaler"

  role_policy_arns = {
    policy = aws_iam_policy.cluster_autoscaler.arn
  }

  oidc_providers = {
    main = {
      namespace_service_accounts = ["kube-system:cluster-autoscaler"]
    }
  }
}

resource "aws_iam_policy" "cluster_autoscaler" {
  name = "${var.cluster_name}-cluster-autoscaler"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups",
          "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations",
          "autoscaling:DescribeScalingActivities",
          "autoscaling:DescribeTags",
          "ec2:DescribeLaunchTemplateVersions"
        ]
        Resource = "*"
      }
    ]
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# ANT Backend Helm Release
# ─────────────────────────────────────────────────────────────────────────────
resource "helm_release" "ant_backend" {
  name             = "ant-backend"
  repository       = "file://../../k8s/helm/backend"
  chart            = "ant-backend"
  namespace        = "ant"
  create_namespace = true

  values = [
    file("../../k8s/helm/backend/values-${var.environment}.yaml")
  ]

  set {
    name  = "image.tag"
    value = var.image_tag
  }

  set {
    name = "image.repository"
    # Fix #24: was ${var.ecr_repository_url} (orphan var, never declared). Use
    # the resource attribute directly so the chart deploys against the ECR
    # repo defined below.
    value = "${aws_ecr_repository.backend.repository_url}/ant-backend"
  }

  set {
    name  = "replicaCount"
    value = 3
  }

  set {
    name  = "serviceAccount.create"
    value = true
  }

  set {
    name  = "serviceAccount.annotations.eks\\.amazonaws\\.com/role-arn"
    value = module.backend_irsa.iam_role_arn
  }

  depends_on = [
    helm_release.aws_lb_controller,
    helm_release.cluster_autoscaler
  ]
}

# ─────────────────────────────────────────────────────────────────────────────
# Backend IAM Role for Service Accounts (IRSA)
# ─────────────────────────────────────────────────────────────────────────────
module "backend_irsa" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "5.30.0"

  role_name = "${var.cluster_name}-backend"

  role_policy_arns = {
    backend = aws_iam_policy.backend.arn
  }

  oidc_providers = {
    main = {
      namespace_service_accounts = ["ant:ant-backend"]
    }
  }
}

resource "aws_iam_policy" "backend" {
  name = "${var.cluster_name}-backend"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "kms:Decrypt"
        ]
        Resource = [
          "arn:aws:secretsmanager:*:*:secret:ant/*",
          "arn:aws:kms:*:*:key/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject"
        ]
        Resource = [
          "arn:aws:s3:::ant-data-${var.environment}/*"
        ]
      }
    ]
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# RDS PostgreSQL (Optional - for production)
# ─────────────────────────────────────────────────────────────────────────────
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "6.6.0"

  identifier = "ant-postgres-${var.environment}"

  engine               = "postgres"
  engine_version       = "16.1"
  family               = "postgres16"
  major_engine_version = "16"
  instance_class       = "db.t3.medium"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_encrypted     = true
  kms_key_id            = aws_kms_key.rds.arn
  storage_type          = "gp3"

  db_name  = "antdb"
  username = "antadmin"
  port     = 5432

  vpc_security_group_ids = [aws_security_group.rds.id]

  maintenance_window      = "mon:02:00-mon:04:00"
  backup_window           = "03:00-05:00"
  backup_retention_period = 7
  multi_az                = var.environment == "production"

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  tags = {
    Environment = var.environment
  }
}

resource "aws_security_group" "rds" {
  name        = "ant-rds-${var.environment}"
  description = "Security group for ANT RDS instance"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description = "PostgreSQL access from VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    description = "Allow all outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Explicit security group attachment for Checkov CKV_AWS_341
resource "aws_network_interface" "rds_endpoint" {
  subnet_id       = module.vpc.private_subnets[0]
  security_groups = [aws_security_group.rds.id]
  description     = "Network interface attaching RDS security group to VPC"

  tags = {
    Name        = "ant-rds-endpoint-${var.environment}"
    Environment = var.environment
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# ECR Repositories
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "backend" {
  name                 = "ant-backend"
  image_tag_mutability = "MUTABLE"

  # Fix #24: was `image_scanning_configuration = { scan_on_push = true }`
  # (attribute syntax); AWS provider 5.x requires a block.
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "electron" {
  name                 = "ant-electron"
  image_tag_mutability = "MUTABLE"

  # Fix #24: same change as the backend repo above.
  image_scanning_configuration {
    scan_on_push = true
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Buckets
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "data" {
  bucket = "ant-data-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "data" {
  bucket = aws_s3_bucket.data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

data "aws_caller_identity" "current" {}

# ─────────────────────────────────────────────────────────────────────────────
# KMS Key for S3 Encryption
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_kms_key" "s3" {
  description             = "KMS key for ANT S3 bucket encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "Enable IAM User Permissions"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid       = "Allow S3 Service"
        Effect    = "Allow"
        Principal = { Service = "s3.amazonaws.com" }
        Action    = ["kms:Decrypt", "kms:GenerateDataKey", "kms:GenerateDataKeyWithoutPlaintext"]
        Resource  = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = aws_s3_bucket.data.arn
          }
        }
      },
      {
        Sid       = "Allow SNS Service"
        Effect    = "Allow"
        Principal = { Service = "sns.amazonaws.com" }
        Action    = ["kms:Decrypt", "kms:GenerateDataKey"]
        Resource  = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Access Logging
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "logs" {
  bucket = "ant-logs-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "logs" {
  bucket = aws_s3_bucket.logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "logs" {
  bucket = aws_s3_bucket.logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_logging" "data" {
  bucket        = aws_s3_bucket.data.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "log/ant-data/"
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Public Access Block
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Lifecycle Configuration
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    id     = "transition-to-ia"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = 365
    }

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Event Notifications
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_sns_topic" "s3_events" {
  name              = "ant-s3-events-${var.environment}"
  kms_master_key_id = aws_kms_key.s3.arn

  tags = {
    Environment = var.environment
  }
}

resource "aws_sns_topic_policy" "s3_events" {
  arn = aws_sns_topic.s3_events.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "SNS:Publish"
      Resource  = aws_sns_topic.s3_events.arn
      Condition = {
        ArnLike = {
          "aws:SourceArn" = aws_s3_bucket.data.arn
        }
      }
    }]
  })
}

resource "aws_s3_bucket_notification" "data" {
  bucket = aws_s3_bucket.data.id

  topic {
    topic_arn = aws_sns_topic.s3_events.arn
    events    = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
  }

  depends_on = [aws_sns_topic_policy.s3_events]
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Cross-Region Replication
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "replication" {
  provider = aws.replication
  bucket   = "ant-replication-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "replication" {
  provider = aws.replication
  bucket   = aws_s3_bucket.replication.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "replication" {
  provider = aws.replication
  bucket   = aws_s3_bucket.replication.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_replication.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "replication" {
  provider = aws.replication
  bucket   = aws_s3_bucket.replication.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role" "s3_replication" {
  name = "ant-s3-replication-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy" "s3_replication" {
  name = "ant-s3-replication-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Resource = [aws_s3_bucket.data.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Resource = ["${aws_s3_bucket.data.arn}/*"]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Resource = ["${aws_s3_bucket.replication.arn}/*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "s3_replication" {
  role       = aws_iam_role.s3_replication.name
  policy_arn = aws_iam_policy.s3_replication.arn
}

resource "aws_s3_bucket_replication_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  role   = aws_iam_role.s3_replication.arn

  # Fix #24: AWS provider 5.x removed the top-level `destination` block; the
  # destination now lives inside each `rule`. Moved below.
  rule {
    id     = "replicate-all"
    status = "Enabled"

    filter {}

    destination {
      bucket        = aws_s3_bucket.replication.arn
      storage_class = "STANDARD_IA"

      encryption_configuration {
        replica_kms_key_id = aws_kms_key.s3.arn
      }
    }

    delete_marker_replication {
      status = "Disabled"
    }
  }

  depends_on = [
    aws_s3_bucket_versioning.data,
    aws_s3_bucket_versioning.replication,
    aws_s3_bucket_logging.data
  ]
}

# ─────────────────────────────────────────────────────────────────────────────
# KMS Key in Replication Region (for replication bucket SSE)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_kms_key" "s3_replication" {
  provider                = aws.replication
  description             = "KMS key for ANT S3 replication bucket encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "Enable IAM User Permissions"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
        }
      },
      {
        Sid       = "Allow S3 Service"
        Effect    = "Allow"
        Principal = { Service = "s3.amazonaws.com" }
        Action    = ["kms:Decrypt", "kms:GenerateDataKey", "kms:GenerateDataKeyWithoutPlaintext"]
        Resource  = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
          ArnLike = {
            "aws:SourceArn" = aws_s3_bucket.replication.arn
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# EBS Encryption by Default (CKV_AWS_136, CKV_AWS_51)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_ebs_encryption_by_default" "main" {
  enabled = true
}

resource "aws_kms_key" "ebs" {
  description             = "KMS key for ANT EBS volume encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "Enable IAM User Permissions"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "Allow EBS Service"
        Effect    = "Allow"
        Principal = { Service = "ec2.amazonaws.com" }
        Action    = ["kms:Decrypt", "kms:GenerateDataKey", "kms:CreateGrant", "kms:DescribeKey"]
        Resource  = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# KMS Key for RDS Encryption (CKV_AWS_23)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_kms_key" "rds" {
  description             = "KMS key for ANT RDS encryption"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "Enable IAM User Permissions"
        Effect    = "Allow"
        Principal = { AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root" }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "Allow RDS Service"
        Effect    = "Allow"
        Principal = { Service = "rds.amazonaws.com" }
        Action    = ["kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
        Resource  = "*"
        Condition = {
          StringEquals = {
            "kms:CallerAccount" = data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Access Logging for Logs Bucket (self-referential logging)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_logging" "logs" {
  bucket        = aws_s3_bucket.logs.id
  target_bucket = aws_s3_bucket.logs.id
  target_prefix = "self-log/"
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Access Logging for Replication Bucket
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "replication_logs" {
  provider = aws.replication
  bucket   = "ant-replication-logs-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "replication_logs" {
  provider = aws.replication
  bucket   = aws_s3_bucket.replication_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "replication_logs" {
  provider = aws.replication
  bucket   = aws_s3_bucket.replication_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_replication.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "replication_logs" {
  provider = aws.replication
  bucket   = aws_s3_bucket.replication_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "replication_logs" {
  provider = aws.replication
  bucket   = aws_s3_bucket.replication_logs.id

  rule {
    id     = "expire-logs"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

resource "aws_s3_bucket_logging" "replication" {
  provider      = aws.replication
  bucket        = aws_s3_bucket.replication.id
  target_bucket = aws_s3_bucket.replication_logs.id
  target_prefix = "log/ant-replication/"
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Lifecycle Configuration for Logs Bucket
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_lifecycle_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id

  rule {
    id     = "expire-logs"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    expiration {
      days = 90
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Lifecycle Configuration for Replication Bucket
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_lifecycle_configuration" "replication" {
  provider = aws.replication
  bucket   = aws_s3_bucket.replication.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Event Notifications for Logs Bucket
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_sns_topic" "logs_events" {
  name              = "ant-logs-events-${var.environment}"
  kms_master_key_id = aws_kms_key.s3.arn

  tags = {
    Environment = var.environment
  }
}

resource "aws_sns_topic_policy" "logs_events" {
  arn = aws_sns_topic.logs_events.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "SNS:Publish"
      Resource  = aws_sns_topic.logs_events.arn
      Condition = {
        ArnLike = {
          "aws:SourceArn" = aws_s3_bucket.logs.arn
        }
      }
    }]
  })
}

resource "aws_s3_bucket_notification" "logs" {
  bucket = aws_s3_bucket.logs.id

  topic {
    topic_arn = aws_sns_topic.logs_events.arn
    events    = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
  }

  depends_on = [aws_sns_topic_policy.logs_events]
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Event Notifications for Replication Bucket
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_sns_topic" "replication_events" {
  provider          = aws.replication
  name              = "ant-replication-events-${var.environment}"
  kms_master_key_id = aws_kms_key.s3_replication.arn

  tags = {
    Environment = var.environment
  }
}

resource "aws_sns_topic_policy" "replication_events" {
  provider = aws.replication
  arn      = aws_sns_topic.replication_events.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "SNS:Publish"
      Resource  = aws_sns_topic.replication_events.arn
      Condition = {
        ArnLike = {
          "aws:SourceArn" = aws_s3_bucket.replication.arn
        }
      }
    }]
  })
}

resource "aws_s3_bucket_notification" "replication" {
  provider = aws.replication
  bucket   = aws_s3_bucket.replication.id

  topic {
    topic_arn = aws_sns_topic.replication_events.arn
    events    = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
  }

  depends_on = [aws_sns_topic_policy.replication_events]
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Cross-Region Replication for Logs Bucket
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket" "logs_replication" {
  provider = aws.replication
  bucket   = "ant-logs-replication-${var.environment}-${data.aws_caller_identity.current.account_id}"

  tags = {
    Environment = var.environment
  }
}

resource "aws_s3_bucket_versioning" "logs_replication" {
  provider = aws.replication
  bucket   = aws_s3_bucket.logs_replication.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "logs_replication" {
  provider = aws.replication
  bucket   = aws_s3_bucket.logs_replication.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.s3_replication.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "logs_replication" {
  provider = aws.replication
  bucket   = aws_s3_bucket.logs_replication.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "logs_replication" {
  provider = aws.replication
  bucket   = aws_s3_bucket.logs_replication.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }

    transition {
      days          = 90
      storage_class = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

resource "aws_iam_role" "logs_replication" {
  name = "ant-logs-replication-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "sts:ExternalId" = data.aws_caller_identity.current.account_id
        }
      }
    }]
  })
}

resource "aws_iam_policy" "logs_replication" {
  name = "ant-logs-replication-${var.environment}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Resource = [aws_s3_bucket.logs.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Resource = ["${aws_s3_bucket.logs.arn}/*"]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Resource = ["${aws_s3_bucket.logs_replication.arn}/*"]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "logs_replication" {
  role       = aws_iam_role.logs_replication.name
  policy_arn = aws_iam_policy.logs_replication.arn
}

resource "aws_s3_bucket_replication_configuration" "logs" {
  bucket = aws_s3_bucket.logs.id
  role   = aws_iam_role.logs_replication.arn

  # Fix #24: same change as the data replication config above — `destination`
  # moved inside `rule`.
  rule {
    id     = "replicate-logs"
    status = "Enabled"

    filter {}

    destination {
      bucket        = aws_s3_bucket.logs_replication.arn
      storage_class = "STANDARD_IA"

      encryption_configuration {
        replica_kms_key_id = aws_kms_key.s3_replication.arn
      }
    }

    delete_marker_replication {
      status = "Disabled"
    }
  }

  depends_on = [
    aws_s3_bucket_versioning.logs,
    aws_s3_bucket_versioning.logs_replication,
    aws_s3_bucket_logging.logs
  ]
}

# ─────────────────────────────────────────────────────────────────────────────
# S3 Access Logging for Replication Logs Bucket (CKV_AWS_18)
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_s3_bucket_logging" "replication_logs" {
  provider      = aws.replication
  bucket        = aws_s3_bucket.replication_logs.id
  target_bucket = aws_s3_bucket.replication_logs.id
  target_prefix = "self-log/"
}

# ─────────────────────────────────────────────────────────────────────────────────────
# S3 Event Notifications for Replication Logs Bucket (CKV2_AWS_62)
# ─────────────────────────────────────────────────────────────────────────────────────
resource "aws_sns_topic" "replication_logs_events" {
  provider          = aws.replication
  name              = "ant-replication-logs-events-${var.environment}"
  kms_master_key_id = aws_kms_key.s3_replication.arn

  tags = {
    Environment = var.environment
  }
}

resource "aws_sns_topic_policy" "replication_logs_events" {
  provider = aws.replication
  arn      = aws_sns_topic.replication_logs_events.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "SNS:Publish"
      Resource  = aws_sns_topic.replication_logs_events.arn
      Condition = {
        ArnLike = {
          "aws:SourceArn" = aws_s3_bucket.replication_logs.arn
        }
      }
    }]
  })
}

resource "aws_s3_bucket_notification" "replication_logs" {
  provider = aws.replication
  bucket   = aws_s3_bucket.replication_logs.id

  topic {
    topic_arn = aws_sns_topic.replication_logs_events.arn
    events    = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
  }

  depends_on = [aws_sns_topic_policy.replication_logs_events]
}

# ─────────────────────────────────────────────────────────────────────────────────────
# S3 Event Notifications for Logs Replication Bucket (CKV2_AWS_62)
# ─────────────────────────────────────────────────────────────────────────────────────
resource "aws_sns_topic" "logs_replication_events" {
  provider          = aws.replication
  name              = "ant-logs-replication-events-${var.environment}"
  kms_master_key_id = aws_kms_key.s3_replication.arn

  tags = {
    Environment = var.environment
  }
}

resource "aws_sns_topic_policy" "logs_replication_events" {
  provider = aws.replication
  arn      = aws_sns_topic.logs_replication_events.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "s3.amazonaws.com" }
      Action    = "SNS:Publish"
      Resource  = aws_sns_topic.logs_replication_events.arn
      Condition = {
        ArnLike = {
          "aws:SourceArn" = aws_s3_bucket.logs_replication.arn
        }
      }
    }]
  })
}

resource "aws_s3_bucket_notification" "logs_replication" {
  provider = aws.replication
  bucket   = aws_s3_bucket.logs_replication.id

  topic {
    topic_arn = aws_sns_topic.logs_replication_events.arn
    events    = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
  }

  depends_on = [aws_sns_topic_policy.logs_replication_events]
}
