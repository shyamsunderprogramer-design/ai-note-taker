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
  description = "Azure AD group ID for AKS cluster admin access (granted via Azure RBAC). Leave empty to use only the deploying principal; managed Azure RBAC remains enabled."
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

variable "kubernetes_version" {
  description = "Optional supported AKS version. Null uses the service default for new clusters; existing clusters require a reviewed upgrade path."
  type        = string
  default     = null
  validation {
    condition     = var.kubernetes_version == null ? true : can(regex("^[0-9]+\\.[0-9]+(\\.[0-9]+)?$", var.kubernetes_version))
    error_message = "Use a supported AKS minor or patch version, such as 1.35 or 1.35.7."
  }
}

variable "aks_login_mode" {
  description = "kubelogin identity matching the Terraform principal: Azure CLI, service principal, workload identity or managed identity."
  type        = string
  default     = "azurecli"
  validation {
    condition     = contains(["azurecli", "spn", "workloadidentity", "msi"], var.aks_login_mode)
    error_message = "Supported login modes are azurecli, spn, workloadidentity and msi."
  }
}
