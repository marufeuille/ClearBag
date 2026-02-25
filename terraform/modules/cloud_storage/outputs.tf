output "bucket_name" {
  value       = google_storage_bucket.this.name
  description = "GCS バケット名"
}

output "bucket_url" {
  value       = google_storage_bucket.this.url
  description = "GCS バケット URL（gs://...）"
}
