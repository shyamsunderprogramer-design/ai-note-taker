# backend.tf — Terraform remote state configuration for the ANT GCP stack.
#
# The `backend "gcs"` block was moved here from main.tf. It is a PARTIAL
# backend by design: hardcoded bucket + prefix match the production state
# store the team provisioned by hand.
#
# How to use:
#   1. Create the state bucket in GCP (one-time per project):
#          gsutil mb -p <project> -l us-central1 gs://ant-tf-state/
#          gsutil versioning set on gs://ant-tf-state/
#   2. Either (a) edit the placeholders below, or (b) pass overrides via
#      -backend-config so they never land in git:
#          terraform init \
#            -backend-config="bucket=ant-tf-state-prod" \
#            -backend-config="prefix=gcp/terraform/state"
#   3. `terraform init` to migrate from local state to GCS (if you had state
#      locally, terraform will offer to copy it).
#
# Authentication: the GCS backend uses the same `google` provider
# credentials, which default to `GOOGLE_APPLICATION_CREDENTIALS` env var or
# Application Default Credentials (`gcloud auth application-default login`).
#
# Why GCS: GCS object versioning gives free state history, and the GCS
# backend uses GCS generation numbers as a lock — no separate lock service
# to set up.

terraform {
  backend "gcs" {
    # Defaults match the production state store. Override per-env via
    # -backend-config (see above). The `prefix` separates the GCP
    # state files from any other stacks that share the same bucket.
    bucket = "ant-tf-state"
    prefix = "terraform/state"
  }
}
