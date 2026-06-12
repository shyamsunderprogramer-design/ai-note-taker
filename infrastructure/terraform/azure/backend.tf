# backend.tf — Terraform remote state configuration for the ANT Azure stack.
#
# The `backend "azurerm"` block was moved here from main.tf. It is a PARTIAL
# backend by design: the hardcoded values match the production state store
# the team provisioned by hand. For non-prod environments, override via
# -backend-config flags.
#
# How to use:
#   1. Create the state storage account + container in the Azure portal
#      (one-time per subscription). The hardcoded values below assume:
#          resource_group_name  = "ant-tf-state"
#          storage_account_name = "anttfbstate"
#          container_name       = "tfstate"
#      The storage account must have a blob container named "tfstate".
#   2. Either (a) edit the values below, or (b) pass overrides via
#      `terraform init -backend-config=` so they never land in git:
#          terraform init \
#            -backend-config="resource_group_name=ant-tf-state-dev" \
#            -backend-config="storage_account_name=anttfstatedev" \
#            -backend-config="container_name=tfstate" \
#            -backend-config="key=dev.terraform.tfstate"
#   3. `terraform init` to migrate from local state to Azure Blob (if you
#      had state locally, terraform will offer to copy it).
#
# Why azurerm: native Azure Storage leases provide state locking out of the
# box (no DynamoDB equivalent to set up).

terraform {
  backend "azurerm" {
    # Defaults match the production state store. Override per-env via
    # -backend-config (see above). The `key` value is intentionally
    # `prod.terraform.tfstate` — change it to a different prefix for
    # staging/dev so the workspaces don't collide.
    resource_group_name  = "ant-tf-state"
    storage_account_name = "anttfbstate"
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate"
  }
}
