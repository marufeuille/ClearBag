resource "google_firestore_database" "this" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.location
  type        = "FIRESTORE_NATIVE"

  # 誤削除防止
  deletion_policy = "DELETE"
}

# Cloud Run Service / Worker SA に Firestore の読み書き権限を付与
resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${var.service_account_email}"
}

# コレクショングループクエリ用の複合インデックス
# users/{uid}/documents/{docId}/events をまたいだ日付範囲クエリに必要
resource "google_firestore_index" "events_by_start" {
  project     = var.project_id
  database    = google_firestore_database.this.name
  collection  = "events"
  query_scope = "COLLECTION_GROUP"

  fields {
    field_path = "family_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "start"
    order      = "ASCENDING"
  }

  depends_on = [google_firestore_database.this]
}

# tasks の completed フィールドでフィルタークエリを可能にする
resource "google_firestore_index" "tasks_by_completed" {
  project     = var.project_id
  database    = google_firestore_database.this.name
  collection  = "tasks"
  query_scope = "COLLECTION_GROUP"

  fields {
    field_path = "family_id"
    order      = "ASCENDING"
  }

  fields {
    field_path = "completed"
    order      = "ASCENDING"
  }

  depends_on = [google_firestore_database.this]
}

# 招待トークンで招待情報を検索するための collection_group インデックス
resource "google_firestore_index" "invitations_by_token" {
  project     = var.project_id
  database    = google_firestore_database.this.name
  collection  = "invitations"
  query_scope = "COLLECTION_GROUP"

  fields {
    field_path = "token"
    order      = "ASCENDING"
  }

  fields {
    field_path = "__name__"
    order      = "ASCENDING"
  }

  depends_on = [google_firestore_database.this]
}
