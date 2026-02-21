# Terraform Testing Guide

This document describes how to test the GCP Artifact Registry Terraform configuration.

## Overview

The Terraform configuration includes automated validation tests that verify:
- Configuration syntax and format
- Input variable validation (project_id, region, artifact_registry_writers)
- Resource plan generation
- IAM format validation

## Prerequisites

- Terraform >= 1.0 installed
- GCP project ID: `marufeuille-linebot`
- `gcloud auth application-default login` completed for authentication
- jq (for plan JSON parsing)

## Running Tests

### Full Test Suite

Run all validation tests:

```bash
cd terraform
bash tests/terraform_validate_test.sh
```

This script will execute:
1. Terraform format validation
2. Terraform initialization
3. Configuration validation
4. Plan generation for dev environment
5. Resource plan verification
6. Input validation tests (invalid project_id, region, IAM format)

### Individual Tests

#### Test 1: Format Check

```bash
cd terraform
terraform fmt -check -recursive .
```

To automatically fix formatting issues:
```bash
terraform fmt -recursive .
```

#### Test 2: Initialize Backend

```bash
cd terraform
terraform init
```

This initializes the GCS backend at `marufeuille-linebot-terraform-backend`.

#### Test 3: Validate Configuration

```bash
cd terraform
terraform validate
```

Checks for syntax errors and configuration consistency.

#### Test 4: Plan Resources

```bash
cd terraform
terraform plan -var-file="environments/dev.tfvars" -out=tfplan
```

Or with custom values:
```bash
terraform plan \
  -var="project_id=marufeuille-linebot" \
  -var="region=asia-northeast1" \
  -var='artifact_registry_writers=["serviceAccount:ci@marufeuille-linebot.iam.gserviceaccount.com"]'
```

#### Test 5: Show Plan Details

```bash
cd terraform
terraform show tfplan
```

To view in JSON format:
```bash
terraform show tfplan -json | jq .
```

## Input Validation

The configuration includes validation blocks that enforce input constraints:

### project_id

- **Format**: 6-30 characters, lowercase letters, digits, and hyphens
- **Requirement**: Must start and end with lowercase letter or digit
- **Example**: `marufeuille-linebot`

Valid:
```bash
terraform plan -var="project_id=marufeuille-linebot" ...
```

Invalid:
```bash
# Too short
terraform plan -var="project_id=proj" ...

# Invalid characters (uppercase)
terraform plan -var="project_id=MyProject" ...

# Starts with hyphen
terraform plan -var="project_id=-invalid" ...
```

### region

- **Format**: Valid GCP region identifier
- **Default**: `asia-northeast1`
- **Examples**: `us-central1`, `europe-west1`, `asia-southeast2`

Valid regions:
```bash
terraform plan -var="region=us-central1" ...
terraform plan -var="region=europe-west1" ...
```

Invalid:
```bash
terraform plan -var="region=invalid-region" ...
```

### artifact_registry_writers

- **Format**: List of IAM members in `type:identifier` format
- **Valid types**: `serviceAccount`, `user`
- **Default**: Empty list (no write permissions)

Valid formats:
```bash
terraform plan -var='artifact_registry_writers=["serviceAccount:ci@marufeuille-linebot.iam.gserviceaccount.com"]' ...
terraform plan -var='artifact_registry_writers=["user:developer@example.com","serviceAccount:bot@project.iam.gserviceaccount.com"]' ...
```

Invalid:
```bash
# Missing type prefix
terraform plan -var='artifact_registry_writers=["ci@marufeuille-linebot.iam.gserviceaccount.com"]' ...

# Invalid type
terraform plan -var='artifact_registry_writers=["group:team@example.com"]' ...
```

## Expected Outputs

### Successful terraform init

```
Initializing the backend...
Successfully configured the backend "gcs"!
...
Terraform has been successfully initialized!
```

### Successful terraform validate

```
Success! The configuration is valid.
```

### Successful terraform plan

```
Terraform will perform the following actions:

  # module.artifact_registry.google_artifact_registry_repository.repository will be created
  + resource "google_artifact_registry_repository" "repository" {
      + description               = "Docker container repository for dev environment"
      + format                    = "DOCKER"
      + id                        = (known after apply)
      + location                  = "asia-northeast1"
      + project                   = "marufeuille-linebot"
      + repository_id             = "dev-containers"
      ...
    }

  # module.artifact_registry.google_artifact_registry_repository_iam_member.writers[*] will be created
  + resource "google_artifact_registry_repository_iam_member" "writers" {
      + etag       = (known after apply)
      + member     = "serviceAccount:ci@marufeuille-linebot.iam.gserviceaccount.com"
      + project    = "marufeuille-linebot"
      + repository = "dev-containers"
      + role       = "roles/artifactregistry.writer"
    }

Plan: 1 to add, 0 to change, 0 to destroy.
```

## Troubleshooting

### Backend Initialization Failed

If you encounter GCS bucket access errors:
```
Error acquiring the state lock: Error reading GCS object:
```

Verify:
1. GCS bucket exists: `gsutil ls gs://marufeuille-linebot-terraform-backend`
2. You have appropriate permissions: `gsutil iam ch user:$USER:objectViewer gs://marufeuille-linebot-terraform-backend`
3. Authenticate: `gcloud auth application-default login`

### Validation Errors

If a variable validation fails, check the error message and fix the input:

```bash
# Example: Invalid project_id
terraform plan -var="project_id=invalid!project"

# Error:
# Invalid or missing required argument: project_id must be 6-30 characters,
# start and end with lowercase letters or digits, and contain only lowercase
# letters, digits, and hyphens.
```

### Permission Errors

If you encounter IAM permission errors during plan:
```
Error: Error creating Artifact Registry: googleapi: Error 403
```

Verify you have the required roles:
- `roles/artifactregistry.admin` (to create repositories)
- `roles/iam.securityAdmin` (to manage IAM bindings)

## CI/CD Integration

To run tests in a CI/CD pipeline:

```yaml
# Example: GitHub Actions
- name: Terraform Format
  run: terraform fmt -check -recursive terraform/

- name: Run Terraform Tests
  run: bash terraform/tests/terraform_validate_test.sh
```

## Adding New Tests

To add a new validation test:

1. Edit `terraform/tests/terraform_validate_test.sh`
2. Add a new test function following the existing pattern
3. Increment the TEST number in the output
4. Run the full test suite to verify

Example:
```bash
# Test N: Custom validation
echo -e "${YELLOW}[TEST N]${NC} Testing new validation..."
if terraform plan [OPTIONS] > /dev/null 2>&1; then
  echo -e "${GREEN}✓${NC} Test passed"
else
  echo -e "${RED}✗${NC} Test failed"
  exit 1
fi
```

## References

- [Terraform Validation Blocks](https://www.terraform.io/language/values/variables#custom-validation-rules)
- [GCP Artifact Registry](https://cloud.google.com/artifact-registry/docs)
- [Terraform GCP Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
