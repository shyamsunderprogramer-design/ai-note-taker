# ANT Backend - GCP GKE Terraform Configuration
# Production-grade Kubernetes deployment on Google Cloud GKE

terraform {
  required_version = ">= 1.7.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.25"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.25"
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

  backend "gcs" {
    bucket = "ant-tf-state"
    prefix = "terraform/state"
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

variable "project" {
  description = "GCP Project ID"
  type        = string
  default     = "your-project-id"
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

# ─────────────────────────────────────────────────────────────────────────────
# Enable APIs
# ─────────────────────────────────────────────────────────────────────────────
resource "google_project_service" "apis" {
  for_each = toset([
    "container.googleapis.com",
    "compute.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudsql.googleapis.com",
    "sqladmin.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "networkmanagement.googleapis.com",
    "certificatemanager.googleapis.com",
  ])

  project = var.project
  service = each.value

  disable_dependent_services = false
  disable_on_destroy         = false
}

# ─────────────────────────────────────────────────────────────────────────────
# VPC Network
# ─────────────────────────────────────────────────────────────────────────────
resource "google_compute_network" "main" {
  name                    = "ant-vpc-${var.environment}"
  auto_create_subnetworks = false
  description             = "ANT VPC Network"
}

resource "google_compute_subnetwork" "main" {
  name          = "ant-subnet-${var.environment}"
  network       = google_compute_network.main.id
  ip_cidr_range = "10.0.0.0/24"
  region        = var.region

  secondary_ip_range = [
    {
      range_name    = "pods"
      ip_cidr_range = "10.4.0.0/16"
    },
    {
      range_name    = "services"
      ip_cidr_range = "10.5.0.0/20"
    }
  ]
}

resource "google_compute_firewall" "allow_internal" {
  name    = "ant-allow-internal"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  source_ranges = ["10.0.0.0/8"]
}

# ─────────────────────────────────────────────────────────────────────────────
# Private Service Connect for Cloud SQL
# ─────────────────────────────────────────────────────────────────────────────
resource "google_compute_global_address" "private_ip" {
  name          = "ant-private-ip"
  purpose       = "VPC_PEERING"
  prefix_length = 16
  network       = google_compute_network.main.id
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.main.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip.name]

  depends_on = [google_project_service.apis]
}

# ─────────────────────────────────────────────────────────────────────────────
# GKE Cluster
# ─────────────────────────────────────────────────────────────────────────────
resource "google_container_cluster" "main" {
  name                       = "ant-gke-${var.environment}"
  location                   = var.zone
  remove_default_node_pool   = true
  initial_node_count         = 1
  network                    = google_compute_network.main.name
  subnetwork                 = google_compute_subnetwork.main.name

  enable_intranode_visibility = true
  enable_shielded_nodes       = true

  security_posture_config {
    mode = "ENABLED"
  }

  workload_identity_config {
    workload_pool = "${var.project}.svc.id.goog"
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
    stack_type                   = "IPV4_IPV6"
    dual_stack_type              = "IPV4_IPV6"
  }

  release_channel {
    channel = "REGULAR"
  }

  node_config {
    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }

  timeouts {
    create = "60m"
    update = "60m"
    delete = "60m"
  }

  depends_on = [
    google_project_service.apis,
    google_service_networking_connection.private_vpc_connection
  ]
}

# ─────────────────────────────────────────────────────────────────────────────
# Node Pools
# ─────────────────────────────────────────────────────────────────────────────
resource "google_container_node_pool" "backend" {
  name       = "backend-pool"
  location   = var.zone
  cluster    = google_container_cluster.main.name
  node_count = 3

  node_config {
    machine_type    = "n2-standard-2"
    service_account = google_service_account.backend.email

    preemptible  = var.environment != "production"
    spot         = var.environment != "production"

    disk_size_gb = 50
    disk_type    = "pd-ssd"

    labels = {
      workload = "backend"
    }

    workload_metadata_config {
      mode = "GKE_METADATA"
    }

    shielded_instance_config {
      enable_secure_boot          = true
      enable_integrity_monitoring = true
    }
  }

  autoscaling {
    min_node_count = 2
    max_node_count = 10
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Service Accounts
# ─────────────────────────────────────────────────────────────────────────────
resource "google_service_account" "backend" {
  account_id   = "ant-backend"
  display_name = "ANT Backend Service Account"
}

resource "google_project_iam_member" "backend" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/storage.objectViewer",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter",
  ])

  project = var.project
  role    = each.value
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Artifact Registry
# ─────────────────────────────────────────────────────────────────────────────
resource "google_artifact_registry_repository" "main" {
  location      = var.region
  name          = "ant-docker"
  repository_id = "ant-docker"
  description   = "ANT Docker repository"
  format        = "DOCKER"

  cleanup_policy_dry_run = false

  mode = "STANDARD_REPOSITORY"
}

# ─────────────────────────────────────────────────────────────────────────────
# Cloud SQL (PostgreSQL)
# ─────────────────────────────────────────────────────────────────────────────
resource "google_sql_database_instance" "main" {
  name             = "ant-postgres-${var.environment}"
  database_version = "POSTGRES_16"
  region          = var.region

  deletion_protection  = var.environment == "production"
  enable_binary_logging = var.environment == "production"

  settings {
    tier              = var.environment == "production" ? "db-n1-standard-2" : "db-f1-micro"
    availability_type = var.environment == "production" ? "REGIONAL" : "ZONAL"
    disk_type        = "PD_SSD"
    disk_size        = 100
    disk_autoresize  = true

    ip_configuration {
      ipv4_enabled    = false
      private_network = google_compute_network.main.id
      require_ssl     = true
    }

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = var.environment == "production"
      backup_retention_settings {
        retained_backups = 7
        retention_unit   = "COUNT"
      }
    }

    maintenance_window {
      day          = 0
      hour         = 4
      update_track = "stable"
    }

    insights_config {
      query_insights_enabled  = true
      query_string_length      = 1024
      record_application_tags  = true
      record_client_address    = false
    }
  }

  depends_on = [google_service_networking_connection.private_vpc_connection]
}

resource "google_sql_database" "main" {
  name     = "antdb"
  instance = google_sql_database_instance.main.name
}

resource "random_password" "postgres" {
  length = 32
}

resource "google_sql_user" "main" {
  name     = "antadmin"
  instance = google_sql_database_instance.main.name
  password = random_password.postgres.result
}

# ─────────────────────────────────────────────────────────────────────────────
# Secret Manager
# ─────────────────────────────────────────────────────────────────────────────
resource "google_secret_manager_secret" "database_url" {
  secret_id = "ant-database-url"

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
  }
}

resource "google_secret_manager_secret_version" "database_url" {
  secret = google_secret_manager_secret.database_url.id

  secret_data = "postgresql://antadmin:${random_password.postgres.result}@/${google_sql_database.main.name}?host=/cloudsql/${var.project}:${var.region}:ant-postgres-${var.environment}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Cloud Armor (WAF)
# ─────────────────────────────────────────────────────────────────────────────
resource "google_compute_security_policy" "main" {
  name        = "ant-security-policy"
  description = "ANT Security Policy"

  adaptive_protection_config {
    layer7_ddos_defense_config {
      enable = var.environment == "production"
      rule_visibility = "STANDARD"
    }
  }

  rule {
    action   = "deny(403)"
    priority = 1000
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('xss-v33-stable')"
      }
    }
    description = "Block XSS"
  }

  rule {
    action   = "deny(403)"
    priority = 1001
    match {
      expr {
        expression = "evaluatePreconfiguredExpr('sqli-v33-stable')"
      }
    }
    description = "Block SQL Injection"
  }
}

# ─────────────────────────────────────────────────────────────────────────────
# Kubernetes Provider
# ─────────────────────────────────────────────────────────────────────────────
provider "kubernetes" {
  host                   = "https://${var.zone}/${google_container_cluster.main.id}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(google_container_cluster.main.master_auth[0].cluster_ca_certificate)
}

# ─────────────────────────────────────────────────────────────────────────────
# Helm Provider
# ─────────────────────────────────────────────────────────────────────────────
provider "helm" {
  kubernetes {
    host                   = "https://${var.zone}/${google_container_cluster.main.id}"
    token                  = data.google_client_config.default.access_token
    cluster_ca_certificate = base64decode(google_container_cluster.main.master_auth[0].cluster_ca_certificate)
  }
}

data "google_client_config" "default" {}

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
    value = "${var.region}-docker.pkg.dev/${var.project}/${google_artifact_registry_repository.main.name}/ant-backend"
  }

  set {
    name  = "replicaCount"
    value = var.environment == "production" ? 3 : 2
  }

  set {
    name  = "serviceAccount.create"
    value = true
  }

  set {
    name  = "serviceAccount.annotationsiam\\.gke\\.io/gcp-service-account"
    value = google_service_account.backend.email
  }
}
