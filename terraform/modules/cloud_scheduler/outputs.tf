output "job_name" {
  description = "Cloud Scheduler ジョブ名"
  value       = google_cloud_scheduler_job.this.name
}
