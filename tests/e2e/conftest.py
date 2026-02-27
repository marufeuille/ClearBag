"""E2E テスト用フィクスチャ

Firestore Emulator に接続し、実際の Repository を使ってテストする。
Firebase Auth は dependency_overrides でバイパスする。

前提: FIRESTORE_EMULATOR_HOST 環境変数が設定されていること
  例: FIRESTORE_EMULATOR_HOST=localhost:8080 uv run pytest tests/e2e/ -m e2e -v
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from google.cloud import firestore
from v2.entrypoints.api import deps
from v2.entrypoints.api.app import app
from v2.entrypoints.api.deps import AuthInfo

# test_v2_full_pipeline.py はモジュールレベルで実際の API を呼ぶため、
# E2E テスト実行時のコレクション対象から除外する
collect_ignore = ["test_v2_full_pipeline.py"]

# テスト用固定値
TEST_UID = "e2e-test-user"
TEST_UID_2 = "e2e-test-user-2"


@pytest.fixture(scope="session")
def firestore_client():
    """Firestore Emulator に接続するクライアント（セッション共有）。

    FIRESTORE_EMULATOR_HOST が未設定の場合は localhost:8080 をデフォルトとして使用する。
    エミュレーターが起動していない場合はテストが接続エラーで失敗する。
    """
    host = os.environ.get("FIRESTORE_EMULATOR_HOST", "localhost:8080")
    os.environ["FIRESTORE_EMULATOR_HOST"] = host
    return firestore.Client(project="test-project")


@pytest.fixture(autouse=True)
def _cleanup_firestore(request, firestore_client):
    """各テスト後に Emulator のデータをクリーンアップ。

    e2e マーク付きテストのみに適用する（test_v2_full_pipeline.py 等への副作用を防ぐ）。
    """
    yield
    if not request.node.get_closest_marker("e2e"):
        return
    for collection_name in ["families", "users"]:
        for doc in firestore_client.collection(collection_name).stream():
            _delete_document_recursive(firestore_client, doc.reference)


def _delete_document_recursive(client: firestore.Client, doc_ref) -> None:
    """ドキュメントとサブコレクションを再帰的に削除"""
    for subcol in doc_ref.collections():
        for doc in subcol.stream():
            _delete_document_recursive(client, doc.reference)
    doc_ref.delete()


@pytest.fixture
def e2e_client(firestore_client):
    """認証バイパス + 実 Firestore の TestClient。

    - get_auth_info: AuthInfo(TEST_UID) を固定返却（Firebase Auth をバイパス）
    - get_blob_storage: MagicMock（GCS を使わない）
    - get_task_queue: None（BackgroundTasks で代替）
    - Firestore: Emulator に接続した実 Client を使用
    - TEST_UID に is_activated: True を事前設定（アクティベーションチェックを通過）
    """
    deps._firestore_client = firestore_client

    # TEST_UID をアクティベート済みにする（is_activated チェックを通過させる）
    firestore_client.collection("users").document(TEST_UID).set(
        {"is_activated": True}, merge=True
    )

    mock_blob = MagicMock()
    mock_blob.upload.return_value = "uploads/test.pdf"

    app.dependency_overrides[deps.get_auth_info] = lambda: AuthInfo(
        uid=TEST_UID, email="e2e@example.com", display_name="E2E Test User"
    )
    app.dependency_overrides[deps.get_blob_storage] = lambda: mock_blob
    app.dependency_overrides[deps.get_task_queue] = lambda: None

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    deps._firestore_client = None
