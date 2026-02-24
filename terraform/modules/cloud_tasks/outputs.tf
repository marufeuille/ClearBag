output "queue_name" {
  value       = google_cloud_tasks_queue.this.name
  description = "Cloud Tasks キューの完全修飾名"
}

output "queue_id" {
  value       = var.queue_name
  description = "Cloud Tasks キュー ID（短縮名）"
}
