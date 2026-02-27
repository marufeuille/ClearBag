"""既存ユーザーに is_activated: True を付与するスクリプト

コードデプロイ前に本番 Firestore に対して実行し、既存ユーザーが
アクティベーションチェックでブロックされないようにする。

実行方法:
    # Firestore Emulator で検証する場合
    FIRESTORE_EMULATOR_HOST=localhost:8080 python scripts/activate_existing_users.py --dry-run

    # 本番実行（全ユーザー）
    python scripts/activate_existing_users.py

    # 特定ユーザーのみ
    python scripts/activate_existing_users.py --uid <uid>

処理内容:
    users/{uid} に is_activated: True を set(merge=True) で書き込む。
    既に is_activated: True の場合はスキップ（冪等）。
"""

from __future__ import annotations

import argparse
import logging

from google.cloud import firestore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_USERS = "users"


def activate_user(
    db: firestore.Client, uid: str, user_data: dict, dry_run: bool
) -> bool:
    """
    1ユーザーに is_activated: True を付与する。

    Returns:
        True: 更新を行った場合（または dry_run で更新予定）
        False: スキップ（既にアクティベート済み）
    """
    if user_data.get("is_activated"):
        logger.info("SKIP uid=%s (already activated)", uid)
        return False

    logger.info("ACTIVATE uid=%s (dry_run=%s)", uid, dry_run)

    if not dry_run:
        db.collection(_USERS).document(uid).set(
            {"is_activated": True}, merge=True
        )

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Activate existing users (set is_activated: True)"
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
        help="Activate only this specific uid (optional)",
    )
    args = parser.parse_args()

    db = firestore.Client()

    if args.uid:
        snap = db.collection(_USERS).document(args.uid).get()
        if not snap.exists:
            logger.error("User not found: uid=%s", args.uid)
            return
        activate_user(db, args.uid, snap.to_dict() or {}, dry_run=args.dry_run)
    else:
        users = list(db.collection(_USERS).stream())
        logger.info("Found %d users to process", len(users))

        activated = 0
        skipped = 0
        errors = 0

        for user_snap in users:
            uid = user_snap.id
            try:
                result = activate_user(
                    db, uid, user_snap.to_dict() or {}, dry_run=args.dry_run
                )
                if result:
                    activated += 1
                else:
                    skipped += 1
            except Exception:
                logger.exception("Activation failed for uid=%s", uid)
                errors += 1

        logger.info(
            "Done: activated=%d, skipped=%d, errors=%d",
            activated,
            skipped,
            errors,
        )

    if args.dry_run:
        logger.info("DRY RUN: No changes were made")


if __name__ == "__main__":
    main()
