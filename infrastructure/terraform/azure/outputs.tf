# outputs.tf — Post-apply machine-readable outputs for the ANT Azure stack.
#
# Consume via `terraform output -json` or `terraform output <name>`.

# Output: aks_cluster_name — AKS cluster name (kubectl target)
output "aks_cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.main.name
}

# Output: aks_cluster_fqdn — AKS API server FQDN
output "aks_cluster_fqdn" {
  description = "AKS Kubernetes API server FQDN"
  value       = azurerm_kubernetes_cluster.main.fqdn
}

# Output: aks_kubeconfig_raw — raw kubeconfig (sensitive — for `kubectl --kubeconfig=-`)
output "aks_kubeconfig_raw" {
  description = "Raw kubeconfig YAML for kubectl (sensitive)"
  value       = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive   = true
}

# Output: resource_group_name — RG holding the stack
output "resource_group_name" {
  description = "Azure resource group name holding the entire stack"
  value       = azurerm_resource_group.main.name
}

# Output: vnet_id — VNet ID (for peering, additional subnets, or external resources)
output "vnet_id" {
  description = "Virtual network ID hosting the AKS cluster and Postgres"
  value       = azurerm_virtual_network.main.id
}

# Output: postgres_fqdn — PostgreSQL Flexible Server FQDN (DATABASE_URL host)
output "postgres_fqdn" {
  description = "PostgreSQL Flexible Server FQDN for DATABASE_URL"
  value       = azurerm_postgresql_flexible_server.main.fqdn
}

# Output: key_vault_uri — Key Vault URI (for storing secrets / retrieving the database URL secret)
output "key_vault_uri" {
  description = "Key Vault URI for secret storage and retrieval"
  value       = azurerm_key_vault.main.vault_uri
}

# Output: acr_login_server — Azure Container Registry login server (the ant-backend image is pushed here)
output "acr_login_server" {
  description = "Azure Container Registry login server (push/pull target for ant-backend image)"
  value       = azurerm_container_registry.main.login_server
}

# Output: web_app_default_hostname — App Service default hostname (azurewebsites.net)
output "web_app_default_hostname" {
  description = "App Service default hostname"
  value       = azurerm_linux_web_app.main.default_hostname
}
