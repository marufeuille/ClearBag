"""
Protocol と runtime_checkable の実例

この例では、Protocolを使って「通知サービス」のインターフェースを定義し、
SlackとLINEの2つの実装を作ります。継承は一切使いません。
"""

from typing import Protocol, runtime_checkable


# ========== Protocol定義 ==========

@runtime_checkable
class Notifier(Protocol):
    """通知サービスのインターフェース（継承不要）"""

    def send_message(self, message: str) -> None:
        """メッセージを送信"""
        ...


# ========== 実装1: Slack（Protocolを知らない） ==========

class SlackNotifier:
    """Slack通知実装 - Notifierを継承していない！"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_message(self, message: str) -> None:
        """Slackにメッセージ送信"""
        print(f"[Slack] Sending to {self.webhook_url}: {message}")
        # 実際はrequests.post(self.webhook_url, json={"text": message})


# ========== 実装2: LINE（Protocolを知らない） ==========

class LineNotifier:
    """LINE通知実装 - これもNotifierを継承していない！"""

    def __init__(self, access_token: str):
        self.access_token = access_token

    def send_message(self, message: str) -> None:
        """LINEにメッセージ送信"""
        print(f"[LINE] Sending with token {self.access_token}: {message}")
        # 実際はLINE Notify APIを呼ぶ


# ========== ビジネスロジック（Protocolに依存） ==========

class AlertSystem:
    """アラートシステム - Notifier Protocolにのみ依存"""

    def __init__(self, notifier: Notifier):
        self._notifier = notifier

    def send_alert(self, message: str) -> None:
        """アラートを送信"""
        self._notifier.send_message(f"🚨 ALERT: {message}")


# ========== 実行例 ==========

if __name__ == "__main__":
    # 1. Slack通知で動作
    slack = SlackNotifier(webhook_url="https://hooks.slack.com/xxx")
    alert_system = AlertSystem(slack)
    alert_system.send_alert("Database connection failed!")

    print()

    # 2. LINE通知に差し替え（コード変更不要！）
    line = LineNotifier(access_token="LINE_TOKEN_123")
    alert_system = AlertSystem(line)
    alert_system.send_alert("Disk space is low!")

    print()

    # 3. 型チェック（runtime_checkableのおかげで可能）
    print("=== Type checks ===")
    print(f"isinstance(slack, Notifier): {isinstance(slack, Notifier)}")
    print(f"isinstance(line, Notifier): {isinstance(line, Notifier)}")

    # 4. シグネチャが合わないクラスは型エラー
    class NotANotifier:
        def different_method(self) -> None:
            pass

    not_notifier = NotANotifier()
    print(f"isinstance(not_notifier, Notifier): {isinstance(not_notifier, Notifier)}")

    # 5. モック例（テストで使う）
    from unittest.mock import MagicMock

    mock_notifier = MagicMock(spec=Notifier)
    alert_system = AlertSystem(mock_notifier)
    alert_system.send_alert("Test alert")
    mock_notifier.send_message.assert_called_once_with("🚨 ALERT: Test alert")
    print("\n✅ Mock test passed!")
