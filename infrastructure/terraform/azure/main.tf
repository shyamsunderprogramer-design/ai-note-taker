# ANT Backend - Azure AKS Terraform Configuration
# Production-grade Kubernetes deployment on Azure AKS

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.12"
    }
  }

  backend "azurerm" {
    resource_group_name  = "ant-tf-state"
    storage_account_name = "anttfbstate"
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate"
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

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

# ─────────────────────────────────────────────────────────────────────────────
# Providers
# ─────────────────────────────────────────────────────────────────────────────
provider "azurerm" {
  features {
    key_vault {
      purge_soft_deleted_secrets_on_destroy = true
    }
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Resource Group
# ─────────────────────────────────────────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = "ant-${var.environment}-rg"
  location = var.location

  tags = {
    Environment = var.environment
    Project     = "ANT"
    ManagedBy   = "Terraform"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Azure Kubernetes Service
# ─────────────────────────────────────────────────────────────────────────────
resource "azurerm_kubernetes_cluster" "main" {
  name                = "ant-aks-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  dns_prefix          = "ant"
  sku_tier            = var.environment == "production" ? "Standard" : "Free"

  kubernetes_version  = "1.29"
 aks_clusters_min_version = "1.28"

  default_node_pool {
    name                = "default"
    node_count          = 3
    vm_size            = "Standard_DS2_v2"
    type               = "VirtualMachineScaleSets"
    availability_zones  = ["1", "2", "3"]
    enable_auto_scaling = true
    min_count          = 2
    max_count          = 10
    os_disk_size_gb    = 50
    os_disk_type       = "Managed"
    vnet_subnet_id     = azurerm_subnet.main.id

    node_labels = {
      "workload" = "default"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin     = "azure"
    network_policy     = "calico"
    load_balancer_sku  = "standard"
    outbound_type      = "loadBalancer"
    service_cidr       = "10.1.0.0/16"
    dns_service_ip     = "10.1.0.10"
  }

  azure_active_directory_role_based_access_control {
    managed                = true
    azure_rbac_enabled     = true
    admin_group_object_ids = [var.azure_admin_group_id]
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  }

  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  maintenance_window {
    allowed {
      day   = "Sunday"
      hours = [2, 3, 4]
    }
  }

  timeouts {
    create = "60m"
    update = "60m"
    delete = "60m"
  }
}

variable "azure_admin_group_id" {
  description = "Azure AD group ID for cluster admin access"
  type        = string
  default     = ""
}

# ─────────────────────────────────────────────────────────────────────────────
# Virtual Network & Subnets
# ─────────────────────────────────────────────────────────────────────────────
resource "azurerm_virtual_network" "main" {
  name                = "ant-vnet-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  address_space       = ["10.0.0.0/8"]

  tags = {
    Environment = var.environment
  }
}

resource "azurerm_subnet" "main" {
  name                 = "ant-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.0.0.0/16"]

  delegation {
    name = "aks-delegation"
    service_delegation {
      name    = "Microsoft.ContainerService/managedClusters"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_subnet" "aks_system" {
  name                 = "ant-aks-system"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.1.0.0/24"]

  enforce_private_link_endpoint_network_policies = true
}

# ─────────────────────────────────────────────────────────────────────────────
# Azure Container Registry
# ─────────────────────────────────────────────────────────────────────────────
resource "azurerm_container_registry" "main" {
  name                = "antacr${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  sku                 = "Premium"
  admin_enabled       = false

  georeplications = var.environment == "production" ? [
    {
      location = "westus2"
      tags     = {}
    }
  ] : []

  trust_policy {
    enabled = true
  }

  encryption {
    enabled = true
    key_vault_key_id = azurerm_key_vault_key.main.id
  }

  network_rule_set {
    default_action = "Allow"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Key Vault for Secrets
# ─────────────────────────────────────────────────────────────────────────────
resource "azurerm_key_vault" "main" {
  name                = "ant-kv-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "premium"

  soft_delete_retention_days = 7
  purge_protection_enabled   = var.environment == "production"

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    certificate_permissions = [
      "Get", "List", "Create", "Delete", "Update", "ManageContacts"
    ]
    key_permissions = [
      "Get", "List", "Create", "Delete", "Update", "Recover", "GetRotationPolicy"
    ]
    secret_permissions = [
      "Get", "List", "Set", "Delete", "Recover", "Purge"
    ]
  }

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = azurerm_kubernetes_cluster.main.kubelet_identity.0.object_id

    secret_permissions = ["Get", "List"]
  }
}

resource "azurerm_key_vault_key" "main" {
  name         = "ant-backend-key"
  key_vault_id = azurerm_key_vault.main.id
  key_type     = "RSA"
  key_size     = 2048
  key_opts     = ["decrypt", "encrypt", "sign", "unwrapKey", "wrapKey", "verify"]

  rotation_policy {
    automatic {
      time_before_expiry = "P30D"
    }
    notify {
      datetime_format = "RFC3339"
      time_before_expiry = "P7D"
    }
  }
}

data "azurerm_client_config" "current" {}

# ─────────────────────────────────────────────────────────────────────────────
# Log Analytics Workspace
# ─────────────────────────────────────────────────────────────────────────────
resource "azurerm_log_analytics_workspace" "main" {
  name                = "ant-log-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  retention_days      = 30
  sku                 = "PerGB2018"
}

# ─────────────────────────────────────────────────────────────────────────────
# Azure Database for PostgreSQL
# ─────────────────────────────────────────────────────────────────────────────
resource "azurerm_postgresql_flexible_server" "main" {
  name                = "ant-postgres-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  version            = "16"
  sku_name           = "GP_Standard_D4s_v3"
  tier              = "GeneralPurpose"
  storage_mb         = 32768
  backup_retention_days = 7
  geo_redundant_backup_enabled = var.environment == "production"
  delegated_subnet_id = azurerm_subnet.database.id
  private_dns_zone_id = azurerm_private_dns_zone.main.id

  administrator_login          = "antadmin"
  administrator_password      = random_password.postgres.result
  create_mode                = "Default"

  high_availability {
    mode                      = var.environment == "production" ? "ZoneRedundant" : "Disabled"
    standby_availability_zone = "2"
  }

  maintenance_window {
    day_of_week  = 0
    start_hour   = 2
    start_minute = 0
  }
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "antdb"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "utf8"
  collation = "en_US.utf8"
}

resource "random_password" "postgres" {
  length  = 32
  special = true
}

resource "azurerm_subnet" "database" {
  name                 = "ant-database-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.2.0.0/24"]

  delegation {
    name = "postgresql-delegation"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

resource "azurerm_private_dns_zone" "main" {
  name                = "ant.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.main.name

  depends_on = [azurerm_resource_group.main]
}

resource "azurerm_private_dns_zone_virtual_network_link" "main" {
  name                  = "ant-vnet-link"
  resource_group_name   = azurerm_resource_group.main.name
  private_dns_zone_name = azurerm_private_dns_zone.main.name
  virtual_network_id    = azurerm_virtual_network.main.id
}

# ─────────────────────────────────────────────────────────────────────────────
# Kubernetes Provider
# ─────────────────────────────────────────────────────────────────────────────
provider "kubernetes" {
  host                   = azurerm_kubernetes_cluster.main.kube_config.0.host
  client_certificate     = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.client_certificate)
  client_key             = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.client_key)
  cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.cluster_ca_certificate)
}

# ─────────────────────────────────────────────────────────────────────────────
# Helm Provider
# ─────────────────────────────────────────────────────────────────────────────
provider "helm" {
  kubernetes {
    host                   = azurerm_kubernetes_cluster.main.kube_config.0.host
    client_certificate     = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.client_certificate)
    client_key             = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.client_key)
    cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.cluster_ca_certificate)
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Helm Release - Backend
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
    value = "${azurerm_container_registry.main.login_server}/ant-backend"
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
    name  = "env[0].name"
    value = "DATABASE_URL"
  }

  set {
    name  = "env[0].valueFrom.secretKeyRef.name"
    value = "ant-secrets"
  }

  set {
    name  = "env[0].valueFrom.secretKeyRef.key"
    value = "database-url"
  }
}
