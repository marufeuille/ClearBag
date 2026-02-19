"""
ABC版とProtocol版でテストの書き方がどう変わるかの比較
"""

from abc import ABC, abstractmethod
from typing import Protocol
from unittest.mock import MagicMock

# ========== Protocol版 ==========


class NotifierProtocol(Protocol):
    def send(self, msg: str) -> None: ...


def test_with_protocol():
    """Protocol版のテスト"""
    # MagicMock で一発
    mock = MagicMock(spec=NotifierProtocol)
    mock.send("test")
    mock.send.assert_called_once_with("test")
    print("✅ Protocol版: MagicMock(spec=Protocol)")


# ========== ABC版 ==========


class NotifierABC(ABC):
    @abstractmethod
    def send(self, msg: str) -> None:
        pass


def test_with_abc():
    """ABC版のテスト"""
    # MagicMock で一発（Protocolと同じ）
    mock = MagicMock(spec=NotifierABC)
    mock.send("test")
    mock.send.assert_called_once_with("test")
    print("✅ ABC版: MagicMock(spec=ABC) - 全く同じ")


# ========== 実装の違い ==========


# Protocol: 継承不要
class SlackNotifierProtocol:  # 継承なし
    def send(self, msg: str) -> None:
        print(f"[Slack] {msg}")


# ABC: 継承必須
class SlackNotifierABC(NotifierABC):  # 継承あり
    def send(self, msg: str) -> None:
        print(f"[Slack] {msg}")


# ❌ ABC: 実装漏れはインスタンス化時にエラー
class IncompleteABC(NotifierABC):
    pass  # sendを実装していない


# ❌ Protocol: 実装漏れは使用時にエラー
class IncompleteProtocol:
    pass  # sendを実装していない


if __name__ == "__main__":
    print("=" * 60)
    print("テストの書き方比較")
    print("=" * 60)
    test_with_protocol()
    test_with_abc()
    print("\n結論: テストの書き方は全く同じ！")

    print("\n" + "=" * 60)
    print("実装漏れ検出の違い")
    print("=" * 60)

    # ABC: インスタンス化時にエラー
    try:
        IncompleteABC()
    except TypeError as e:
        print(f"ABC: インスタンス化時にエラー ✅\n  → {e}")

    # Protocol: インスタンス化できてしまう
    incomplete_proto = IncompleteProtocol()
    print("Protocol: インスタンス化できてしまう ⚠️")

    print("\n" + "=" * 60)
    print("結論")
    print("=" * 60)
    print("""
School Agent v2のケース:
- 全て新規実装のアダプタクラス
- 既存ライブラリをそのまま使うわけではない
- テストの書き方はProtocolもABCも同じ

→ ABCの方が適切！
  - 実装漏れを早期検出
  - 継承関係が明確
  - 「使い分け」の複雑さがない
    """)
