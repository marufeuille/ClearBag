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
    ) -> None:
        """
        Web Push 通知を送信。

        Args:
            subscription: ブラウザの Push サブスクリプション
            title: 通知タイトル
            body: 通知本文
            url: タップ時に開く URL（相対パス）

        Raises:
            WebPushException: 送信に失敗した場合
        """
        payload = json.dumps({"title": title, "body": body, "url": url})

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
        )
