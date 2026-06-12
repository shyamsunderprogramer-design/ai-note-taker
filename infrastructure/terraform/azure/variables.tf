# variables.tf — Input variables for the ANT Azure stack.
#
# This file is the single source of truth for inputs that main.tf,
# backend.tf, and outputs.tf reference. Defaults are picked so that
# `terraform plan` works out-of-the-box for the production environment;
# override via terraform.tfvars (gitignored) or `-var` flags.
#
# Variable reference (alphabetical):
#   azure_admin_group_id    — Azure AD group ID for AKS cluster admin
#   azure_admin_object_id   — Azure AD object ID for PostgreSQL AAD admin
#   domain_name             — Public DNS name (e.g. api.ant.example.com) for the App Service cert
#   environment             — Deployment environment tag (production / staging / dev)
#   image_tag               — Docker image tag to deploy
#   location                — Azure region

variable "azure_admin_group_id" {
  description = "Azure AD group ID for AKS cluster admin access (granted via Azure RBAC). Leave empty to skip RBAC setup."
  type        = string
  default     = ""
}

variable "azure_admin_object_id" {
  description = "Azure AD object ID for PostgreSQL AAD administrator. Falls back to the deploying principal's object_id if empty."
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Public DNS name for the App Service TLS cert (e.g. ant.example.com). Leave empty to skip custom domain."
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

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus"
}
