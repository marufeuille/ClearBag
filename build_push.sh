#!/bin/bash
set -euo pipefail

# ==========================================
# Configuration
# ==========================================
REGION="asia-northeast1"
IMAGE_NAME="school-agent-v2"

# 引数: ENV（dev/prod）, IMAGE_TAG（任意）
ENV="${1:-dev}"
IMAGE_TAG="${2:-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')}"

# 環境ごとのリポジトリID
case "$ENV" in
  dev)  REPOSITORY_ID="school-agent-dev" ;;
  prod) REPOSITORY_ID="school-agent" ;;
  *)    echo "Error: Unknown environment '$ENV'. Use 'dev' or 'prod'."; exit 1 ;;
esac

# Load environment variables
if [ -f .env ]; then
  export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

# Check required
if [ -z "${PROJECT_ID:-}" ]; then
  echo "Error: PROJECT_ID is not set in .env"
  exit 1
fi

IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_ID}/${IMAGE_NAME}:${IMAGE_TAG}"

echo "Environment : ${ENV}"
echo "Image URL   : ${IMAGE_URL}"

# ==========================================
# Preparation
# ==========================================
echo "Generating requirements.txt..."
uv export -o requirements.txt --no-hashes

# ==========================================
# Build
# ==========================================
echo "Building Docker image..."
docker build -t "${IMAGE_URL}" .

# ==========================================
# Push
# ==========================================
echo "Configuring Docker auth for Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

echo "Pushing image..."
docker push "${IMAGE_URL}"

echo ""
echo "Successfully pushed: ${IMAGE_URL}"
# 後続の処理から参照できるようにexportで出力
echo "IMAGE_URL=${IMAGE_URL}"
