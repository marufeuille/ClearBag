terraform {
  backend "gcs" {
    bucket = "marufeuille-linebot-terraform-backend"
    prefix = "artifact-registry"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "artifact_registry" {
  source = "./modules/artifact_registry"

  project_id      = var.project_id
  region          = var.region
  repository_name = "dev-containers"
  description     = "Docker container repository for dev environment"

  # IAM configuration for pushing images
  # Example: ["serviceAccount:my-sa@project.iam.gserviceaccount.com", "user:user@example.com"]
  artifact_registry_writers = var.artifact_registry_writers
}
