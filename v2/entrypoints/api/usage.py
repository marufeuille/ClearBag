"""月間利用枚数の Lazy Reset ヘルパー

アクセス時に last_reset_at を確認し、月が変わっていれば
documents_this_month を 0 にリセットする。
Cloud Scheduler 不要でリセット処理を実現する。
"""

from __future__ import annotations

import datetime
import logging

logger = logging.getLogger(__name__)


def ensure_monthly_reset(
    family_repo: object,
    family_id: str,
    family: dict,
    _now: datetime.datetime | None = None,
) -> dict:
    """月が変わっていれば documents_this_month を 0 にリセットする（Lazy Reset）。

    - last_reset_at が None / 未存在: 現在時刻で初期化するがカウントはリセットしない
      （月途中のデプロイで既存ユーザーが不公平にならないため）
    - last_reset_at の year-month が現在と異なる: カウンターを 0 にリセット + last_reset_at 更新
    - 同月内: 何もしない

    Args:
        family_repo: update_family メソッドを持つリポジトリ
        family_id: ファミリー ID
        family: get_family() の戻り値 dict
        _now: テスト用の固定日時（None の場合は現在時刻を使用）

    Returns:
        リセット後の family dict（呼び出し元は必ず戻り値を使用すること）
    """
    now = _now or datetime.datetime.now(datetime.UTC)
    last_reset_at = family.get("last_reset_at")

    if last_reset_at is None:
        # 初回 or 既存データ: last_reset_at を設定するだけでカウントはリセットしない
        family_repo.update_family(family_id, {"last_reset_at": now})  # type: ignore[attr-defined]
        logger.info("Initialized last_reset_at: family_id=%s", family_id)
        return {**family, "last_reset_at": now}

    # Firestore Timestamp が timezone-naive で返る場合は UTC とみなす
    if hasattr(last_reset_at, "tzinfo") and last_reset_at.tzinfo is None:
        last_reset_at = last_reset_at.replace(tzinfo=datetime.UTC)

    if (last_reset_at.year, last_reset_at.month) != (now.year, now.month):
        # 月が変わった: カウンターをリセット
        family_repo.update_family(  # type: ignore[attr-defined]
            family_id,
            {"documents_this_month": 0, "last_reset_at": now},
        )
        logger.info(
            "Monthly reset: family_id=%s, %d-%02d → %d-%02d",
            family_id,
            last_reset_at.year,
            last_reset_at.month,
            now.year,
            now.month,
        )
        return {**family, "documents_this_month": 0, "last_reset_at": now}

    return family
