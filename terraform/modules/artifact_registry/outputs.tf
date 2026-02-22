output "registry_url" {
  description = "Artifact Registry の Docker リポジトリ URL"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}"
}

output "image_base" {
  description = "イメージ名のベース（タグなし）"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${var.repository_id}/school-agent-v2"
}
