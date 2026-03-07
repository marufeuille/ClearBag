"""Dev環境のデータクリーンアップ＋デモデータシードスクリプト

dev環境（clearbag-dev）の Firestore + GCS データを全削除し、
手動テストに必要なデモデータをシードする。

安全策: PROJECT_ID が "clearbag-dev" 以外の場合は即座に終了する（prod誤実行防止）。

実行方法:
    # dry-run で対象件数のみ確認
    PROJECT_ID=clearbag-dev uv run python scripts/reset_dev_data.py --email user@example.com --dry-run

    # 本実行（クリーンアップ + デモデータシード）
    PROJECT_ID=clearbag-dev GCS_BUCKET_NAME=clearbag-dev-clearbag-uploads-dev \\
        uv run python scripts/reset_dev_data.py --email user@example.com

    # クリーンアップのみ（デモデータシードなし）
    PROJECT_ID=clearbag-dev GCS_BUCKET_NAME=clearbag-dev-clearbag-uploads-dev \\
        uv run python scripts/reset_dev_data.py --email user@example.com --cleanup-only

    # Firestore クリーンアップのみ（GCS クリーンアップをスキップ、PDF アップロードは GCS_BUCKET_NAME 次第）
    PROJECT_ID=clearbag-dev uv run python scripts/reset_dev_data.py \\
        --email user@example.com --skip-gcs
"""

from __future__ import annotations

import argparse
import logging
import os
import uuid
from datetime import UTC, datetime, timedelta

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials as fb_creds
from google.cloud import firestore, storage

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_ALLOWED_PROJECT_ID = "clearbag-dev"
_FAMILIES = "families"
_USERS = "users"
_MEMBERS = "members"
_PROFILES = "profiles"
_DOCUMENTS = "documents"
_EVENTS = "events"
_TASKS = "tasks"


def _guard_project_id(project_id: str | None) -> str:
    """clearbag-dev 以外の PROJECT_ID では即座に終了する（prod誤実行防止）。"""
    if project_id != _ALLOWED_PROJECT_ID:
        raise SystemExit(
            f"このスクリプトは {_ALLOWED_PROJECT_ID} 環境専用です。"
            f" PROJECT_ID={project_id!r} では実行できません。"
        )
    return project_id


def _init_firebase(project_id: str) -> None:
    """Firebase Admin SDK を初期化（未初期化の場合のみ）。"""
    if not firebase_admin._apps:
        cred = fb_creds.ApplicationDefault()
        firebase_admin.initialize_app(
            cred,
            options={"projectId": project_id},
        )


def resolve_uid_by_email(email: str) -> str:
    """Firebase Auth でメールアドレスから UID を取得する。"""
    try:
        user = fb_auth.get_user_by_email(email)
        logger.info("Resolved uid=%s for email=%s", user.uid, email)
        return user.uid
    except fb_auth.UserNotFoundError:
        raise SystemExit(f"Firebase Auth にユーザーが見つかりません: {email}") from None


def _delete_document_recursive(
    client: firestore.Client, doc_ref: firestore.DocumentReference
) -> None:
    """ドキュメントとサブコレクションを再帰的に削除する。"""
    for subcol in doc_ref.collections():
        for doc in subcol.stream():
            _delete_document_recursive(client, doc.reference)
    doc_ref.delete()


def cleanup_firestore(db: firestore.Client, dry_run: bool) -> None:
    """families + users コレクションを再帰削除する。"""
    for collection_name in [_FAMILIES, _USERS]:
        docs = list(db.collection(collection_name).stream())
        logger.info(
            "Firestore cleanup: collection=%s, count=%d (dry_run=%s)",
            collection_name,
            len(docs),
            dry_run,
        )
        if not dry_run:
            for doc in docs:
                _delete_document_recursive(db, doc.reference)


def cleanup_gcs(bucket_name: str, dry_run: bool) -> None:
    """GCS バケットの uploads/ 配下を全削除する。"""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix="uploads/"))
    logger.info(
        "GCS cleanup: bucket=%s, count=%d (dry_run=%s)",
        bucket_name,
        len(blobs),
        dry_run,
    )
    if not dry_run:
        for blob in blobs:
            blob.delete()
            logger.debug("Deleted GCS object: %s", blob.name)


def _minimal_pdf(title: str) -> bytes:
    """シード用の最小限 PDF を生成する。

    xref テーブルのバイトオフセットを動的計算するため、常に有効な PDF 構造を返す。
    タイトルは UTF-16-BE（BOM付き）でエンコードして /Info 辞書に格納する。
    ページコンテンツは空白（可視テキストなし）。

    Args:
        title: /Title メタデータに埋め込む文字列（日本語可）
    """
    title_hex = (b"\xfe\xff" + title.encode("utf-16-be")).hex().upper()

    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R /Info 4 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
    obj4 = f"4 0 obj\n<< /Title <{title_hex}> >>\nendobj\n".encode()

    header = b"%PDF-1.4\n"
    objects = [obj1, obj2, obj3, obj4]

    offsets: list[int] = []
    body = b""
    for obj in objects:
        offsets.append(len(header) + len(body))
        body += obj

    xref_offset = len(header) + len(body)
    xref = b"xref\n0 5\n" + b"0000000000 65535 f \n"
    for offset in offsets:
        xref += f"{offset:010d} 00000 n \n".encode()

    trailer = (
        b"trailer\n<< /Size 5 /Root 1 0 R /Info 4 0 R >>\n"
        b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF\n"
    )

    return header + body + xref + trailer


def seed_demo_data(
    db: firestore.Client,
    uid: str,
    email: str,
    dry_run: bool,
    bucket_name: str | None = None,
) -> None:
    """デモデータをシードする。

    シード内容:
      - users/{uid}: is_activated, ical_token, family_id
      - families/{familyId}: テストファミリー (plan: free)
      - families/{familyId}/members/{uid}: owner
      - profiles × 1: 太郎（小学3年生）
      - documents × 2 (completed) + events × 2 + tasks × 3
      - documents × 1 (completed, archive_filename=None): 旧スキーマ互換性テスト用
      - documents × 1 (pending): 処理中状態の UI テスト用

    Args:
        bucket_name: GCS バケット名。指定した場合は各ドキュメントの PDF も GCS にアップロードする。
                     未指定の場合は Firestore レコードのみ作成（storage_path は記録される）。
    """
    family_id = str(uuid.uuid4())
    ical_token = str(uuid.uuid4())
    now = datetime.now(UTC)
    date_30d = (now + timedelta(days=30)).strftime("%Y-%m-%d")
    date_29d = (now + timedelta(days=29)).strftime("%Y-%m-%d")
    date_14d = (now + timedelta(days=14)).strftime("%Y-%m-%d")
    date_7d = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    logger.info(
        "Seeding demo data: uid=%s, family_id=%s (dry_run=%s)",
        uid,
        family_id,
        dry_run,
    )

    if dry_run:
        logger.info(
            "DRY RUN: Would create users/%s, families/%s, 1 profile, 4 documents (2 completed + 1 legacy-null + 1 pending), 2 events, 3 tasks%s",
            uid,
            family_id,
            f" + upload PDFs to gs://{bucket_name}" if bucket_name else "",
        )
        return

    gcs_bucket = storage.Client().bucket(bucket_name) if bucket_name else None
    if gcs_bucket:
        logger.info("GCS PDF upload enabled: bucket=%s", bucket_name)
    else:
        logger.info("GCS PDF upload skipped (GCS_BUCKET_NAME not set)")

    # users/{uid}
    db.collection(_USERS).document(uid).set(
        {
            "is_activated": True,
            "ical_token": ical_token,
            "family_id": family_id,
        }
    )
    logger.info("Created users/%s", uid)

    # families/{familyId}
    db.collection(_FAMILIES).document(family_id).set(
        {
            "owner_uid": uid,
            "name": "テストファミリー",
            "plan": "free",
            "documents_this_month": 0,
            "last_reset_at": firestore.SERVER_TIMESTAMP,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    )
    logger.info("Created families/%s", family_id)

    # families/{familyId}/members/{uid}
    db.collection(_FAMILIES).document(family_id).collection(_MEMBERS).document(uid).set(
        {
            "role": "owner",
            "display_name": email.split("@")[0],
            "email": email,
            "joined_at": firestore.SERVER_TIMESTAMP,
        }
    )
    logger.info("Created families/%s/members/%s", family_id, uid)

    # profiles × 1: 太郎（小学3年生）
    profile_ref = (
        db.collection(_FAMILIES).document(family_id).collection(_PROFILES).document()
    )
    profile_ref.set(
        {
            "name": "太郎",
            "grade": "小学3年生",
            "keywords": "サッカー,遠足",
            "created_at": firestore.SERVER_TIMESTAMP,
        }
    )
    logger.info("Created profile: %s", profile_ref.id)

    # documents × 2（正常データ）
    _seed_document_sports_day(db, family_id, uid, date_30d, date_29d, gcs_bucket)
    _seed_document_parent_meeting(db, family_id, uid, date_14d, date_7d, gcs_bucket)

    # documents × 2（互換性テスト用：旧スキーマ・処理中状態）
    _seed_document_legacy_null_archive(db, family_id, uid, gcs_bucket)
    _seed_document_pending(db, family_id, uid, gcs_bucket)

    logger.info("Seed complete: 1 profile, 4 documents (2 completed + 1 legacy-null + 1 pending), 2 events, 3 tasks")


def _seed_document_sports_day(
    db: firestore.Client,
    family_id: str,
    uid: str,
    event_date: str,
    task_date: str,
    gcs_bucket: storage.Bucket | None = None,
) -> None:
    """ドキュメント1: 運動会のおしらせ（イベント×1 + タスク×2）。"""
    title = "運動会のおしらせ"
    doc_id = str(uuid.uuid4())
    storage_path = f"uploads/{uid}/{doc_id}.pdf"

    if gcs_bucket is not None:
        gcs_bucket.blob(storage_path).upload_from_string(
            _minimal_pdf(title), content_type="application/pdf"
        )
        logger.info("Uploaded PDF to GCS: %s", storage_path)

    doc_ref = (
        db.collection(_FAMILIES)
        .document(family_id)
        .collection(_DOCUMENTS)
        .document(doc_id)
    )
    doc_ref.set(
        {
            "uid": uid,
            "status": "completed",
            "content_hash": str(uuid.uuid4()),
            "storage_path": storage_path,
            "original_filename": f"{title}.pdf",
            "mime_type": "application/pdf",
            "summary": "10月の運動会についてのお知らせです。保護者の参加も歓迎します。",
            "category": "EVENT",
            "archive_filename": f"{title}.pdf",
            "error_message": None,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    )

    doc_ref.collection(_EVENTS).document().set(
        {
            "family_id": family_id,
            "document_id": doc_id,
            "summary": "運動会",
            "start": f"{event_date}T09:00:00",
            "end": f"{event_date}T15:00:00",
            "location": "校庭",
            "description": "",
            "confidence": "HIGH",
        }
    )
    doc_ref.collection(_TASKS).document().set(
        {
            "family_id": family_id,
            "document_id": doc_id,
            "title": "お弁当の持ち物確認",
            "due_date": task_date,
            "assignee": "PARENT",
            "note": "",
            "completed": False,
        }
    )
    doc_ref.collection(_TASKS).document().set(
        {
            "family_id": family_id,
            "document_id": doc_id,
            "title": "体操着の準備",
            "due_date": task_date,
            "assignee": "CHILD",
            "note": "",
            "completed": False,
        }
    )
    logger.info("Created document: %s (doc_id=%s)", title, doc_id)


def _seed_document_parent_meeting(
    db: firestore.Client,
    family_id: str,
    uid: str,
    event_date: str,
    task_date: str,
    gcs_bucket: storage.Bucket | None = None,
) -> None:
    """ドキュメント2: 保護者会のご案内（イベント×1 + タスク×1）。"""
    title = "保護者会のご案内"
    doc_id = str(uuid.uuid4())
    storage_path = f"uploads/{uid}/{doc_id}.pdf"

    if gcs_bucket is not None:
        gcs_bucket.blob(storage_path).upload_from_string(
            _minimal_pdf(title), content_type="application/pdf"
        )
        logger.info("Uploaded PDF to GCS: %s", storage_path)

    doc_ref = (
        db.collection(_FAMILIES)
        .document(family_id)
        .collection(_DOCUMENTS)
        .document(doc_id)
    )
    doc_ref.set(
        {
            "uid": uid,
            "status": "completed",
            "content_hash": str(uuid.uuid4()),
            "storage_path": storage_path,
            "original_filename": f"{title}.pdf",
            "mime_type": "application/pdf",
            "summary": "今学期の保護者会を開催します。出欠票を提出してください。",
            "category": "EVENT",
            "archive_filename": f"{title}.pdf",
            "error_message": None,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    )

    doc_ref.collection(_EVENTS).document().set(
        {
            "family_id": family_id,
            "document_id": doc_id,
            "summary": "保護者会",
            "start": f"{event_date}T14:00:00",
            "end": f"{event_date}T16:00:00",
            "location": "体育館",
            "description": "",
            "confidence": "HIGH",
        }
    )
    doc_ref.collection(_TASKS).document().set(
        {
            "family_id": family_id,
            "document_id": doc_id,
            "title": "出欠票の提出",
            "due_date": task_date,
            "assignee": "PARENT",
            "note": "",
            "completed": False,
        }
    )
    logger.info("Created document: %s (doc_id=%s)", title, doc_id)


def _seed_document_legacy_null_archive(
    db: firestore.Client,
    family_id: str,
    uid: str,
    gcs_bucket: storage.Bucket | None = None,
) -> None:
    """ドキュメント3: archive_filename が null の旧形式データ（互換性テスト用）。

    archive_filename フィールドが導入される前に解析が完了したドキュメントを模倣する。
    Firestore に archive_filename: null が保存されている状態で GET /api/documents が
    500 にならないことを検証するためのシードデータ。
    """
    title = "給食だより"
    doc_id = str(uuid.uuid4())
    storage_path = f"uploads/{uid}/{doc_id}.pdf"

    if gcs_bucket is not None:
        gcs_bucket.blob(storage_path).upload_from_string(
            _minimal_pdf(title), content_type="application/pdf"
        )
        logger.info("Uploaded PDF to GCS: %s", storage_path)

    doc_ref = (
        db.collection(_FAMILIES)
        .document(family_id)
        .collection(_DOCUMENTS)
        .document(doc_id)
    )
    doc_ref.set(
        {
            "uid": uid,
            "status": "completed",
            "content_hash": str(uuid.uuid4()),
            "storage_path": storage_path,
            "original_filename": f"{title}.pdf",
            "mime_type": "application/pdf",
            "summary": "今月の給食の献立です。アレルギー対応の案内も含まれています。",
            "category": "INFO",
            "archive_filename": None,  # 旧スキーマ: archive_filename 導入前のデータを模倣
            "error_message": None,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    )
    logger.info(
        "Created legacy document (archive_filename=None): %s (doc_id=%s)", title, doc_id
    )


def _seed_document_pending(
    db: firestore.Client,
    family_id: str,
    uid: str,
    gcs_bucket: storage.Bucket | None = None,
) -> None:
    """ドキュメント4: 解析待ち（status=pending）のドキュメント（UI表示テスト用）。

    アップロード直後で AI 解析がまだ完了していない状態を模倣する。
    summary / category / archive_filename が空文字の状態でも一覧表示がクラッシュしないことを検証する。
    """
    title = "学年だより"
    doc_id = str(uuid.uuid4())
    storage_path = f"uploads/{uid}/{doc_id}.pdf"

    if gcs_bucket is not None:
        gcs_bucket.blob(storage_path).upload_from_string(
            _minimal_pdf(title), content_type="application/pdf"
        )
        logger.info("Uploaded PDF to GCS: %s", storage_path)

    doc_ref = (
        db.collection(_FAMILIES)
        .document(family_id)
        .collection(_DOCUMENTS)
        .document(doc_id)
    )
    doc_ref.set(
        {
            "uid": uid,
            "status": "pending",
            "content_hash": str(uuid.uuid4()),
            "storage_path": storage_path,
            "original_filename": f"{title}.pdf",
            "mime_type": "application/pdf",
            "summary": "",
            "category": "",
            "archive_filename": "",
            "error_message": None,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        }
    )
    logger.info("Created pending document: %s (doc_id=%s)", title, doc_id)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dev環境のデータをクリーンアップしてデモデータをシードする"
    )
    parser.add_argument(
        "--email",
        type=str,
        required=True,
        help="デモデータを紐づける Firebase Auth ユーザーのメールアドレス",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="削除・シード対象の件数のみ表示し、実データ操作なし",
    )
    parser.add_argument(
        "--skip-gcs",
        action="store_true",
        help="GCS クリーンアップをスキップ（Firestore のみ）",
    )
    parser.add_argument(
        "--cleanup-only",
        action="store_true",
        help="デモデータシードを行わず、クリーンアップのみ実行",
    )
    args = parser.parse_args()

    project_id = os.environ.get("PROJECT_ID")
    _guard_project_id(project_id)

    _init_firebase(project_id)  # type: ignore[arg-type]
    uid = resolve_uid_by_email(args.email)

    db = firestore.Client(project=project_id)
    logger.info("Firestore client initialized: project=%s", project_id)

    cleanup_firestore(db, dry_run=args.dry_run)

    if not args.skip_gcs:
        bucket_name = os.environ.get("GCS_BUCKET_NAME")
        if not bucket_name:
            raise SystemExit(
                "GCS_BUCKET_NAME 環境変数が設定されていません。"
                " --skip-gcs を使うか GCS_BUCKET_NAME を設定してください。"
            )
        cleanup_gcs(bucket_name, dry_run=args.dry_run)
    else:
        logger.info("GCS cleanup skipped (--skip-gcs)")

    if args.cleanup_only:
        logger.info("Seed skipped (--cleanup-only)")
    else:
        seed_demo_data(
            db,
            uid,
            args.email,
            dry_run=args.dry_run,
            bucket_name=os.environ.get("GCS_BUCKET_NAME"),
        )

    if args.dry_run:
        logger.info("DRY RUN: No changes were made")
    else:
        logger.info("Done: dev environment reset complete")


if __name__ == "__main__":
    main()
