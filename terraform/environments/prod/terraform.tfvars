# WARNING: このファイルには機密情報が含まれる可能性があります。コミットしないでください。
# *.tfvars は .gitignore に含まれていません。git add する前に必ず確認してください。

project_id       = "<GCP_PROJECT_ID>"
region           = "asia-northeast1"
prefix           = ""
scheduler_paused = false

env_vars = {
  PROJECT_ID        = "<GCP_PROJECT_ID>"
  SPREADSHEET_ID    = "<PROD_SPREADSHEET_ID>"
  INBOX_FOLDER_ID   = "<PROD_INBOX_FOLDER_ID>"
  ARCHIVE_FOLDER_ID = "<PROD_ARCHIVE_FOLDER_ID>"
}
