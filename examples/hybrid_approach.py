"""
ハイブリッドアプローチ: ABC + Protocol の組み合わせ

School Agent v2 の再設計案
"""

from abc import ABC, abstractmethod
from typing import Protocol


# ========== 案1: Protocol + ABC の組み合わせ ==========

# Protocolで「型」を定義（外部向け）
class FileStorage(Protocol):
    """外部からの型として使う（テストモック等）"""

    def list_files(self) -> list[str]: ...
    def download(self, file_id: str) -> bytes: ...


# ABCで「実装ガイド」を提供（内部向け）
class FileStorageBase(ABC):
    """実装者向けの基底クラス（実装漏れを防ぐ）"""

    @abstractmethod
    def list_files(self) -> list[str]:
        """ファイル一覧取得"""
        pass

    @abstractmethod
    def download(self, file_id: str) -> bytes:
        """ファイルダウンロード"""
        pass


# ✅ 実装者はABCを継承（実装漏れを防ぐ）
class GoogleDriveStorage(FileStorageBase):
    def list_files(self) -> list[str]:
        return ["file1", "file2"]

    def download(self, file_id: str) -> bytes:
        return b"content"

    # ↑ メソッドを忘れるとインスタンス化時にエラー


# ✅ 利用者はProtocolで型指定（柔軟性）
def process_files(storage: FileStorage) -> None:
    """Protocolを使うので、ABCを継承しないクラスでもOK"""
    files = storage.list_files()
    for file_id in files:
        storage.download(file_id)


# 両方の利点を得られる
google_drive = GoogleDriveStorage()  # ABCで実装漏れ検出
process_files(google_drive)  # Protocolで柔軟に使用


# ========== 案2: Protocolのみ + 厳密なmypy設定 ==========

# pyproject.toml に以下を追加
"""
[tool.mypy]
strict = true
warn_unused_ignores = true
disallow_untyped_defs = true
"""

# mypyを常時実行すれば実装漏れを検出可能
# CI/CDでmypyを必須にする


print("""
【結論】

1. 型制約の強さ: ABC > Protocol ✅（あなたの指摘は正しい）

2. School Agent v2 での選択:
   現状: Protocolのみ
   より良い案: Protocol（型定義） + ABC（実装ガイド）のハイブリッド

3. 実際の運用:
   - mypyを導入すれば実装漏れは検出可能
   - CI/CDでmypy必須化すればProtocolでも十分安全
   - ただしABCの方が「即座に」エラーになる点で優れている

4. 今後の方針:
   Phase 3（Adapter実装）では、ABCベースクラスも提供する選択肢あり
   - v2/adapters/base.py にABC定義
   - 実装者は継承を「推奨」（必須ではない）
   - Protocolとの二重定義になるが、安全性向上
""")
