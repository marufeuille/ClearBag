resource "google_artifact_registry_repository" "docker" {
  location      = var.region
  repository_id = var.repository_name
  description   = var.description
  format        = "DOCKER"
  project       = var.project_id
}

# Grant artifactregistry.writer role to specified members for pushing images
resource "google_artifact_registry_repository_iam_member" "writer" {
  for_each = toset(var.artifact_registry_writers)

  project    = var.project_id
  location   = var.region
  repository = google_artifact_registry_repository.docker.name
  role       = "roles/artifactregistry.writer"
  member     = each.value
}
