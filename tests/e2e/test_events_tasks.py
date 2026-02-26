"""イベント・タスク API の E2E テスト

Firestore にサンプルデータを直接書き込んで、API クエリの動作を検証する。
collection_group クエリ（events, tasks）は Emulator ではインデックス定義なしで動作する。
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.e2e


@pytest.fixture
def family_with_events_and_tasks(e2e_client, firestore_client):
    """イベント・タスクデータ付きのファミリーを作成するフィクスチャ。

    1. /api/families/me で family_id を取得（ファミリー自動作成）
    2. documents/{docId}/events, tasks に直接テストデータを書き込む
    """
    r = e2e_client.get("/api/families/me")
    assert r.status_code == 200
    family_id = r.json()["id"]

    # ドキュメントドキュメントを作成
    doc_ref = (
        firestore_client.collection("families")
        .document(family_id)
        .collection("documents")
        .document()
    )
    doc_ref.set(
        {
            "uid": family_id,
            "status": "completed",
            "original_filename": "test.pdf",
            "content_hash": "abc123",
            "storage_path": "gs://test/test.pdf",
            "mime_type": "application/pdf",
            "summary": "テストドキュメント",
            "category": "event",
        }
    )

    # イベントを作成
    event_ref = doc_ref.collection("events").document()
    event_ref.set(
        {
            "family_id": family_id,
            "document_id": doc_ref.id,
            "summary": "運動会",
            "start": "2026-05-01T09:00:00",
            "end": "2026-05-01T15:00:00",
            "location": "校庭",
            "description": "保護者も参加可",
            "confidence": "HIGH",
        }
    )

    # タスクを作成（未完了）
    task_ref = doc_ref.collection("tasks").document()
    task_ref.set(
        {
            "family_id": family_id,
            "document_id": doc_ref.id,
            "title": "参加費を支払う",
            "due_date": "2026-04-25",
            "assignee": "PARENT",
            "note": "3000円",
            "completed": False,
        }
    )

    return {
        "family_id": family_id,
        "doc_id": doc_ref.id,
        "task_id": task_ref.id,
    }


class TestEvents:
    """GET /api/events のテスト"""

    def test_list_events_returns_all(self, e2e_client, family_with_events_and_tasks):
        """全イベントを返す"""
        r = e2e_client.get("/api/events")
        assert r.status_code == 200
        events = r.json()
        assert len(events) == 1
        assert events[0]["summary"] == "運動会"
        assert events[0]["location"] == "校庭"
        assert events[0]["confidence"] == "HIGH"

    def test_list_events_with_from_date_filter(
        self, e2e_client, family_with_events_and_tasks
    ):
        """from_date 以降のイベントだけ返す"""
        # 範囲内
        r = e2e_client.get("/api/events?from_date=2026-05-01")
        assert r.status_code == 200
        assert len(r.json()) == 1

        # 範囲外（翌月以降）
        r = e2e_client.get("/api/events?from_date=2026-06-01")
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_list_events_with_to_date_filter(
        self, e2e_client, family_with_events_and_tasks
    ):
        """to_date 以前のイベントだけ返す"""
        # 範囲内
        r = e2e_client.get("/api/events?to_date=2026-05-31")
        assert r.status_code == 200
        assert len(r.json()) == 1

        # 範囲外（前月まで）
        r = e2e_client.get("/api/events?to_date=2026-04-30")
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_list_events_with_date_range(
        self, e2e_client, family_with_events_and_tasks
    ):
        """from_date + to_date の組み合わせが機能する"""
        r = e2e_client.get("/api/events?from_date=2026-05-01&to_date=2026-05-31")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_empty_events_for_new_family(self, e2e_client):
        """データなしのファミリーは空リストを返す"""
        e2e_client.get("/api/families/me")
        r = e2e_client.get("/api/events")
        assert r.status_code == 200
        assert r.json() == []


class TestTasks:
    """GET /api/tasks, PATCH /api/tasks/{id} のテスト"""

    def test_list_tasks_returns_all(self, e2e_client, family_with_events_and_tasks):
        """全タスクを返す"""
        r = e2e_client.get("/api/tasks")
        assert r.status_code == 200
        tasks = r.json()
        assert len(tasks) == 1
        assert tasks[0]["title"] == "参加費を支払う"
        assert tasks[0]["completed"] is False

    def test_filter_incomplete_tasks(self, e2e_client, family_with_events_and_tasks):
        """completed=false フィルターが機能する"""
        r = e2e_client.get("/api/tasks?completed=false")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_filter_complete_tasks_returns_empty(
        self, e2e_client, family_with_events_and_tasks
    ):
        """completed=true フィルターで未完了タスクは返さない"""
        r = e2e_client.get("/api/tasks?completed=true")
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_update_task_completed(self, e2e_client, family_with_events_and_tasks):
        """タスクを完了済みに更新できる"""
        task_id = family_with_events_and_tasks["task_id"]

        r = e2e_client.patch(f"/api/tasks/{task_id}", json={"completed": True})
        assert r.status_code == 200
        assert r.json()["completed"] is True

        # 完了済みタスクがクエリで取得できることを確認
        r = e2e_client.get("/api/tasks?completed=true")
        assert r.status_code == 200
        assert len(r.json()) == 1

        # 未完了タスクが空になることを確認
        r = e2e_client.get("/api/tasks?completed=false")
        assert r.status_code == 200
        assert len(r.json()) == 0

    def test_empty_tasks_for_new_family(self, e2e_client):
        """データなしのファミリーは空リストを返す"""
        e2e_client.get("/api/families/me")
        r = e2e_client.get("/api/tasks")
        assert r.status_code == 200
        assert r.json() == []
