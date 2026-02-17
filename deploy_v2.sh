#!/bin/bash

# ==========================================
# Configuration
# ==========================================
FUNCTION_NAME="school-agent-v2"
REGION="asia-northeast1"
RUNTIME="python313"
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
# Note: TODOIST and SLACK variables are optional for v2
REQUIRED_VARS=("PROJECT_ID" "SPREADSHEET_ID" "INBOX_FOLDER_ID" "ARCHIVE_FOLDER_ID")
for VAR in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!VAR}" ]; then
    echo "Error: $VAR is not set in .env"
    exit 1
  fi
done

# Optional variables (warn if missing but don't fail)
OPTIONAL_VARS=("SLACK_BOT_TOKEN" "SLACK_CHANNEL_ID" "TODOIST_API_TOKEN")
for VAR in "${OPTIONAL_VARS[@]}"; do
  if [ -z "${!VAR}" ]; then
    echo "Warning: $VAR is not set in .env (optional)"
  fi
done

# ==========================================
# Preparation
# ==========================================

# Generate requirements.txt
echo "Generating requirements.txt..."
uv export -o requirements.txt --no-hashes

# Extract Service Account Email
# Try multiple methods in order of preference
if [ -n "$SERVICE_ACCOUNT_EMAIL" ]; then
  echo "Using SERVICE_ACCOUNT_EMAIL from environment variable"
elif [ -f "service_account.json" ]; then
  echo "Extracting SERVICE_ACCOUNT_EMAIL from service_account.json"
  SERVICE_ACCOUNT_EMAIL=$(grep -o '"client_email": "[^"]*' service_account.json | cut -d'"' -f4)
else
  echo "Using default service account from gcloud"
  SERVICE_ACCOUNT_EMAIL=$(gcloud iam service-accounts list \
    --project="$PROJECT_ID" \
    --filter="email:*@$PROJECT_ID.iam.gserviceaccount.com" \
    --format="value(email)" \
    --limit=1)
fi

if [ -z "$SERVICE_ACCOUNT_EMAIL" ]; then
  echo "Error: Could not determine SERVICE_ACCOUNT_EMAIL"
  echo "Please set SERVICE_ACCOUNT_EMAIL environment variable or ensure service_account.json exists"
  exit 1
fi

echo "Using Service Account: $SERVICE_ACCOUNT_EMAIL"

# Construct Environment Variables String (Non-secrets)
ENV_VARS="PROJECT_ID=$PROJECT_ID"
ENV_VARS+=",SPREADSHEET_ID=$SPREADSHEET_ID"
ENV_VARS+=",INBOX_FOLDER_ID=$INBOX_FOLDER_ID"
ENV_VARS+=",ARCHIVE_FOLDER_ID=$ARCHIVE_FOLDER_ID"

# ==========================================
# Secret Manager Setup (share v1 secrets)
# ==========================================

create_and_grant_secret() {
  local SECRET_NAME=$1
  local SECRET_VALUE=$2
  local SA_EMAIL=$3

  echo "Processing secret: $SECRET_NAME"

  # Skip if secret value is empty (optional)
  if [ -z "$SECRET_VALUE" ]; then
    echo "  Skipping (no value provided)"
    return
  fi

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

# Define Secret Mappings (v1と同じSecret名を使用)
SLACK_BOT_TOKEN_SECRET="school-agent-slack-bot-token"
SLACK_CHANNEL_ID_SECRET="school-agent-slack-channel-id"
TODOIST_API_TOKEN_SECRET="school-agent-todoist-api-token"

# Create and Grant Secrets (optional変数も処理)
create_and_grant_secret "$SLACK_BOT_TOKEN_SECRET" "$SLACK_BOT_TOKEN" "$SERVICE_ACCOUNT_EMAIL"
create_and_grant_secret "$SLACK_CHANNEL_ID_SECRET" "$SLACK_CHANNEL_ID" "$SERVICE_ACCOUNT_EMAIL"
create_and_grant_secret "$TODOIST_API_TOKEN_SECRET" "$TODOIST_API_TOKEN" "$SERVICE_ACCOUNT_EMAIL"

# Construct Secrets String for Deployment
SECRETS_MAPPING=""
if [ -n "$SLACK_BOT_TOKEN" ]; then
  SECRETS_MAPPING="SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN_SECRET:latest"
fi
if [ -n "$SLACK_CHANNEL_ID" ]; then
  if [ -n "$SECRETS_MAPPING" ]; then
    SECRETS_MAPPING+=","
  fi
  SECRETS_MAPPING+="SLACK_CHANNEL_ID=$SLACK_CHANNEL_ID_SECRET:latest"
fi
if [ -n "$TODOIST_API_TOKEN" ]; then
  if [ -n "$SECRETS_MAPPING" ]; then
    SECRETS_MAPPING+=","
  fi
  SECRETS_MAPPING+="TODOIST_API_TOKEN=$TODOIST_API_TOKEN_SECRET:latest"
fi

# ==========================================
# main_v2.py handling
# ==========================================

# Cloud Functionsはデフォルトでmain.pyを探すため、
# main_v2.pyを一時的にmain.pyとしてコピーする
MAIN_BACKUP=""
if [ -f "main.py" ]; then
  echo "Backing up existing main.py to main.py.v1backup..."
  MAIN_BACKUP="main.py.v1backup"
  cp main.py "$MAIN_BACKUP"
fi

echo "Copying main_v2.py to main.py for deployment..."
cp main_v2.py main.py

# Cleanup function
cleanup_main() {
  echo "Restoring original main.py..."
  if [ -n "$MAIN_BACKUP" ] && [ -f "$MAIN_BACKUP" ]; then
    mv "$MAIN_BACKUP" main.py
  else
    rm -f main.py
  fi
}

# Set trap to ensure cleanup happens even if script fails
trap cleanup_main EXIT

# ==========================================
# Deployment
# ==========================================

if [ "$DEPLOY_FUNCTION" = true ]; then
  echo "Deploying function: $FUNCTION_NAME"
  echo "Project: $PROJECT_ID"
  echo "Region: $REGION"
  echo "Service Account: $SERVICE_ACCOUNT_EMAIL"

  DEPLOY_CMD="gcloud functions deploy $FUNCTION_NAME \
    --gen2 \
    --project=$PROJECT_ID \
    --region=$REGION \
    --runtime=$RUNTIME \
    --source=$SOURCE_DIR \
    --entry-point=$ENTRY_POINT \
    --service-account=$SERVICE_ACCOUNT_EMAIL \
    --memory=1024MiB \
    --trigger-http \
    --no-allow-unauthenticated \
    --set-env-vars $ENV_VARS"

  # Add secrets only if any are defined
  if [ -n "$SECRETS_MAPPING" ]; then
    DEPLOY_CMD+=" --set-secrets $SECRETS_MAPPING"
  fi

  eval $DEPLOY_CMD
else
  echo "Skipping gcloud functions deploy..."
fi

# ==========================================
# Scheduler
# ==========================================

echo "Setting up Cloud Scheduler..."
SCHEDULER_JOB_NAME="${FUNCTION_NAME}-scheduler"
SCHEDULE="0 9,17 * * *" # 朝9時と夕方17時
TIMEZONE="Asia/Tokyo"

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
    --time-zone="$TIMEZONE" \
    --uri="$FUNCTION_URL" \
    --http-method=POST \
    --oidc-service-account-email="$SERVICE_ACCOUNT_EMAIL"
else
  echo "Creating new scheduler job..."
  gcloud scheduler jobs create http "$SCHEDULER_JOB_NAME" \
    --project="$PROJECT_ID" \
    --location="$REGION" \
    --schedule="$SCHEDULE" \
    --time-zone="$TIMEZONE" \
    --uri="$FUNCTION_URL" \
    --http-method=POST \
    --oidc-service-account-email="$SERVICE_ACCOUNT_EMAIL"
fi

echo "Deployment and Scheduling finished."
