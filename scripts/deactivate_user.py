"""ユーザーを停止するスクリプト

users/{uid} に is_activated: False を set(merge=True) で書き込む。
停止したユーザーは次の API 呼び出しで 403 ACTIVATION_REQUIRED を受ける。

実行方法:
    # メールアドレスで指定
    PROJECT_ID=clearbag-dev uv run python scripts/deactivate_user.py --email user@example.com

    # UID で指定
    PROJECT_ID=clearbag-dev uv run python scripts/deactivate_user.py --uid <uid>

    # dry-run（変更なしで確認）
    PROJECT_ID=clearbag-dev uv run python scripts/deactivate_user.py --email user@example.com --dry-run
"""

from __future__ import annotations

import argparse
import logging
import os

import firebase_admin
from firebase_admin import auth as fb_auth
from firebase_admin import credentials as fb_creds
from google.cloud import firestore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_USERS = "users"


def _init_firebase() -> None:
    """Firebase Admin SDK を初期化（未初期化の場合のみ）。"""
    if not firebase_admin._apps:
        project_id = os.environ.get("PROJECT_ID")
        cred = fb_creds.ApplicationDefault()
        firebase_admin.initialize_app(
            cred,
            options={"projectId": project_id} if project_id else {},
        )


def resolve_uid_by_email(email: str) -> str:
    """Firebase Auth でメールアドレスから UID を取得する。"""
    _init_firebase()
    try:
        user = fb_auth.get_user_by_email(email)
        logger.info("Resolved uid=%s for email=%s", user.uid, email)
        return user.uid
    except fb_auth.UserNotFoundError as err:
        raise SystemExit(f"Firebase Auth にユーザーが見つかりません: {email}") from err


def deactivate_user(
    db: firestore.Client, uid: str, user_data: dict, dry_run: bool
) -> bool:
    """
    1ユーザーの is_activated を False にする。

    Returns:
        True: 更新を行った場合（または dry_run で更新予定）
        False: スキップ（既に停止済みまたは未アクティベート）
    """
    if not user_data.get("is_activated"):
        logger.info("SKIP uid=%s (already inactive or not activated)", uid)
        return False

    logger.info("DEACTIVATE uid=%s (dry_run=%s)", uid, dry_run)

    if not dry_run:
        db.collection(_USERS).document(uid).set({"is_activated": False}, merge=True)

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deactivate a user (set is_activated: False)"
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
        help="Deactivate only this specific uid",
    )
    parser.add_argument(
        "--email",
        type=str,
        default=None,
        help="Firebase Auth のメールアドレスで UID を解決して停止",
    )
    args = parser.parse_args()

    if args.uid and args.email:
        raise SystemExit("--uid と --email は同時に指定できません")

    if not args.uid and not args.email:
        raise SystemExit("--uid または --email のいずれかを指定してください")

    project_id = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    db = firestore.Client(project=project_id)
    logger.info("Firestore client initialized project=%s", project_id)

    if args.email:
        uid = resolve_uid_by_email(args.email)
        snap = db.collection(_USERS).document(uid).get()
        deactivate_user(db, uid, snap.to_dict() or {}, dry_run=args.dry_run)
    else:
        snap = db.collection(_USERS).document(args.uid).get()
        if not snap.exists:
            logger.error("User not found: uid=%s", args.uid)
            return
        deactivate_user(db, args.uid, snap.to_dict() or {}, dry_run=args.dry_run)

    if args.dry_run:
        logger.info("DRY RUN: No changes were made")


if __name__ == "__main__":
    main()
