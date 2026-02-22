terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
  # 将来的にGCSバックエンドへ移行する（別タスク）
  # backend "gcs" {
  #   bucket = "YOUR_TFSTATE_BUCKET"
  #   prefix = "terraform/environments/dev"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = "school-agent-dev"
  environment   = "dev"
}
