terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source = "hashicorp/google"
    }
    google-beta = {
      source = "hashicorp/google-beta"
    }
  }

  backend "gcs" {
    bucket = "marufeuille-linebot-terraform-backend"
    prefix = "prod/tfstate"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

module "school_agent" {
  source = "../../modules/school-agent"

  project_id       = var.project_id
  region           = var.region
  prefix           = var.prefix
  scheduler_paused = var.scheduler_paused
  env_vars         = var.env_vars
}

variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
}

variable "prefix" {
  description = "Resource name prefix"
  type        = string
}

variable "scheduler_paused" {
  description = "Whether to pause the Cloud Scheduler job"
  type        = bool
}

variable "env_vars" {
  description = "Environment variables for Cloud Functions"
  type = object({
    PROJECT_ID        = string
    SPREADSHEET_ID    = string
    INBOX_FOLDER_ID   = string
    ARCHIVE_FOLDER_ID = string
  })
}
