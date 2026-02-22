# CI設計：v2/ Python コード向け GitHub Actions

## Context

`v2/` 配下のPythonコードに対するCI（継続的インテグレーション）が未導入の状態。
以前存在していたワークフロー（commit `eb5ad70`で削除済み）を踏まえ、ruff（linter/formatter）と pytest によるCIを GitHub Actions で新規構築する。

---

## 方針サマリ

| 項目 | 内容 |
|------|------|
| CIプラットフォーム | GitHub Actions |
| トリガー | Pull Request to `main` のみ |
| パスフィルター | `v2/**`, `tests/**`, `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml` |
| Linter | ruff (lint + format check) |
| テスト | pytest (`tests/unit/`, `tests/integration/` のうち `-m "not manual"`) |
| パッケージ管理 | uv（既存のプロジェクト構成を踏襲） |
| Python バージョン | 3.13 |

---

## 変更対象ファイル

| ファイル | 操作 | 目的 |
|----------|------|------|
| `.github/workflows/ci.yml` | **新規作成** | CIワークフロー定義 |
| `pyproject.toml` | **編集** | `[tool.ruff]` セクション追加 |

---

## 1. pyproject.toml への ruff 設定追加

既存の `[tool.pytest.ini_options]` セクションの後に以下を追加する。

```toml
[tool.ruff]
target-version = "py313"
src = ["v2", "tests"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort (import ordering)
    "UP",   # pyupgrade (Python 3.13向けモダン化)
    "B",    # flake8-bugbear (よくあるバグパターン)
    "SIM",  # flake8-simplify
]
```

### 設定の根拠

- `target-version = "py313"` — Python 3.13を前提としたルール適用
- `src = ["v2", "tests"]` — isortがファーストパーティimportを正しく識別するためのソースルート指定
- `select` は保守的なルールセット。`D`（docstring）や `ANN`（型アノテーション）など、既存コードに大量の警告を出すルールは含めない
- `[tool.ruff.format]` は不要（デフォルトの88文字/ダブルクォートで問題ない）

---

## 2. GitHub Actions ワークフロー

### 2.1 ジョブ構成

**lint** と **test** の2ジョブに分離し、並列実行する。

- lint は高速（数秒）に完了するため、テスト完了を待たずフォーマット/lint違反を即座にフィードバックできる
- 失敗のセマンティクスが異なる（スタイル違反 vs ロジック不具合）

### 2.2 ワークフロー定義 (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  pull_request:
    branches: [main]
    paths:
      - "v2/**"
      - "tests/**"
      - "pyproject.toml"
      - "uv.lock"
      - ".github/workflows/ci.yml"

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Ruff lint
        run: uv run ruff check v2/ tests/

      - name: Ruff format check
        run: uv run ruff format --check v2/ tests/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true

      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Install dependencies
        run: uv sync --extra dev

      - name: Run tests
        run: >
          uv run pytest
          tests/unit/
          tests/integration/
          -m "not manual"
          --cov=v2
          --cov-report=term-missing

```

### 2.3 設計判断

| 判断 | 理由 |
|------|------|
| PR のみトリガー | push + PR だと同一コミットで二重実行されるため |
| パスフィルター導入 | ドキュメントのみの変更でCI消費を防ぐ |
| `astral-sh/setup-uv@v5` + `enable-cache: true` | uv のパッケージキャッシュを自動管理。追加の `actions/cache` 不要 |
| テスト対象: `tests/unit/` + `tests/integration/` | `tests/e2e/` はpytestテスト形式でなくスクリプト形式のため除外。`tests/manual/` は実API依存のため除外 |
| `-m "not manual"` | `tests/integration/test_adapters_manual.py` の全テストが `@pytest.mark.manual` 付きのため安全に除外 |
| `--cov=v2` | カバレッジ計測対象を `v2/` プロダクションコードに限定 |
| `--cov-report=term-missing` | CIログ上でカバレッジと未カバー行を確認可能 |
| mypy は含めない | 今回のスコープ外（ruff + pytest のみ） |

---

## 3. 注意事項

### 既存コードの ruff 違反

ruff を新規導入するため、初回実行時に `v2/` や `tests/` で既存のlint/format違反が検出される可能性が高い。CI導入PRの一部として以下を事前に実行し修正すること。

```bash
uv run ruff check --fix v2/ tests/
uv run ruff format v2/ tests/
```

### integration テストの安全性

`tests/integration/test_adapters_manual.py` 内の全テストクラスには `@pytest.mark.manual` が付与済みであることを確認済み。`-m "not manual"` により CI では安全にスキップされる。

---

## 4. 検証手順

CI導入後、以下の手順で動作を検証する。

1. **ローカルでの事前確認**
   ```bash
   uv run ruff check v2/ tests/
   uv run ruff format --check v2/ tests/
   uv run pytest tests/unit/ tests/integration/ -m "not manual" --cov=v2 --cov-report=term-missing
   ```

2. **PR作成による CI 動作確認**
   - 新規ブランチで `.github/workflows/ci.yml` と `pyproject.toml` の変更をcommit
   - main 向けにPRを作成し、lint / test の両ジョブが正常に完了することを確認

3. **意図的な失敗テスト**（任意）
   - ruff 違反を含むコードをpushし、lint ジョブが失敗することを確認
   - 失敗するテストを追加し、test ジョブが失敗することを確認
