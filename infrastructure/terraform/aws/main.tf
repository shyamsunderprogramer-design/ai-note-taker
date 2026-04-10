# ANT Backend - AWS EKS Terraform Configuration
# Production-grade Kubernetes deployment on AWS EKS

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    aws        = { source  = "hashicorp/aws", version = "~> 5.30" }
    kubernetes = { source  = "hashicorp/kubernetes", version = "~> 2.25" }
    helm       = { source  = "hashicorp/helm", version = "~> 2.12" }
  }

  backend "s3" {
    encrypt = true
    # Configure via backend config or environment variables
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Variables
# ─────────────────────────────────────────────────────────────────────────────
variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "image_tag" {
  description = "Docker image tag to deploy"
  type        = string
  default     = "latest"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "ant-cluster"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
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

  enable_nat_gateway     = true
  single_nat_gateway     = false
  enable_dns_hostnames   = true
  enable_dns_support     = true

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

  cluster_name    = "${var.cluster_name}-${var.environment}"
  cluster_version = "1.29"
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
  name = "${var-cluster_name}-cluster-autoscaler"

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
      }
    ]
  })
}

# ─────────────────────────────────────────────────────────────────────────────
# ANT Backend Helm Release
# ─────────────────────────────────────────────────────────────────────────────
resource "helm_release" "ant_backend" {
  name       = "ant-backend"
  repository = "file://../../k8s/helm/backend"
  chart      = "ant-backend"
  namespace  = "ant"
  create_namespace = true

  values = [
    file("../../k8s/helm/backend/values-${var.environment}.yaml")
  ]

  set {
    name  = "image.tag"
    value = var.image_tag
  }

  set {
    name  = "image.repository"
    value = "${var.ecr_repository_url}/ant-backend"
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
  family              = "postgres16"
  major_engine_version = "16"
  instance_class       = "db.t3.medium"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_encrypted     = true
  storage_type          = "gp3"

  db_name  = "antdb"
  username = "antadmin"
  port     = 5432

  vpc_security_group_ids = [aws_security_group.rds.id]

  maintenance_window      = "mon:02:00-mon:04:00"
  backup_window          = "03:00-05:00"
  backup_retention_period = 7
  multi_az               = var.environment == "production"

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
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# ECR Repositories
# ─────────────────────────────────────────────────────────────────────────────
resource "aws_ecr_repository" "backend" {
  name                 = "ant-backend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration = {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "electron" {
  name                 = "ant-electron"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration = {
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

resource "aws_s3_bucket_server_side_encryption" "data" {
  bucket = aws_s3_bucket.data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

data "aws_caller_identity" "current" {}
