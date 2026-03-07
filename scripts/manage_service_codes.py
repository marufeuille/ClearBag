"""サービス招待コード管理スクリプト

list サブコマンド: 全コードの一覧を表示
revoke サブコマンド: 指定コードを即時無効化（expires_at を過去日時に設定）

実行方法:
    # 一覧表示
    PROJECT_ID=clearbag-dev uv run python scripts/manage_service_codes.py list

    # コードを無効化
    PROJECT_ID=clearbag-dev uv run python scripts/manage_service_codes.py revoke A3kX9mP2

    # dry-run で確認
    PROJECT_ID=clearbag-dev uv run python scripts/manage_service_codes.py revoke A3kX9mP2 --dry-run
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os

import firebase_admin
from firebase_admin import credentials as fb_creds
from google.cloud import firestore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_SERVICE_CODES = "service_codes"
_JST = datetime.timezone(datetime.timedelta(hours=9))


def _init_firebase() -> None:
    if not firebase_admin._apps:
        project_id = os.environ.get("PROJECT_ID")
        cred = fb_creds.ApplicationDefault()
        firebase_admin.initialize_app(
            cred,
            options={"projectId": project_id} if project_id else {},
        )


def _compute_status(data: dict, now: datetime.datetime) -> str:
    expires_at = data.get("expires_at")
    if expires_at and expires_at <= now:
        return "expired"
    max_uses = data.get("max_uses")
    used_count = data.get("used_count", 0)
    if max_uses is not None and used_count >= max_uses:
        return "exhausted"
    return "active"


def list_codes(db: firestore.Client) -> None:
    """service_codes コレクションの全件を表形式で出力する。"""
    now = datetime.datetime.now(datetime.UTC)
    docs = list(db.collection(_SERVICE_CODES).stream())

    headers = ["CODE", "DESCRIPTION", "USED", "MAX", "REMAINING", "EXPIRES", "STATUS"]
    rows: list[list[str]] = []

    for doc in docs:
        data = doc.to_dict() or {}
        max_uses = data.get("max_uses")
        used_count = data.get("used_count", 0)
        expires_at = data.get("expires_at")

        max_str = str(max_uses) if max_uses is not None else "\u221e"
        remaining_str = str(max_uses - used_count) if max_uses is not None else "\u221e"
        expires_str = (
            expires_at.astimezone(_JST).strftime("%Y-%m-%d %H:%M")
            if expires_at
            else "-"
        )
        status = _compute_status(data, now)

        rows.append(
            [
                doc.id,
                data.get("description", ""),
                str(used_count),
                max_str,
                remaining_str,
                expires_str,
                status,
            ]
        )

    if not rows:
        print("No service codes found.")
        return

    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in col_widths]))
    for row in rows:
        print(fmt.format(*row))


def revoke_code(db: firestore.Client, code: str, *, dry_run: bool) -> None:
    """指定コードの expires_at を過去日時に設定して無効化する。"""
    doc_ref = db.collection(_SERVICE_CODES).document(code)
    snap = doc_ref.get()
    if not snap.exists:
        raise SystemExit(f"Code '{code}' not found.")

    past = datetime.datetime.now(datetime.UTC) - datetime.timedelta(seconds=1)
    logger.info(
        "REVOKE code=%s expires_at -> %s (dry_run=%s)", code, past.isoformat(), dry_run
    )

    if not dry_run:
        doc_ref.update({"expires_at": past})

    if dry_run:
        logger.info("DRY RUN: No changes were made")


def main() -> None:
    parser = argparse.ArgumentParser(description="ClearBag サービス招待コード管理")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="全コードの一覧を表示")

    revoke_parser = subparsers.add_parser("revoke", help="指定コードを即時無効化")
    revoke_parser.add_argument("code", type=str, help="無効化するコード文字列")
    revoke_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="変更なしでプレビューのみ",
    )

    args = parser.parse_args()

    _init_firebase()

    project_id = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    db = firestore.Client(project=project_id)
    logger.info("Firestore client initialized project=%s", project_id)

    if args.command == "list":
        list_codes(db)
    elif args.command == "revoke":
        revoke_code(db, args.code, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
