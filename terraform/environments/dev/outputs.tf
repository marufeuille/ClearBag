output "registry_url" {
  description = "dev 環境の Artifact Registry URL"
  value       = module.artifact_registry.registry_url
}

output "image_base" {
  description = "dev 環境のイメージ名ベース"
  value       = module.artifact_registry.image_base
}
