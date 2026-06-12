# ANT Backend — GCP Terraform Stack

Provisions the GCP infrastructure for the ANT (AI Note Taker) backend and deploys
the Helm chart at `k8s/helm/backend/` (post Fix #25) into the resulting GKE cluster.

═══════════════════════════════════════════════════════════════════════════════
  OVERVIEW
═══════════════════════════════════════════════════════════════════════════════

Resources created by `terraform apply`:

  - **VPC** (custom mode, 1 subnet with secondary ranges for pods + services, Calico network policy, Cloud Router NAT via Private Service Connect for Cloud SQL)
  - **GKE cluster** (zonal, private nodes, Workload Identity, Shielded GKE Nodes, Container Threat Detection, REGULAR release channel, IPV4_IPV6 dual-stack)
  - **Node pool** (`backend-pool`, autoscaling 2-10, n2-standard-2, Shielded VMs, preemptible/spot for non-prod)
  - **Service account** (`ant-backend`) with roles for Cloud SQL client, Secret Manager accessor, Storage object viewer, Monitoring + Logging writer
  - **Artifact Registry** (CMK-encrypted via Cloud KMS, scanning via containerscanning.googleapis.com)
  - **Cloud SQL PostgreSQL 17** (private IP, REGIONAL HA for production, pgAudit + 12+ log flags, PITR for production, Query Insights)
  - **Secret Manager** secret for the DATABASE_URL
  - **Cloud Armor security policy** (WAF rules: XSS, SQLi, Log4j CVE-2021-44228; L7 DDoS defense for production)
  - **Helm release** deploying the backend chart into the `ant` namespace
  - **Required APIs** auto-enabled via `google_project_service` (container, compute, artifactregistry, etc.)

**State location:** GCS bucket `ant-tf-state` (see `backend.tf`).

═══════════════════════════════════════════════════════════════════════════════
  PREREQUISITES
═══════════════════════════════════════════════════════════════════════════════

  - **terraform** >= 1.7.0 (`brew tap hashicorp/tap && brew install hashicorp/tap/terraform`)
  - **gcloud** authenticated with permissions for Compute, GKE, Artifact Registry, Cloud SQL, KMS, Secret Manager
    (`gcloud auth application-default login` and `gcloud config set project <project>`)
  - **helm** >= 3 (`brew install helm`)
  - **kubectl** >= 1.29 (matches the GKE cluster version)
  - A **pre-created GCS bucket** for state (one-time per project; see `backend.tf`)
  - The **Helm chart dependencies vendored** (one-time):
        cd ../../k8s/helm/backend && helm dependency build

═══════════════════════════════════════════════════════════════════════════════
  INIT / PLAN / APPLY
═══════════════════════════════════════════════════════════════════════════════

  # 1. Copy the example tfvars and edit
  cp terraform.tfvars.example terraform.tfvars
  $EDITOR terraform.tfvars   # at minimum, set `project` to your GCP project

  # 2. Authenticate with Application Default Credentials
  gcloud auth application-default login
  gcloud config set project $(grep '^project' terraform.tfvars | awk -F'"' '{print $2}')

  # 3. Initialize (override the prod-default prefix for non-prod environments)
  terraform init

  # 4. Plan and review
  terraform plan -out=tfplan
  terraform show tfplan

  # 5. Apply
  terraform apply tfplan

  # 6. Configure kubectl (use the gke_cluster_name + gke_cluster_location outputs)
  gcloud container clusters get-credentials $(terraform output -raw gke_cluster_name) \
    --zone $(terraform output -raw gke_cluster_location) \
    --project $(terraform output -raw project_id)

═══════════════════════════════════════════════════════════════════════════════
  STATE
═══════════════════════════════════════════════════════════════════════════════

  - **Storage:** GCS (`ant-tf-state` bucket), versioning enabled for free history
  - **Locking:** GCS object generations (automatic with the GCS backend)
  - **Inspect:** `terraform state list` / `terraform state show <resource>`
  - **Move/rename:** `terraform state mv <src> <dst>` (after refactors)
  - **Import existing:** `terraform import <addr> <id>`

  ⚠ `terraform destroy` will NOT remove the GCS state bucket. Delete it
  manually (or via `gsutil rb`) if you really want to nuke the state.

  ⚠ The `prefix` is hardcoded to `terraform/state`. For non-prod
  environments, override it with `-backend-config="prefix=staging/terraform/state"`
  to keep the state files separate.

═══════════════════════════════════════════════════════════════════════════════
  TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

  **Bug fixed (Fix #24):** The 5 inline `variable` blocks in the old `main.tf`
  were moved to `variables.tf` (alphabetically sorted). One new var was added:
  `domain_name` (for the GKE ingress cert).

  **Bug fixed (Fix #24):** The `kubernetes` and `helm` providers were using
  `host = "https://${var.zone}/${google_container_cluster.main.id}"` — this
  is wrong because `.id` is the project-scoped resource ID, not the GKE
  control plane URL. Changed to `host = google_container_cluster.main.endpoint`
  (the actual control plane IP/hostname). The same fix was applied to both
  the kubernetes provider (L543) and the helm provider (L553).

  **Gotcha — Container Threat Detection:** `security_posture_config.mode = "ENABLED"`
  requires the GKE Security Posture API to be enabled (handled in
  `google_project_service.apis`) and may incur additional charges.

  **Gotcha — Spot/preemptible nodes:** For non-prod environments, the node pool
  uses `preemptible = true` and `spot = true`, which can be reclaimed at any
  time. Production defaults to on-demand (`var.environment == "production"`).

  **Gotcha — Cloud SQL private IP:** The Cloud SQL instance is reachable only
  from the VPC. The backend connects via the Cloud SQL Proxy sidecar (the
  `connection_name` is in the DATABASE_URL secret) — do not set a public IP
  for the instance.
