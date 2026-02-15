#!/bin/bash

# ==========================================
# Configuration
# ==========================================
FUNCTION_NAME="school-agent"
REGION="asia-northeast1"
RUNTIME="python311"
ENTRY_POINT="school_agent_http"
SOURCE_DIR="."

# Parse arguments
DEPLOY_FUNCTION=true
if [[ "$1" == "--scheduler-only" ]]; then
  DEPLOY_FUNCTION=false
  echo "Skipping function deployment (--scheduler-only passed)."
fi

# Load environment variables
if [ -f .env ]; then
  export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

# Check required environment variables
# Check required environment variables
REQUIRED_VARS=("PROJECT_ID" "SPREADSHEET_ID" "INBOX_FOLDER_ID" "ARCHIVE_FOLDER_ID" "SLACK_BOT_TOKEN" "SLACK_CHANNEL_ID" "TODOIST_API_TOKEN")
for VAR in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!VAR}" ]; then
    echo "Error: $VAR is not set in .env"
    exit 1
  fi
done

# ==========================================
# Preparation
# ==========================================

# Generate requirements.txt
echo "Generating requirements.txt..."
uv export -o requirements.txt --no-hashes

# Extract Service Account Email
SERVICE_ACCOUNT_EMAIL=$(grep -o '"client_email": "[^"]*' service_account.json | cut -d'"' -f4)

if [ -z "$SERVICE_ACCOUNT_EMAIL" ]; then
  echo "Error: Could not extract client_email from service_account.json"
  exit 1
fi

# Construct Environment Variables String (Non-secrets)
ENV_VARS="PROJECT_ID=$PROJECT_ID"
ENV_VARS+=",SPREADSHEET_ID=$SPREADSHEET_ID"
ENV_VARS+=",INBOX_FOLDER_ID=$INBOX_FOLDER_ID"
ENV_VARS+=",ARCHIVE_FOLDER_ID=$ARCHIVE_FOLDER_ID"

# ==========================================
# Secret Manager Setup
# ==========================================

create_and_grant_secret() {
  local SECRET_NAME=$1
  local SECRET_VALUE=$2
  local SA_EMAIL=$3

  echo "Processing secret: $SECRET_NAME"

  # Create secret if not exists
  if ! gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" > /dev/null 2>&1; then
    echo "  Creating secret..."
    gcloud secrets create "$SECRET_NAME" --replication-policy="automatic" --project="$PROJECT_ID"
  fi

  # Add secret version
  echo "  Adding new version..."
  echo -n "$SECRET_VALUE" | gcloud secrets versions add "$SECRET_NAME" --data-file=- --project="$PROJECT_ID" > /dev/null

  # Grant access to Service Account
  echo "  Granting access to Service Account..."
  gcloud secrets add-iam-policy-binding "$SECRET_NAME" \
    --project="$PROJECT_ID" \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor" > /dev/null
}

# Define Secret Mappings (EnvVar -> SecretName)
SLACK_BOT_TOKEN_SECRET="school-agent-slack-bot-token"
SLACK_CHANNEL_ID_SECRET="school-agent-slack-channel-id"
TODOIST_API_TOKEN_SECRET="school-agent-todoist-api-token"

# Create and Grant Secrets
create_and_grant_secret "$SLACK_BOT_TOKEN_SECRET" "$SLACK_BOT_TOKEN" "$SERVICE_ACCOUNT_EMAIL"
create_and_grant_secret "$SLACK_CHANNEL_ID_SECRET" "$SLACK_CHANNEL_ID" "$SERVICE_ACCOUNT_EMAIL"
create_and_grant_secret "$TODOIST_API_TOKEN_SECRET" "$TODOIST_API_TOKEN" "$SERVICE_ACCOUNT_EMAIL"

# Construct Secrets String for Deployment
SECRETS_MAPPING="SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN_SECRET:latest"
SECRETS_MAPPING+=",SLACK_CHANNEL_ID=$SLACK_CHANNEL_ID_SECRET:latest"
SECRETS_MAPPING+=",TODOIST_API_TOKEN=$TODOIST_API_TOKEN_SECRET:latest"

# ==========================================
# Deployment
# ==========================================

if [ "$DEPLOY_FUNCTION" = true ]; then
  echo "Deploying function: $FUNCTION_NAME"
  echo "Project: $PROJECT_ID"
  echo "Region: $REGION"
  echo "Service Account: $SERVICE_ACCOUNT_EMAIL"

  gcloud functions deploy "$FUNCTION_NAME" \
    --gen2 \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --runtime="$RUNTIME" \
    --source="$SOURCE_DIR" \
    --entry-point="$ENTRY_POINT" \
    --service-account="$SERVICE_ACCOUNT_EMAIL" \
    --memory=1024MiB \
    --trigger-http \
    --allow-unauthenticated \
    --set-env-vars "$ENV_VARS" \
    --set-secrets "$SECRETS_MAPPING"
else
  echo "Skipping gcloud functions deploy..."
fi
#
## ==========================================
## Scheduler
## ==========================================

echo "Setting up Cloud Scheduler..."
SCHEDULER_JOB_NAME="${FUNCTION_NAME}-scheduler"
SCHEDULE="0 * * * *" # Every hour

# Get the Function URL
FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" --project="$PROJECT_ID" --region="$REGION" --format="value(serviceConfig.uri)")

if [ -z "$FUNCTION_URL" ]; then
  echo "Error: Could not retrieve Function URL."
  exit 1
fi

echo "Function URL: $FUNCTION_URL"

# Check if job exists
if gcloud scheduler jobs describe "$SCHEDULER_JOB_NAME" --project="$PROJECT_ID" --location="$REGION" > /dev/null 2>&1; then
  echo "Updating existing scheduler job..."
  gcloud scheduler jobs update http "$SCHEDULER_JOB_NAME" \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    --schedule="$SCHEDULE" \
    --uri="$FUNCTION_URL" \
    --http-method=POST \
    --oidc-service-account-email="$SERVICE_ACCOUNT_EMAIL"
else
  echo "Creating new scheduler job..."
  gcloud scheduler jobs create http "$SCHEDULER_JOB_NAME" \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    --schedule="$SCHEDULE" \
    --uri="$FUNCTION_URL" \
    --http-method=POST \
    --oidc-service-account-email="$SERVICE_ACCOUNT_EMAIL"
fi

echo "Deployment and Scheduling finished."
