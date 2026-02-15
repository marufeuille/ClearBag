# Changelog

## Phase 2 Review - 2026-02-15

### Changed: Protocol → ABC

**理由**:
- School Agent v2は全て新規実装のアダプタ
- Protocolの利点（既存クラスをそのまま使える）が活かせない
- ABCの方が実装漏れを早期検出できる（インスタンス化時 vs 使用時）
- テストの書き方は同じ（`MagicMock(spec=ABC)` も `MagicMock(spec=Protocol)` も同じ）

**変更内容**:
- `v2/domain/ports.py`: `@runtime_checkable class XXX(Protocol)` → `class XXX(ABC)` に変更
- 全6つのPort（ConfigSource, FileStorage, DocumentAnalyzer, CalendarService, TaskService, Notifier）をABC化
- `@abstractmethod` デコレータを追加

**影響**:
- ✅ テスト: 31個全てpass（変更不要）
- ✅ カバレッジ: 96%（ports.pyの抽象メソッド本体を除けば100%）
- ✅ ビジネスロジック: 変更なし

**Phase 3への影響**:
- Adapter実装時にABCを継承することが必須になる
- 実装漏れがあればインスタンス化時に即座にエラー
- IDEの補完・mypyの型チェックがより効果的に

## Phase 1-2 Complete - 2026-02-15

### Added
- ドメインモデル: 8つのdataclass
- ドメイン例外: 5つの例外クラス
- Ports: 6つのABC
- ビジネスロジック: Orchestrator, ActionDispatcher
- ユニットテスト: 31テスト、96%カバレッジ

### Documentation
- ARCHITECTURE_V2.md: 設計ドキュメント
- v2/README.md: v2概要
- v2/PHASE3_GUIDE.md: Phase 3実装ガイド
