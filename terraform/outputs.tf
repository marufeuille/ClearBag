output "repository_url" {
  description = "Artifact Registry Repository URL"
  value       = module.artifact_registry.repository_url
}

output "repository_id" {
  description = "Artifact Registry Repository ID"
  value       = module.artifact_registry.repository_id
}

output "repository_name" {
  description = "Artifact Registry Repository Name"
  value       = module.artifact_registry.repository_name
}

output "artifact_registry_writers" {
  description = "List of members with artifactregistry.writer role"
  value       = module.artifact_registry.artifact_registry_writers
}
