# ==============================================================================
# EarCodeX — AWS Cloud Infrastructure as Code (Terraform)
# Enterprise Insurance Administration & Reconciliation System Architecture
# Practice: N.White Systems (Principal Technology Architect & AI Systems Engineer)
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Platform    = "EarCodeX"
      Sector      = "Insurance & Financial Services"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Practice    = "N.White Systems"
    }
  }
}

variable "aws_region" {
  type    = string
  default = "af-south-1" # Primary AWS region
}

variable "environment" {
  type    = string
  default = "production"
}

# 1. KMS Key for Insurance Document & Ledger Encryption
resource "aws_kms_key" "earcodex_key" {
  description             = "KMS Key for EarCodeX insurance document encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  tags = {
    Name = "earcodex-kms-key"
  }
}

# 2. S3 Encrypted Claims Document Vault
resource "aws_s3_bucket" "claims_vault" {
  bucket        = "nwhite-earcodex-claims-vault-\${var.environment}"
  force_destroy = false
}

resource "aws_s3_bucket_versioning" "claims_vault_versioning" {
  bucket = aws_s3_bucket.claims_vault.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "claims_vault_encryption" {
  bucket = aws_s3_bucket.claims_vault.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.earcodex_key.arn
      sse_algorithm     = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "claims_vault_block" {
  bucket = aws_s3_bucket.claims_vault.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# 3. DynamoDB State Table for Claims Workflow & Idempotency
resource "aws_dynamodb_table" "claims_state" {
  name         = "earcodex-claims-state-\${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "claim_id"
  range_key    = "policy_number"

  attribute {
    name = "claim_id"
    type = "S"
  }

  attribute {
    name = "policy_number"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.earcodex_key.arn
  }

  tags = {
    Name = "earcodex-claims-state"
  }
}

# 4. CloudWatch Log Group for Regulatory Audit & Tracing
resource "aws_cloudwatch_log_group" "audit_logs" {
  name              = "/aws/earcodex/audit-trail-\${var.environment}"
  retention_in_days = 365 # 1-year compliance retention
}

output "claims_vault_bucket" {
  value = aws_s3_bucket.claims_vault.id
}

output "kms_key_arn" {
  value = aws_kms_key.earcodex_key.arn
}

output "dynamodb_table_arn" {
  value = aws_dynamodb_table.claims_state.arn
}
