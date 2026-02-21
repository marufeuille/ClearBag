variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-northeast1"
}

variable "function_name" {
  description = "Cloud Functions name"
  type        = string
  default     = "school-agent-v2"
}

variable "runtime" {
  description = "Cloud Functions runtime"
  type        = string
  default     = "python313"
}

variable "memory" {
  description = "Memory in MiB"
  type        = number
  default     = 1024
}

variable "entry_point" {
  description = "Cloud Functions entry point"
  type        = string
  default     = "school_agent_http"
}

variable "service_account_email" {
  description = "Service Account email for Cloud Functions"
  type        = string
  default     = ""
  nullable    = true
}

variable "artifact_registry_repo" {
  description = "Artifact Registry repository name"
  type        = string
  default     = "school-agent"
}

variable "scheduler_schedule" {
  description = "Cloud Scheduler schedule (cron format)"
  type        = string
  default     = "0 9,17 * * *"
}

variable "scheduler_timezone" {
  description = "Cloud Scheduler timezone"
  type        = string
  default     = "Asia/Tokyo"
}

variable "env_vars" {
  description = "Environment variables for Cloud Functions"
  type = object({
    PROJECT_ID        = string
    SPREADSHEET_ID    = string
    INBOX_FOLDER_ID   = string
    ARCHIVE_FOLDER_ID = string
  })
  default = {
    PROJECT_ID        = ""
    SPREADSHEET_ID    = ""
    INBOX_FOLDER_ID   = ""
    ARCHIVE_FOLDER_ID = ""
  }
}
