# WARNING: このファイルには機密情報が含まれる可能性があります。コミットしないでください。
# *.tfvars は .gitignore に含まれていません。git add する前に必ず確認してください。

project_id       = "<GCP_PROJECT_ID>"
region           = "asia-northeast1"
prefix           = "dev-"
scheduler_paused = true

env_vars = {
  PROJECT_ID        = "<GCP_PROJECT_ID>"
  SPREADSHEET_ID    = "<DEV_SPREADSHEET_ID>"    # dev用スプレッドシートIDを設定
  INBOX_FOLDER_ID   = "<DEV_INBOX_FOLDER_ID>"   # dev用Google DriveフォルダIDを設定
  ARCHIVE_FOLDER_ID = "<DEV_ARCHIVE_FOLDER_ID>" # dev用Google DriveフォルダIDを設定
}

# GCP Secret Manager への事前登録が必要なシークレット:
#   dev-school-agent-slack-bot-token
#   dev-school-agent-slack-channel-id
#   dev-school-agent-todoist-api-token
#
# GCP で別途用意が必要なリソース:
#   - dev用 Google Sheets スプレッドシート → SPREADSHEET_ID に設定
#   - dev用 Google Drive インボックスフォルダ → INBOX_FOLDER_ID に設定
#   - dev用 Google Drive アーカイブフォルダ → ARCHIVE_FOLDER_ID に設定
#   - dev用 Slack チャンネル ID → Secret Manager の dev-school-agent-slack-channel-id に登録
