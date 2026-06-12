# variables.tf — Input variables for the ANT AWS stack.
#
# This file is the single source of truth for inputs that main.tf,
# backend.tf, and outputs.tf reference. Defaults are picked so that
# `terraform plan` works out-of-the-box for the production environment;
# override via terraform.tfvars (gitignored) or `-var` flags.
#
# Variable reference (alphabetical):
#   aws_region        — AWS region for all primary resources
#   cluster_name      — EKS cluster name (suffixed with environment)
#   domain_name       — Public DNS name (e.g. api.ant.example.com) for the ALB cert
#   environment       — Deployment environment tag (production / staging / dev)
#   image_tag         — Docker image tag to deploy
#   replication_region — AWS region for S3 cross-region replication
#   vpc_cidr          — VPC CIDR block

variable "aws_region" {
  description = "AWS region for primary resources (EKS, RDS, S3, etc.)"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster name (suffixed with -<environment>)"
  type        = string
  default     = "ant-cluster"
}

variable "domain_name" {
  description = "Public DNS name for the ALB TLS cert (e.g. api.ant.example.com). Leave empty to skip cert creation."
  type        = string
  default     = ""
}

variable "environment" {
  description = "Deployment environment (production, staging, dev)"
  type        = string
  default     = "production"
}

variable "image_tag" {
  description = "Docker image tag to deploy via the helm release"
  type        = string
  default     = "latest"
}

variable "replication_region" {
  description = "AWS region for S3 cross-region replication (DR)"
  type        = string
  default     = "us-west-2"
}

variable "vpc_cidr" {
  description = "VPC CIDR block (must be /16 or larger; 3 private + 3 public /24s are carved out of it)"
  type        = string
  default     = "10.0.0.0/16"
}
