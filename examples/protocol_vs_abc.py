"""
Protocol と ABC の型チェック比較

実装漏れがあった場合の挙動を比較します。
"""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


# ========== 1. ABC方式 ==========

class NotifierABC(ABC):
    """ABC版 - 継承が必須"""

    @abstractmethod
    def send_message(self, message: str) -> None:
        """メッセージ送信"""
        pass

    @abstractmethod
    def get_status(self) -> str:
        """ステータス取得"""
        pass


# ❌ ケース1: ABCで実装漏れ
class IncompleteABCNotifier(NotifierABC):
    """send_messageしか実装していない → インスタンス化時にエラー"""

    def send_message(self, message: str) -> None:
        print(f"Sending: {message}")

    # get_status を実装していない！


# ========== 2. Protocol方式 ==========

@runtime_checkable
class NotifierProtocol(Protocol):
    """Protocol版 - 継承不要"""

    def send_message(self, message: str) -> None:
        """メッセージ送信"""
        ...

    def get_status(self) -> str:
        """ステータス取得"""
        ...


# ❌ ケース2: Protocolで実装漏れ
class IncompleteProtocolNotifier:
    """send_messageしか実装していない → 実行時エラーなし！"""

    def send_message(self, message: str) -> None:
        print(f"Sending: {message}")

    # get_status を実装していない！


# ========== 実行比較 ==========

def use_notifier_abc(notifier: NotifierABC) -> None:
    """ABC版を使う関数"""
    notifier.send_message("Hello")
    print(f"Status: {notifier.get_status()}")


def use_notifier_protocol(notifier: NotifierProtocol) -> None:
    """Protocol版を使う関数"""
    notifier.send_message("Hello")
    print(f"Status: {notifier.get_status()}")


if __name__ == "__main__":
    print("=" * 60)
    print("1. ABC方式: 実装漏れのテスト")
    print("=" * 60)

    try:
        incomplete_abc = IncompleteABCNotifier()  # ← ここで即エラー
    except TypeError as e:
        print(f"✅ ABCはインスタンス化時点でエラー: {e}")

    print()
    print("=" * 60)
    print("2. Protocol方式: 実装漏れのテスト")
    print("=" * 60)

    incomplete_proto = IncompleteProtocolNotifier()  # ← エラーなし
    print("✅ Protocolはインスタンス化できてしまう")

    # 型チェックは通る（runtime_checkableでもメソッド存在チェックのみ）
    print(f"isinstance check: {isinstance(incomplete_proto, NotifierProtocol)}")

    # 実際に使おうとすると...
    try:
        use_notifier_protocol(incomplete_proto)
    except AttributeError as e:
        print(f"❌ 実行時にエラー: {e}")

    print()
    print("=" * 60)
    print("3. 静的型チェック（mypy）での検出")
    print("=" * 60)
    print("mypyを実行すると...")
    print("  ABC: インスタンス化時点でエラー検出 ✅")
    print("  Protocol: メソッド呼び出し時点でエラー検出 ✅")
    print("  → どちらも型チェッカーは検出できる")
