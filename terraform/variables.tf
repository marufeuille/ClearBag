variable "project_id" {
  description = "GCP Project ID"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Project ID must be 6-30 characters, start and end with lowercase letters or digits, and contain only lowercase letters, digits, and hyphens."
  }
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "asia-northeast1"

  validation {
    condition = contains([
      "asia-east1",
      "asia-east2",
      "asia-northeast1",
      "asia-northeast2",
      "asia-northeast3",
      "asia-south1",
      "asia-south2",
      "asia-southeast1",
      "asia-southeast2",
      "europe-central2",
      "europe-north1",
      "europe-southwest1",
      "europe-west1",
      "europe-west2",
      "europe-west3",
      "europe-west4",
      "europe-west6",
      "europe-west8",
      "europe-west9",
      "europe-west12",
      "me-central1",
      "me-central2",
      "me-west1",
      "northamerica-northeast1",
      "northamerica-northeast2",
      "southamerica-east1",
      "southamerica-west1",
      "us-central1",
      "us-east1",
      "us-east4",
      "us-east5",
      "us-south1",
      "us-west1",
      "us-west2",
      "us-west3",
      "us-west4"
    ], var.region)
    error_message = "Region must be a valid GCP region."
  }
}

variable "artifact_registry_writers" {
  description = "List of members (service accounts or users) with artifactregistry.writer role for pushing images. Format: 'serviceAccount:EMAIL' or 'user:EMAIL'"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for member in var.artifact_registry_writers :
      can(regex("^(serviceAccount|user):.+$", member))
    ])
    error_message = "Each member must be in format 'serviceAccount:EMAIL' or 'user:EMAIL'. Example: 'serviceAccount:my-sa@project.iam.gserviceaccount.com'"
  }
}
