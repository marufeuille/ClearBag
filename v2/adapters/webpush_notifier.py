"""Web Push Notifier Adapter

pywebpush + VAPID を使った Web Push 通知実装（Phase 3）。
PWA のサービスワーカーと連携してプッシュ通知を送信する。

VAPID (Voluntary Application Server Identification):
- 公開鍵と秘密鍵のペアでアプリサーバーを認証する仕組み
- ブラウザのプッシュサービス（FCM 等）がサーバーを識別できる
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from pywebpush import WebPushException, webpush

logger = logging.getLogger(__name__)


@dataclass
class VapidConfig:
    """VAPID 認証の設定"""

    private_key: str  # VAPID 秘密鍵（PEM 形式）
    public_key: str  # VAPID 公開鍵（Base64url エンコード）
    claims_email: str  # VAPID クレームのメールアドレス


@dataclass
class PushSubscription:
    """ブラウザから受け取った Push サブスクリプション情報"""

    endpoint: str
    keys: dict  # {"auth": "...", "p256dh": "..."}


class WebPushNotifier:
    """
    pywebpush を使った Web Push 通知実装。

    ブラウザが Push Manager で生成したサブスクリプション情報を
    Firestore から取得し、VAPID 認証でプッシュ通知を送信する。
    """

    def __init__(self, vapid: VapidConfig) -> None:
        """
        Args:
            vapid: VAPID キーとクレームの設定
        """
        self._vapid = vapid

    def send(
        self,
        subscription: PushSubscription,
        title: str,
        body: str,
        url: str = "/",
        tag: str | None = None,
    ) -> None:
        """
        Web Push 通知を送信。

        Args:
            subscription: ブラウザの Push サブスクリプション
            title: 通知タイトル
            body: 通知本文
            url: タップ時に開く URL（相対パス）
            tag: 同一 tag の通知を上書きする識別子（重複防止）

        Raises:
            WebPushException: 送信に失敗した場合
        """
        data: dict = {"title": title, "body": body, "url": url}
        if tag is not None:
            data["tag"] = tag
        payload = json.dumps(data)

        try:
            webpush(
                subscription_info={
                    "endpoint": subscription.endpoint,
                    "keys": subscription.keys,
                },
                data=payload,
                vapid_private_key=self._vapid.private_key,
                vapid_claims={
                    "sub": f"mailto:{self._vapid.claims_email}",
                },
            )
            logger.info("Web Push sent: endpoint=%s...", subscription.endpoint[:40])
        except WebPushException as e:
            logger.error(
                "Web Push failed: endpoint=%s..., error=%s",
                subscription.endpoint[:40],
                e,
            )
            raise

    def notify_analysis_complete(
        self,
        subscription: PushSubscription,
        filename: str,
        document_id: str,
    ) -> None:
        """
        解析完了プッシュ通知を送信する。

        Args:
            subscription: 送信先のプッシュサブスクリプション
            filename: 解析したファイル名
            document_id: 解析結果の確認 URL に使うドキュメント ID
        """
        self.send(
            subscription=subscription,
            title="解析完了",
            body=f"「{filename}」の解析が完了しました",
            url=f"/documents/{document_id}",
            tag=f"analysis-complete-{document_id}",
        )

    def notify_morning_digest(
        self,
        subscription: PushSubscription,
        event_count: int,
        task_count: int,
    ) -> None:
        """
        朝のダイジェストプッシュ通知を送信する。

        イベント・タスクが0件の場合は送信をスキップする。

        Args:
            subscription: 送信先のプッシュサブスクリプション
            event_count: 今後7日間のイベント件数
            task_count: 未完了タスク件数
        """
        if event_count == 0 and task_count == 0:
            logger.debug("Morning digest skipped: no events or tasks")
            return

        parts = []
        if event_count > 0:
            parts.append(f"予定 {event_count}件")
        if task_count > 0:
            parts.append(f"タスク {task_count}件")
        body = "今週の " + "、".join(parts) + " があります"

        self.send(
            subscription=subscription,
            title="ClearBag ダイジェスト",
            body=body,
            url="/calendar",
            tag="morning-digest",
        )

    def notify_event_reminder(
        self,
        subscription: PushSubscription,
        events: list,
    ) -> None:
        """
        翌日のイベントリマインダープッシュ通知を送信する。

        Args:
            subscription: 送信先のプッシュサブスクリプション
            events: 翌日のイベントリスト（EventData のリスト）
        """
        count = len(events)
        if count == 0:
            return

        body = f"明日の予定が {count}件 あります"
        self.send(
            subscription=subscription,
            title="明日の予定リマインダー",
            body=body,
            url="/calendar",
            tag="event-reminder",
        )
