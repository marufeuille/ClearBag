output "database_name" {
  value       = google_firestore_database.this.name
  description = "Firestore データベース名"
}
