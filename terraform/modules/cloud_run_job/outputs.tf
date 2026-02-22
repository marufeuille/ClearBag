output "job_name" {
  description = "Cloud Run Job 名"
  value       = google_cloud_run_v2_job.this.name
}

output "job_api_uri" {
  description = "Cloud Scheduler から呼び出す Jobs API URI"
  value       = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.this.name}:run"
}
