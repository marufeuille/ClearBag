resource "google_storage_bucket" "this" {
  project       = var.project_id
  name          = var.bucket_name
  location      = var.location
  force_destroy = false

  # バージョニングは不要（ユーザーが再アップロードすれば良い）
  versioning {
    enabled = false
  }

  # ライフサイクル: 1年後に自動削除
  dynamic "lifecycle_rule" {
    for_each = var.lifecycle_delete_days > 0 ? [1] : []
    content {
      action {
        type = "Delete"
      }
      condition {
        age = var.lifecycle_delete_days
      }
    }
  }

  # パブリックアクセス防止（ファイルは署名付き URL または API 経由でのみアクセス）
  public_access_prevention = "enforced"

  uniform_bucket_level_access = true
}

# Cloud Run SA にバケットへの読み書き権限を付与
resource "google_storage_bucket_iam_member" "object_admin" {
  bucket = google_storage_bucket.this.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.service_account_email}"
}
