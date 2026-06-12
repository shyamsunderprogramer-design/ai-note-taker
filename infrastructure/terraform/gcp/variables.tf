# variables.tf — Input variables for the ANT GCP stack.
#
# This file is the single source of truth for inputs that main.tf,
# backend.tf, and outputs.tf reference. Defaults are picked so that
# `terraform plan` works out-of-the-box for the production environment;
# override via terraform.tfvars (gitignored) or `-var` flags.
#
# Variable reference (alphabetical):
#   domain_name    — Public DNS name (e.g. api.ant.example.com) for the GKE ingress cert
#   environment    — Deployment environment tag (production / staging / dev)
#   image_tag      — Docker image tag to deploy
#   project        — GCP Project ID
#   region         — GCP region
#   zone           — GCP zone (for zonal cluster resources)

variable "domain_name" {
  description = "Public DNS name for the GKE ingress TLS cert (e.g. api.ant.example.com). Leave empty to skip cert creation."
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

variable "project" {
  description = "GCP Project ID"
  type        = string
  default     = "your-project-id"
}

variable "region" {
  description = "GCP region (for regional resources like Artifact Registry, Cloud SQL)"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone (for zonal cluster + node pool)"
  type        = string
  default     = "us-central1-a"
}
