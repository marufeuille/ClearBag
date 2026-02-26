"""既存ユーザーデータをファミリー構造に移行するスクリプト

実行方法:
    # Firestore Emulator で検証する場合
    FIRESTORE_EMULATOR_HOST=localhost:8080 python scripts/migrate_to_families.py --dry-run

    # 本番実行
    python scripts/migrate_to_families.py

処理内容:
  1. users/{uid} ごとに自動で1人ファミリーを作成
  2. users/{uid}/profiles/* → families/{familyId}/profiles/* にコピー
  3. users/{uid}/documents/* → families/{familyId}/documents/* にコピー
  4. documents/{docId}/events/*.user_uid → family_id にフィールド変換
  5. documents/{docId}/tasks/*.user_uid → family_id にフィールド変換
  6. users/{uid} に family_id フィールドを追加
  7. users/{uid} の plan/documents_this_month を families/{familyId} にコピー

注意:
  - 既に family_id が設定されているユーザーはスキップ（冪等）
  - GCS ファイルの移行は別途 migrate_gcs_paths.py を使用（オプション）
"""

from __future__ import annotations

import argparse
import logging
import uuid
from typing import Any

from google.cloud import firestore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_USERS = "users"
_FAMILIES = "families"
_PROFILES = "profiles"
_DOCUMENTS = "documents"
_EVENTS = "events"
_TASKS = "tasks"
_MEMBERS = "members"


def migrate_user(
    db: firestore.Client, uid: str, user_data: dict, dry_run: bool
) -> str | None:
    """
    1ユーザーをファミリー構造に移行する。

    Returns:
        作成/既存のファミリーID。スキップ時はNone。
    """
    # 既に family_id が設定済みの場合はスキップ
    if user_data.get("family_id"):
        logger.info("SKIP uid=%s (already has family_id=%s)", uid, user_data["family_id"])
        return None

    family_id = str(uuid.uuid4())
    email = user_data.get("email", "")
    display_name = user_data.get("display_name", email or uid)
    plan = user_data.get("plan", "free")
    documents_this_month = user_data.get("documents_this_month", 0)

    logger.info(
        "MIGRATE uid=%s → family_id=%s (dry_run=%s)", uid, family_id, dry_run
    )

    if dry_run:
        # プロファイル数とドキュメント数を確認
        profiles = list(
            db.collection(_USERS).document(uid).collection(_PROFILES).stream()
        )
        documents = list(
            db.collection(_USERS).document(uid).collection(_DOCUMENTS).stream()
        )
        logger.info(
            "  Would migrate: %d profiles, %d documents", len(profiles), len(documents)
        )
        return family_id

    batch = db.batch()

    # ── ファミリー作成 ──────────────────────────────────────────────────────
    family_ref = db.collection(_FAMILIES).document(family_id)
    batch.set(
        family_ref,
        {
            "owner_uid": uid,
            "name": "マイファミリー",
            "plan": plan,
            "documents_this_month": documents_this_month,
            "created_at": firestore.SERVER_TIMESTAMP,
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
    )

    # ── メンバー追加 ────────────────────────────────────────────────────────
    member_ref = family_ref.collection(_MEMBERS).document(uid)
    batch.set(
        member_ref,
        {
            "role": "owner",
            "display_name": display_name,
            "email": email,
            "joined_at": firestore.SERVER_TIMESTAMP,
        },
    )

    # ── users/{uid} に family_id を書き込み ────────────────────────────────
    user_ref = db.collection(_USERS).document(uid)
    batch.update(user_ref, {"family_id": family_id})

    batch.commit()
    logger.info("  Created family and member")

    # ── プロファイル移行 ────────────────────────────────────────────────────
    _migrate_subcollection(
        db,
        src_path=f"{_USERS}/{uid}/{_PROFILES}",
        dst_path=f"{_FAMILIES}/{family_id}/{_PROFILES}",
    )

    # ── ドキュメント移行 ────────────────────────────────────────────────────
    _migrate_documents(db, uid=uid, family_id=family_id)

    return family_id


def _migrate_subcollection(
    db: firestore.Client, src_path: str, dst_path: str
) -> int:
    """
    サブコレクション全体をコピーする。

    Returns:
        コピーしたドキュメント数
    """
    parts = src_path.split("/")
    src_ref = db
    for i, part in enumerate(parts):
        if i % 2 == 0:
            src_ref = src_ref.collection(part)
        else:
            src_ref = src_ref.document(part)

    snaps = list(src_ref.stream())
    if not snaps:
        return 0

    dst_parts = dst_path.split("/")
    dst_col = db
    for i, part in enumerate(dst_parts):
        if i % 2 == 0:
            dst_col = dst_col.collection(part)
        else:
            dst_col = dst_col.document(part)

    batch = db.batch()
    count = 0
    for snap in snaps:
        data = snap.to_dict() or {}
        dst_ref = dst_col.document(snap.id)
        batch.set(dst_ref, data)
        count += 1
        # Firestore バッチの上限（500）に達したらコミット
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()

    if count % 400 != 0:
        batch.commit()

    logger.info("  Copied %d docs: %s → %s", count, src_path, dst_path)
    return count


def _migrate_documents(
    db: firestore.Client, uid: str, family_id: str
) -> None:
    """
    ドキュメントとそのサブコレクション（events, tasks）を移行する。
    user_uid フィールドを family_id に変換する。
    """
    docs_src = db.collection(_USERS).document(uid).collection(_DOCUMENTS)
    docs_dst = db.collection(_FAMILIES).document(family_id).collection(_DOCUMENTS)

    for doc_snap in docs_src.stream():
        doc_data = doc_snap.to_dict() or {}
        doc_id = doc_snap.id

        # ドキュメント本体をコピー
        docs_dst.document(doc_id).set(doc_data)

        # events サブコレクションを移行（user_uid → family_id）
        _migrate_events_or_tasks(
            db,
            src_col=docs_src.document(doc_id).collection(_EVENTS),
            dst_col=docs_dst.document(doc_id).collection(_EVENTS),
            family_id=family_id,
        )

        # tasks サブコレクションを移行（user_uid → family_id）
        _migrate_events_or_tasks(
            db,
            src_col=docs_src.document(doc_id).collection(_TASKS),
            dst_col=docs_dst.document(doc_id).collection(_TASKS),
            family_id=family_id,
        )

    # 移行したドキュメント数をログ出力
    doc_count = sum(1 for _ in docs_dst.stream())
    logger.info("  Migrated %d documents to family_id=%s", doc_count, family_id)


def _migrate_events_or_tasks(
    db: firestore.Client,
    src_col: Any,
    dst_col: Any,
    family_id: str,
) -> None:
    """events または tasks サブコレクションを移行し、user_uid → family_id に変換"""
    batch = db.batch()
    count = 0
    for snap in src_col.stream():
        data = snap.to_dict() or {}
        # user_uid フィールドを family_id に変換
        if "user_uid" in data:
            data["family_id"] = family_id
            del data["user_uid"]
        dst_col.document(snap.id).set(data)
        batch.set(dst_col.document(snap.id), data)
        count += 1
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
    if count % 400 != 0 and count > 0:
        batch.commit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate existing users to family structure"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run without making any changes (preview only)",
    )
    parser.add_argument(
        "--uid",
        type=str,
        default=None,
        help="Migrate only this specific uid (optional)",
    )
    args = parser.parse_args()

    db = firestore.Client()

    if args.uid:
        # 特定ユーザーのみ移行
        snap = db.collection(_USERS).document(args.uid).get()
        if not snap.exists:
            logger.error("User not found: uid=%s", args.uid)
            return
        migrate_user(db, args.uid, snap.to_dict() or {}, dry_run=args.dry_run)
    else:
        # 全ユーザーを移行
        users = list(db.collection(_USERS).stream())
        logger.info("Found %d users to migrate", len(users))

        migrated = 0
        skipped = 0
        errors = 0

        for user_snap in users:
            uid = user_snap.id
            try:
                result = migrate_user(
                    db, uid, user_snap.to_dict() or {}, dry_run=args.dry_run
                )
                if result:
                    migrated += 1
                else:
                    skipped += 1
            except Exception:
                logger.exception("Migration failed for uid=%s", uid)
                errors += 1

        logger.info(
            "Migration complete: migrated=%d, skipped=%d, errors=%d",
            migrated,
            skipped,
            errors,
        )

    if args.dry_run:
        logger.info("DRY RUN: No changes were made")


if __name__ == "__main__":
    main()
