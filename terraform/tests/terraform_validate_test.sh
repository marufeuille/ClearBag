#!/bin/bash
#
# Terraform Configuration Validation Tests
# This script validates the Terraform configuration for GCP Artifact Registry
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$SCRIPT_DIR"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================"
echo "Terraform Configuration Tests"
echo "================================"
echo ""

# Test 1: Terraform format validation
echo -e "${YELLOW}[TEST 1]${NC} Checking Terraform format..."
if terraform fmt -check -recursive . > /dev/null 2>&1; then
  echo -e "${GREEN}✓${NC} Terraform format is valid"
else
  echo -e "${RED}✗${NC} Terraform format check failed"
  echo "Run: terraform fmt -recursive . to fix formatting issues"
  exit 1
fi
echo ""

# Test 2: Terraform init
echo -e "${YELLOW}[TEST 2]${NC} Initializing Terraform..."
if terraform init -input=false > /dev/null 2>&1; then
  echo -e "${GREEN}✓${NC} Terraform init succeeded"
else
  echo -e "${RED}✗${NC} Terraform init failed"
  exit 1
fi
echo ""

# Test 3: Terraform validate
echo -e "${YELLOW}[TEST 3]${NC} Validating Terraform configuration..."
if terraform validate > /dev/null 2>&1; then
  echo -e "${GREEN}✓${NC} Terraform configuration is valid"
else
  echo -e "${RED}✗${NC} Terraform validation failed"
  terraform validate
  exit 1
fi
echo ""

# Test 4: Terraform plan with dev environment
echo -e "${YELLOW}[TEST 4]${NC} Running Terraform plan for dev environment..."
if terraform plan -var-file="environments/dev.tfvars" -out=tfplan > /dev/null 2>&1; then
  echo -e "${GREEN}✓${NC} Terraform plan succeeded"
else
  echo -e "${RED}✗${NC} Terraform plan failed"
  terraform plan -var-file="environments/dev.tfvars"
  exit 1
fi
echo ""

# Test 5: Verify resource plan output
echo -e "${YELLOW}[TEST 5]${NC} Verifying planned resources..."
PLAN_OUTPUT=$(terraform show tfplan -json | jq -r '.resource_changes[]? | select(.type == "google_artifact_registry_repository") | .type' 2>/dev/null || echo "")

if [ -n "$PLAN_OUTPUT" ]; then
  echo -e "${GREEN}✓${NC} google_artifact_registry_repository resource found in plan"
else
  echo -e "${YELLOW}!${NC} Warning: google_artifact_registry_repository not found in plan (may be expected if resource already exists)"
fi
echo ""

# Test 6: Validate input variables with bad values
echo -e "${YELLOW}[TEST 6]${NC} Testing input validation (invalid project_id)..."
if terraform plan -var="project_id=invalid_project_id" -var-file="environments/dev.tfvars" > /dev/null 2>&1; then
  echo -e "${RED}✗${NC} Validation should have failed for invalid project_id"
  exit 1
else
  echo -e "${GREEN}✓${NC} Correctly rejected invalid project_id"
fi
echo ""

# Test 7: Validate input variables with bad region
echo -e "${YELLOW}[TEST 7]${NC} Testing input validation (invalid region)..."
if terraform plan -var="region=invalid-region" -var-file="environments/dev.tfvars" > /dev/null 2>&1; then
  echo -e "${RED}✗${NC} Validation should have failed for invalid region"
  exit 1
else
  echo -e "${GREEN}✓${NC} Correctly rejected invalid region"
fi
echo ""

# Test 8: Validate IAM format
echo -e "${YELLOW}[TEST 8]${NC} Testing input validation (invalid IAM format)..."
if terraform plan -var-file="environments/dev.tfvars" -var='artifact_registry_writers=["invalid-format"]' > /dev/null 2>&1; then
  echo -e "${RED}✗${NC} Validation should have failed for invalid IAM format"
  exit 1
else
  echo -e "${GREEN}✓${NC} Correctly rejected invalid IAM format"
fi
echo ""

# Test 9: Validate valid IAM formats
echo -e "${YELLOW}[TEST 9]${NC} Testing input validation (valid IAM formats)..."
if terraform plan -var-file="environments/dev.tfvars" -var='artifact_registry_writers=["serviceAccount:test@project.iam.gserviceaccount.com","user:test@example.com"]' > /dev/null 2>&1; then
  echo -e "${GREEN}✓${NC} Correctly accepted valid IAM formats"
else
  echo -e "${RED}✗${NC} Validation failed for valid IAM formats"
  terraform plan -var-file="environments/dev.tfvars" -var='artifact_registry_writers=["serviceAccount:test@project.iam.gserviceaccount.com","user:test@example.com"]'
  exit 1
fi
echo ""

# Cleanup
rm -f tfplan

echo "================================"
echo -e "${GREEN}All tests passed!${NC}"
echo "================================"
