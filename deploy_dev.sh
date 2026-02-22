#!/bin/bash
set -euo pipefail

# ==========================================
# Configuration
# ==========================================
ENV="dev"

# 引数: IMAGE_TAG（任意。省略時は git SHA）
IMAGE_TAG="${1:-}"

# ==========================================
# Load environment variables（build_push.sh が参照するため）
# ==========================================
if [ -f .env ]; then
  export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

# ==========================================
# Build & Push
# ==========================================
echo "--- Build & Push ---"
BUILD_OUTPUT=$(./build_push.sh "${ENV}" ${IMAGE_TAG:+"${IMAGE_TAG}"})
echo "${BUILD_OUTPUT}"

IMAGE_URL=$(echo "${BUILD_OUTPUT}" | grep '^IMAGE_URL=' | cut -d'=' -f2-)
if [ -z "${IMAGE_URL}" ]; then
  echo "Error: Could not extract IMAGE_URL from build_push.sh output"
  exit 1
fi

echo ""
echo "--- Terraform Apply ---"
echo "Image: ${IMAGE_URL}"

# ==========================================
# Terraform Apply
# ==========================================
cd terraform/environments/dev
terraform apply -var="image_url=${IMAGE_URL}" -auto-approve

echo ""
echo "Deployment finished."
terraform output job_name
