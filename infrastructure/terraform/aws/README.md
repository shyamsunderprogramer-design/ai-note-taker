# ANT Backend — AWS Terraform Stack

Provisions the AWS infrastructure for the ANT (AI Note Taker) backend and deploys
the Helm chart at `k8s/helm/backend/` (post Fix #25) into the resulting EKS cluster.

═══════════════════════════════════════════════════════════════════════════════
  OVERVIEW
═══════════════════════════════════════════════════════════════════════════════

Resources created by `terraform apply`:

  - **VPC** (3 AZs, 3 private + 3 public /24 subnets, NAT gateways)
  - **EKS cluster** (managed node group + Fargate profile, IRSA for AWS LB Controller, Cluster Autoscaler, and the backend)
  - **RDS PostgreSQL 16** (encrypted, KMS-managed key, multi-AZ for production)
  - **ECR repositories** for `ant-backend` and `ant-electron` (scan-on-push)
  - **S3 buckets** for application data + access logs, with cross-region replication to `replication_region`
  - **KMS keys** for S3, RDS, and EBS encryption (key rotation enabled)
  - **Helm releases** for AWS Load Balancer Controller, Cluster Autoscaler, and the backend chart
  - **IAM policies** for the backend (Secrets Manager + S3 RW scoped to `ant-data-<env>/*`)

**State location:** S3 bucket `ant-tf-state-<env>` with DynamoDB-backed locking (see `backend.tf`).

═══════════════════════════════════════════════════════════════════════════════
  PREREQUISITES
═══════════════════════════════════════════════════════════════════════════════

  - **terraform** >= 1.7.0 (`brew tap hashicorp/tap && brew install hashicorp/tap/terraform`)
  - **aws CLI** authenticated with permissions to create VPC, EKS, IAM, RDS, S3, KMS
    (`aws configure` or `aws sso login`)
  - **helm** >= 3 (`brew install helm`)
  - **kubectl** >= 1.29 (matches the EKS cluster version)
  - A **pre-created S3 bucket** for state + a **DynamoDB table** for locks
    (one-time per account; see `backend.tf` for the exact commands)
  - The **Helm chart dependencies vendored** (one-time):
        cd ../../k8s/helm/backend && helm dependency build

═══════════════════════════════════════════════════════════════════════════════
  INIT / PLAN / APPLY
═══════════════════════════════════════════════════════════════════════════════

  # 1. Copy the example tfvars and edit
  cp terraform.tfvars.example terraform.tfvars
  $EDITOR terraform.tfvars

  # 2. Initialize (pass backend config inline so secrets stay out of git)
  terraform init \
    -backend-config="bucket=ant-tf-state-prod" \
    -backend-config="key=aws/terraform.tfstate" \
    -backend-config="region=us-east-1" \
    -backend-config="dynamodb_table=ant-tf-locks"

  # 3. Plan and review
  terraform plan -out=tfplan
  terraform show tfplan

  # 4. Apply
  terraform apply tfplan

  # 5. Configure kubectl (use the cluster_name output)
  aws eks update-kubeconfig --region us-east-1 --name $(terraform output -raw cluster_name)

═══════════════════════════════════════════════════════════════════════════════
  STATE
═══════════════════════════════════════════════════════════════════════════════

  - **Storage:** S3 (`ant-tf-state-<env>`), versioning enabled for free history
  - **Locking:** DynamoDB (`ant-tf-locks`); required to prevent concurrent applies
  - **Inspect:** `terraform state list` / `terraform state show <resource>`
  - **Move/rename:** `terraform state mv <src> <dst>` (after refactors)
  - **Import existing:** `terraform import <addr> <id>` (e.g. an existing RDS instance)

  ⚠ `terraform destroy` will NOT remove the S3 state bucket or DynamoDB lock
  table — they are external to this config. Delete them manually if you really
  want to nuke the state.

═══════════════════════════════════════════════════════════════════════════════
  TROUBLESHOOTING
═══════════════════════════════════════════════════════════════════════════════

  **Bug fixed (Fix #24):** `var.ecr_repository_url` was used in the helm_release
  (L347) but declared nowhere. Replaced with `aws_ecr_repository.backend.repository_url`
  so the chart deploys against the ECR resource defined in this file.

  **Bug fixed (Fix #24):** The 6 inline `variable` blocks in the old `main.tf`
  were moved to `variables.tf` (alphabetically sorted). One new var was added:
  `domain_name` (for the ALB cert).

  **Gotcha — EKS auth:** The `aws-auth` ConfigMap is managed outside this stack
  (by the EKS module's `access_entries` or a separate `kubectl apply`). If you
  cannot `kubectl` after apply, check the cluster's access entries in the console.

  **Gotcha — RDS in private subnets:** RDS lives in the private subnets and has
  no public endpoint. To reach it from your laptop, run a bastion in a public
  subnet or use SSM Session Manager port-forwarding.

  **Gotcha — KMS costs:** Each KMS key costs ~$1/month. The 3 keys (S3, RDS,
  EBS) are intentional, but you can drop the replication-region key if you
  disable cross-region replication.
