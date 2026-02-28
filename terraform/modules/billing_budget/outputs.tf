output "budget_id" {
  value       = google_billing_budget.this.id
  description = "予算リソースの ID"
}

output "budget_display_name" {
  value       = google_billing_budget.this.display_name
  description = "予算の表示名"
}
