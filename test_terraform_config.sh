#!/bin/bash
set -e
PASS=0
FAIL=0

test_case() {
  local name="$1"
  local condition="$2"
  if eval "$condition"; then
    echo "✓ $name"
    ((PASS++))
  else
    echo "✗ $name"
    ((FAIL++))
  fi
}

echo "=== Terraform Configuration Tests ==="
echo ""

# Test backend configuration
test_case "GCS backend bucket correct" "grep -q 'marufeuille-linebot-terraform-backend' terraform/main.tf"
test_case "Backend prefix set" "grep -q 'artifact-registry' terraform/main.tf"

# Test provider configuration
test_case "Google provider configured" "grep -q 'provider \"google\"' terraform/main.tf"
test_case "Project ID uses variable" "grep -q 'project = var.project_id' terraform/main.tf"
test_case "Region uses variable" "grep -q 'region = var.region' terraform/main.tf"

# Test variables
test_case "Project ID variable exists" "grep -q 'variable \"project_id\"' terraform/variables.tf"
test_case "Region variable exists" "grep -q 'variable \"region\"' terraform/variables.tf"
test_case "Region default is asia-northeast1" "grep -q 'asia-northeast1' terraform/variables.tf"

# Test outputs
test_case "Repository URL output exists" "grep -q 'repository_url' terraform/outputs.tf"
test_case "Repository ID output exists" "grep -q 'repository_id' terraform/outputs.tf"
test_case "Repository name output exists" "grep -q 'repository_name' terraform/outputs.tf"

# Test module
test_case "Module path is relative" "grep -q './modules/artifact_registry' terraform/main.tf"
test_case "Module repository name is dev-containers" "grep -q 'dev-containers' terraform/main.tf"
test_case "AR resource format is DOCKER" "grep -q 'DOCKER' terraform/modules/artifact_registry/main.tf"

# Test module variables
test_case "Module project_id variable" "grep -q 'variable \"project_id\"' terraform/modules/artifact_registry/variables.tf"
test_case "Module region variable" "grep -q 'variable \"region\"' terraform/modules/artifact_registry/variables.tf"
test_case "Module repository_name variable" "grep -q 'variable \"repository_name\"' terraform/modules/artifact_registry/variables.tf"

# Test environment variables
test_case "dev.tfvars has project_id" "grep -q 'marufeuille-linebot' terraform/environments/dev.tfvars"
test_case "dev.tfvars has region" "grep -q 'asia-northeast1' terraform/environments/dev.tfvars"

# Test version constraints
test_case "Terraform >= 1.0" "grep -q '>= 1.0' terraform/versions.tf"
test_case "Google provider >= 5.0" "grep -q '>= 5.0' terraform/versions.tf"

echo ""
echo "=== Test Summary ==="
echo "Passed: $PASS"
echo "Failed: $FAIL"
if [ $FAIL -eq 0 ]; then
  echo "All tests passed! ✓"
  exit 0
else
  exit 1
fi
