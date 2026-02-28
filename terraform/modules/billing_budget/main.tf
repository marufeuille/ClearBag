# ---------------------------------------------------------------------------
# GCP 予算アラート
# ---------------------------------------------------------------------------

# budget_filter.projects は "projects/{PROJECT_NUMBER}" 形式が必要
data "google_project" "this" {
  project_id = var.project_id
}

resource "google_billing_budget" "this" {
  billing_account = var.billing_account_id
  display_name    = "Monthly Budget - ${var.project_id}"

  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }

  amount {
    specified_amount {
      currency_code = var.currency_code
      units         = tostring(var.budget_amount)
    }
  }

  dynamic "threshold_rules" {
    for_each = var.alert_thresholds
    content {
      threshold_percent = threshold_rules.value
      spend_basis       = "CURRENT_SPEND"
    }
  }

  all_updates_rule {
    monitoring_notification_channels = [var.notification_channel_name]
    disable_default_iam_recipients   = false
  }
}
