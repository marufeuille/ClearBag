output "service_url" {
  value       = google_cloud_run_v2_service.this.uri
  description = "Cloud Run Service の URL"
}

output "service_name" {
  value       = google_cloud_run_v2_service.this.name
  description = "Cloud Run Service 名"
}
