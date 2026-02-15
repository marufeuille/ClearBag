"""
実際のプロジェクトでのProtocol vs ABCのトレードオフ

School Agent v2の設計判断を再検討します。
"""

from abc import ABC, abstractmethod
from typing import Protocol
from unittest.mock import MagicMock


# ========== シナリオ1: 既存ライブラリの利用 ==========

print("=" * 60)
print("シナリオ1: 既存ライブラリのラップ")
print("=" * 60)

# 例: requests.Session は我々が制御できない外部クラス
class ExistingHttpClient:
    """外部ライブラリのクラス（変更不可）"""

    def get(self, url: str) -> str:
        return f"Response from {url}"

    def post(self, url: str, data: str) -> str:
        return f"Posted to {url}"


# ABC方式: 継承が必要
class HttpClientABC(ABC):
    @abstractmethod
    def get(self, url: str) -> str: ...

    @abstractmethod
    def post(self, url: str, data: str) -> str: ...


# ❌ 既存クラスをABCに適合させるには「ラッパー」が必要
class ExistingHttpClientAdapter(HttpClientABC):
    """ラッパークラスを作る必要がある"""

    def __init__(self, client: ExistingHttpClient):
        self._client = client

    def get(self, url: str) -> str:
        return self._client.get(url)

    def post(self, url: str, data: str) -> str:
        return self._client.post(url, data)


# Protocol方式: そのまま使える！
class HttpClientProtocol(Protocol):
    def get(self, url: str) -> str: ...

    def post(self, url: str, data: str) -> str: ...


def use_client_protocol(client: HttpClientProtocol) -> None:
    print(client.get("https://example.com"))


# ✅ Protocolなら既存クラスをそのまま使える
existing = ExistingHttpClient()
use_client_protocol(existing)  # ラッパー不要！

print("結論: 既存ライブラリを使う場合、Protocolの方が簡潔")
print()


# ========== シナリオ2: テストのしやすさ ==========

print("=" * 60)
print("シナリオ2: テストでのモック作成")
print("=" * 60)


class NotifierABC(ABC):
    @abstractmethod
    def send(self, msg: str) -> None: ...


class NotifierProtocol(Protocol):
    def send(self, msg: str) -> None: ...


# ABC方式: モックも継承が必要
class MockNotifierABC(NotifierABC):
    def __init__(self):
        self.messages = []

    def send(self, msg: str) -> None:
        self.messages.append(msg)


# Protocol方式: MagicMockで一発
mock_protocol = MagicMock(spec=NotifierProtocol)

print("ABC:     テスト用のモッククラスを定義する必要がある")
print("Protocol: MagicMock(spec=Protocol) で一発")
print()


# ========== シナリオ3: 複数インターフェースの実装 ==========

print("=" * 60)
print("シナリオ3: 複数のインターフェース実装")
print("=" * 60)


class LoggerABC(ABC):
    @abstractmethod
    def log(self, msg: str) -> None: ...


class NotifierABC2(ABC):
    @abstractmethod
    def notify(self, msg: str) -> None: ...


# ABC: 多重継承が必要
class LoggingNotifierABC(LoggerABC, NotifierABC2):
    def log(self, msg: str) -> None:
        print(f"LOG: {msg}")

    def notify(self, msg: str) -> None:
        print(f"NOTIFY: {msg}")


# Protocol: 自然に複数の型として扱える
class LoggerProtocol(Protocol):
    def log(self, msg: str) -> None: ...


class NotifierProtocol2(Protocol):
    def notify(self, msg: str) -> None: ...


class LoggingNotifier:  # 継承なし！
    def log(self, msg: str) -> None:
        print(f"LOG: {msg}")

    def notify(self, msg: str) -> None:
        print(f"NOTIFY: {msg}")


def use_as_logger(logger: LoggerProtocol) -> None:
    logger.log("test")


def use_as_notifier(notifier: NotifierProtocol2) -> None:
    notifier.notify("test")


service = LoggingNotifier()
use_as_logger(service)  # Loggerとして使える
use_as_notifier(service)  # Notifierとしても使える

print("Protocol: 継承なしで複数の型として扱える")
print()


# ========== まとめ ==========

print("=" * 60)
print("まとめ: Protocol vs ABC")
print("=" * 60)
print("""
【ABCが優れている点】
✅ 実装漏れを早期検出（インスタンス化時）
✅ 継承関係が明示的
✅ 共通実装を基底クラスで提供可能

【Protocolが優れている点】
✅ 既存クラスをそのまま利用可能（ラッパー不要）
✅ テストモックが簡単（MagicMock一発）
✅ 継承階層を強制しない（柔軟性）
✅ 複数のProtocolを自然に満たせる

【School Agent v2でProtocolを選んだ理由】
1. Google Drive/Slack等の既存ライブラリをラップする際に簡潔
2. テストでモックを大量に作る必要がある
3. LLMに「継承を説明する」負担を減らす
4. 将来的な拡張（通知先追加等）の柔軟性

【ただし...】
- mypyを導入すれば実装漏れは両方とも検出可能
- 型制約の強さではABCが上
- プロジェクトの性質によってはABCの方が良い場合もある
""")
