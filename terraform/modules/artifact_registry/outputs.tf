output "repository_url" {
  description = "Repository URL for pushing Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_name}"
}

output "repository_id" {
  description = "Repository ID"
  value       = "${var.project_id}/${var.region}/${var.repository_name}"
}

output "repository_name" {
  description = "Repository Name"
  value       = var.repository_name
}

output "artifact_registry_writers" {
  description = "List of members with artifactregistry.writer role"
  value       = var.artifact_registry_writers
}
