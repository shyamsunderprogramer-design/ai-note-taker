# ANT Backend — Azure Terraform Stack

Provisions the Azure infrastructure for the ANT (AI Note Taker) backend and deploys
the Helm chart at `k8s/helm/backend/` (post Fix #25) into the resulting AKS cluster.

═══════════════════════════════════════════════════════════════════════════════
  OVERVIEW
═══════════════════════════════════════════════════════════════════════════════

Resources created by `terraform apply`:

  - **Resource group** (`ant-<env>-rg`) holding all stack resources
  - **AKS cluster** (Standard SKU for production, Calico network policy, Azure AD RBAC, OMS agent, Key Vault secrets provider)
  - **Virtual network** with 3 subnets (main, aks-system, database) + NSG (deny-all-inbound with allow rules for internal traffic + Postgres)
  - **Azure Container Registry** (Premium SKU, geo-replicated for production, CMK-encrypted via Key Vault)
  - **Key Vault** (premium SKU, soft-delete + purge protection, private endpoint via Private Link)
  - **PostgreSQL Flexible Server 16** (ZoneRedundant HA for production, TLS 1.2 enforced, pgAudit enabled, customer-managed keys, private endpoint)
  - **Storage accounts** for data, logs, backups (GRS for data/backups, LRS for logs, all CMK-encrypted, public access denied, TLS 1.2)
  - **App Service** (Linux, P1v2, HTTPS-only, client cert required, TLS 1.2)
  - **Helm release** deploying the backend chart into the `ant` namespace
  - **Diagnostic settings** + **Microsoft Defender for PostgreSQL** (subscription-level)

**State location:** Azure Blob Storage in `ant-tf-state` RG → `anttfbstate` SA → `tfstate` container (see `backend.tf`).

═══════════════════════════════════════════════════════════════════════════════
  PREREQUISITES
═══════════════════════════════════════════════════════════════════════════════

  - **terraform** >= 1.7.0 (`brew tap hashicorp/tap && brew install hashicorp/tap/terraform`)
  - **Azure CLI** authenticated (`az login` or `az account set -s <subscription>`)
  - **helm** >= 3 (`brew install helm`)
  - **kubectl** within one minor version of the selected AKS version
  - **kubelogin** available on PATH; Kubernetes/Helm providers use Entra tokens, not local client certificates
  - A **pre-created state storage account + container** (one-time per subscription; see `backend.tf`)
  - The **Helm chart dependencies vendored** (one-time):
        cd ../../k8s/helm/backend && helm dependency build

═══════════════════════════════════════════════════════════════════════════════
  INIT / PLAN / APPLY
═══════════════════════════════════════════════════════════════════════════════

  # 1. Copy the example tfvars and edit
  cp terraform.tfvars.example terraform.tfvars
  $EDITOR terraform.tfvars

  # 2. Initialize (override the prod-default key for non-prod environments)
  terraform init

  # 3. Plan and review
  terraform plan -out=tfplan
  terraform show tfplan

  # 4. Apply
  terraform apply tfplan

  # 5. Configure kubectl using Entra authentication
  az aks get-credentials --resource-group "$(terraform output -raw resource_group_name)" --name "$(terraform output -raw aks_cluster_name)"
  kubelogin convert-kubeconfig -l azurecli
  kubectl get nodes

═══════════════════════════════════════════════════════════════════════════════
  STATE
═══════════════════════════════════════════════════════════════════════════════

  - **Storage:** Azure Blob (`anttfbstate` SA → `tfstate` container)
  - **Locking:** Azure Storage native leases (automatic with the azurerm backend)
  - **Inspect:** `terraform state list` / `terraform state show <resource>`
  - **Move/rename:** `terraform state mv <src> <dst>` (after refactors)
  - **Import existing:** `terraform import <addr> <id>`

  ⚠ `terraform destroy` will NOT remove the state storage account, container, or
  RG. Delete them manually if you really want to nuke the state.

  ⚠ The backend's `key` is hardcoded to `prod.terraform.tfstate`. For staging
  or dev, override it with `-backend-config="key=staging.terraform.tfstate"`
  to keep the environments in separate state files.

═══════════════════════════════════════════════════════════════════════════════
  TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

  **Bug fixed (Fix #24):** The 5 `variable` blocks (3 at the top of the old
  `main.tf` + 2 out-of-order ones — `azure_admin_group_id` was declared at
  L155 after being used at L130, `azure_admin_object_id` was declared mid-file
  at L807) were consolidated into `variables.tf` (alphabetically sorted).
  One new var was added: `domain_name` (for the App Service custom domain).

  **Gotcha — Key Vault access policies:** The Key Vault access policy for the
  AKS kubelet identity is set during `azurerm_kubernetes_cluster.main`
  creation. If you delete and recreate the AKS cluster, the kubelet identity
  will be different and you'll need to re-run `terraform apply` (or manually
  re-add the policy) to grant the new identity access to the vault.

  **Gotcha — PostgreSQL private endpoint:** Postgres has `public_network_access_enabled = false`
  and is reachable only via the private endpoint in `aks_system` subnet. To
  connect from your laptop, run a bastion in the VNet or use `az postgres flexible-server connect`.

  **Gotcha — Microsoft Defender:** The `azurerm_security_center_subscription_pricing.postgresql_defender`
  resource is a **subscription-level** setting. If you run this stack in a
  shared subscription, you may want to remove it (or scope it to a dedicated
  RG) to avoid affecting other workloads.

## AKS authentication and version selection

Local AKS accounts are disabled. Terraform's Kubernetes and Helm providers use
`kubelogin get-token`; `aks_login_mode` defaults to `azurecli`. Authenticate Azure
CLI as the same principal used by the AzureRM provider. For automation, select
`spn`, `workloadidentity` or `msi` and configure the matching kubelogin identity;
`--use-azurerm-env-vars` supports ARM_* environment names without putting secrets
in command arguments. See [kubelogin](https://azure.github.io/kubelogin/cli/get-token.html).
The deploying principal receives cluster-scoped AKS RBAC administrator access
for installation. An optional nonempty `azure_admin_group_id` adds group access;
empty values no longer produce an invalid group ID.

Azure role assignments can take time to propagate. If first-time Helm access
returns Forbidden, verify the identity and wait for RBAC propagation before
retrying. Terraform validation does not prove live identity access.

`kubernetes_version` defaults to null instead of the retired hardcoded 1.29.
New clusters use AKS's service default; pin a supported minor or patch when your
release process requires one. Existing clusters need a reviewed supported
upgrade path. Kubernetes service addresses use 172.20.0.0/16 to avoid overlap
with this template's 10.0.0.0/8 VNet. Changing an existing cluster's service range
can require replacement: review a saved plan and migration before applying.
No deployed cluster was changed when validating these templates.

## Subscription logging migration

Subscription diagnostic settings replace the retired Monitor log-profile API.
A Terraform `removed` block forgets the old resource without destroying it.
The eight supported subscription activity categories are sent to storage and
Log Analytics; storage lifecycle management preserves the previous 365-day
base-blob retention policy for the activity-log container. Review existing
subscription diagnostics before applying to avoid duplicate collection/cost.
Legacy storage HTTPS and private-endpoint policy attributes use their supported
AzureRM 3.x replacements.
