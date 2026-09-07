# FitnessPulse — AWS Setup Log

This document records manually-created AWS resources during initial setup.
These will be codified in Terraform in Milestone 6; until then, this is the
source of truth for what exists and why.

## Account
- AWS account created (personal), root user secured with MFA + zero-spend budget alert.
- IAM admin user created for daily work (console + CLI), MFA enabled.
- Root user is not used for day-to-day work.

## Region
- `us-east-1` — chosen for broadest Databricks support, more AZs, and lowest cost
  relative to other regions.

## S3
- Single bucket: `fitnesspulse-lakehouse-<account-id>`
- Structure: one bucket, prefix-separated medallion zones (not separate buckets
  per layer) — simpler IAM/Terraform surface area for a project this size.

raw/
bronze/
silver/
gold/
quarantine/

- Versioning: enabled (protects against pipeline runs corrupting/overwriting data).
- Public access: fully blocked.
- Encryption: SSE-S3 (default, Amazon-managed keys).

## Not yet done
- IAM policy scoped to Terraform's actual needs (currently using AdministratorAccess
  on the IAM admin user as a temporary, deliberate simplification — see Milestone 6).
- Databricks workspace + S3 integration (Milestone 2, next step).
- Secrets management (Databricks secret scopes / AWS Secrets Manager).