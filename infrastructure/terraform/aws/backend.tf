# backend.tf — Terraform remote state configuration for the ANT AWS stack.
#
# The `backend "s3"` block was moved here from main.tf. It is a PARTIAL
# backend by design: hardcoded defaults are commented out, and the
# operator must supply values via `terraform init -backend-config`
# or by editing the placeholders below before the first `terraform init`.
#
# How to use:
#   1. Create the state bucket + DynamoDB lock table in the AWS console
#      (one-time per account). Example (paste into a separate scratch
#      config or use the AWS CLI):
#          aws s3api create-bucket --bucket ant-tf-state-prod \
#            --region us-east-1 --create-bucket-configuration LocationConstraint=us-east-1
#          aws s3api put-bucket-versioning --bucket ant-tf-state-prod \
#            --versioning-configuration Status=Enabled
#          aws dynamodb create-table --table-name ant-tf-locks \
#            --attribute-definitions AttributeName=LockID,AttributeType=S \
#            --key-schema AttributeName=LockID,KeyType=HASH \
#            --billing-mode PAY_PER_REQUEST
#   2. Either (a) edit the placeholders below, or (b) pass values via
#      -backend-config flags so the bucket/table names never land in git:
#          terraform init \
#            -backend-config="bucket=ant-tf-state-prod" \
#            -backend-config="key=aws/terraform.tfstate" \
#            -backend-config="region=us-east-1" \
#            -backend-config="dynamodb_table=ant-tf-locks"
#   3. `terraform init` to migrate from local state to S3 (if you had
#      state locally, terraform will offer to copy it).
#
# Why S3 + DynamoDB: S3 stores the state file (with versioning enabled
# for free history); DynamoDB provides the lock so two `terraform apply`
# runs cannot trample each other.

terraform {
  backend "s3" {
    # TODO: set bucket, key, region, dynamodb_table before first init.
    # Example:
    #   bucket         = "ant-tf-state-prod"
    #   key            = "aws/terraform.tfstate"
    #   region         = "us-east-1"
    #   dynamodb_table = "ant-tf-locks"
    #   encrypt        = true
    encrypt = true
  }
}
