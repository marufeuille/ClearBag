"""サービス招待コード生成スクリプト

Firestore の service_codes/{code} にドキュメントを作成する。
生成されたコードを含む招待URLを標準出力に表示する。

実行方法:
    PROJECT_ID=clearbag-dev uv run python scripts/create_service_code.py \\
        --expires-in-days 30 \\
        --max-uses 50 \\
        --description "友人招待用"

    # コードを手動指定する場合
    PROJECT_ID=clearbag-dev uv run python scripts/create_service_code.py \\
        --code SPRING2026 --expires-in-days 7

    # 無制限コードを作成する場合（max-uses 省略）
    PROJECT_ID=clearbag-dev uv run python scripts/create_service_code.py \\
        --expires-in-days 14
"""

from __future__ import annotations

import argparse
import datetime
import logging
import os
import random
import string

import firebase_admin
from firebase_admin import credentials as fb_creds
from google.cloud import firestore

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_SERVICE_CODES = "service_codes"
_DEFAULT_FRONTEND_URL = "https://clearbag.web.app"


def _init_firebase() -> None:
    if not firebase_admin._apps:
        project_id = os.environ.get("PROJECT_ID")
        cred = fb_creds.ApplicationDefault()
        firebase_admin.initialize_app(
            cred,
            options={"projectId": project_id} if project_id else {},
        )


def _generate_code(length: int = 8) -> str:
    """ランダムな英大文字+数字のコードを生成する。"""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def create_service_code(
    db: firestore.Client,
    code: str,
    expires_at: datetime.datetime,
    max_uses: int | None,
    description: str,
    created_by: str,
) -> None:
    """service_codes/{code} にドキュメントを作成する。"""
    doc_ref = db.collection(_SERVICE_CODES).document(code)
    if doc_ref.get().exists:
        raise SystemExit(f"コード '{code}' は既に存在します。別のコードを指定してください。")

    data: dict = {
        "created_by": created_by,
        "expires_at": expires_at,
        "max_uses": max_uses,
        "used_count": 0,
        "description": description,
        "created_at": datetime.datetime.now(datetime.UTC),
    }
    doc_ref.set(data)
    logger.info("Created service code: %s", code)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ClearBag サービス招待コードを生成する"
    )
    parser.add_argument(
        "--code",
        type=str,
        default=None,
        help="招待コード文字列（省略時はランダム8文字英数字を自動生成）",
    )
    parser.add_argument(
        "--expires-in-days",
        type=int,
        required=True,
        help="有効期限（日数）",
    )
    parser.add_argument(
        "--max-uses",
        type=int,
        default=None,
        help="利用上限回数（省略時は無制限）",
    )
    parser.add_argument(
        "--description",
        type=str,
        default="",
        help="コードの説明（メモ用）",
    )
    parser.add_argument(
        "--created-by",
        type=str,
        default="admin",
        help="作成者情報（メモ用）",
    )
    parser.add_argument(
        "--frontend-url",
        type=str,
        default=_DEFAULT_FRONTEND_URL,
        help=f"フロントエンドURL（デフォルト: {_DEFAULT_FRONTEND_URL}）",
    )
    args = parser.parse_args()

    _init_firebase()

    project_id = os.environ.get("PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    db = firestore.Client(project=project_id)
    logger.info("Firestore client initialized project=%s", project_id)

    code = args.code or _generate_code()
    expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
        days=args.expires_in_days
    )

    create_service_code(
        db=db,
        code=code,
        expires_at=expires_at,
        max_uses=args.max_uses,
        description=args.description,
        created_by=args.created_by,
    )

    invite_url = f"{args.frontend_url}/register?code={code}"
    max_uses_str = str(args.max_uses) if args.max_uses is not None else "無制限"
    expires_jst = expires_at.astimezone(datetime.timezone(datetime.timedelta(hours=9)))

    print(f"\nCreated service code: {code}")
    print(f"Invite URL: {invite_url}")
    print(f"Expires: {expires_jst.isoformat()}")
    print(f"Max uses: {max_uses_str}")
    if args.description:
        print(f"Description: {args.description}")


if __name__ == "__main__":
    main()
