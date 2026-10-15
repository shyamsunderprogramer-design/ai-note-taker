# outputs.tf — Post-apply machine-readable outputs for the ANT GCP stack.
#
# Consume via `terraform output -json` or `terraform output <name>`.

# Output: gke_cluster_name — GKE cluster name (kubectl target)
output "gke_cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.main.name
}

# Output: gke_cluster_endpoint — GKE control plane endpoint (use with `gcloud container clusters get-credentials`)
output "gke_cluster_endpoint" {
  description = "GKE Kubernetes API server endpoint"
  value       = google_container_cluster.main.endpoint
}

# Output: gke_cluster_location — GKE cluster location (zone for zonal, region for regional)
output "gke_cluster_location" {
  description = "GKE cluster location (zone for zonal clusters)"
  value       = google_container_cluster.main.location
}

# Output: project_id — echoes the input var
output "project_id" {
  description = "GCP project ID"
  value       = var.project
}

# Output: network_name — VPC network name
output "network_name" {
  description = "VPC network name hosting the GKE cluster"
  value       = google_compute_network.main.name
}

# Output: subnet_name — VPC subnet name
output "subnet_name" {
  description = "VPC subnet name (carries the pods + services secondary ranges)"
  value       = google_compute_subnetwork.main.name
}

# Output: cloudsql_connection_name — Cloud SQL connection name (for Cloud SQL Proxy sidecar)
output "cloudsql_connection_name" {
  description = "Cloud SQL instance connection name (project:region:instance) — used by the Cloud SQL Proxy sidecar"
  value       = google_sql_database_instance.main.connection_name
}

# Output: cloudsql_private_ip — Cloud SQL private IP (for direct VPC connections)
output "cloudsql_private_ip" {
  description = "Cloud SQL private IP address (reachable from the GKE nodes' VPC)"
  value       = google_sql_database_instance.main.private_ip_address
}

# Output: service_account_email — backend service account (for Workload Identity binding)
output "service_account_email" {
  description = "GCP service account email for the ant-backend (bind via Workload Identity)"
  value       = google_service_account.backend.email
}
