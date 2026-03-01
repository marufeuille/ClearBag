# ClearBag バックエンド

# ── ステージ 1: 依存関係ビルダー ────────────────────────────────────────────
FROM python:3.13-slim AS builder

# uv をインストール（公式 distroless イメージからコピー）
COPY --from=ghcr.io/astral-sh/uv:0.6.3 /uv /usr/local/bin/uv

WORKDIR /app

# pyproject.toml と uv.lock だけ先にコピー（レイヤーキャッシュ最適化）
COPY pyproject.toml uv.lock ./

# 本番依存のみインストール（ruff / pytest などの dev 依存を除外）
RUN uv sync --frozen --no-dev --no-install-project

# ── ステージ 2: ランタイムイメージ ──────────────────────────────────────────
FROM python:3.13-slim

# セキュリティ: 非 root ユーザーで実行
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# ビルダーで作成した仮想環境をコピー
COPY --from=builder /app/.venv /app/.venv

# アプリケーションコードをコピー（v2/ のみ）
COPY v2/ ./v2/

# 仮想環境を PATH に追加
ENV PATH="/app/.venv/bin:$PATH"

# Cloud Run は PORT 環境変数でポートを通知する（デフォルト 8080）
ENV PORT=8080

# 非 root ユーザーに切り替え
USER appuser

# デフォルト: API サーバー起動
CMD ["sh", "-c", "uvicorn v2.entrypoints.api.app:app --host 0.0.0.0 --port ${PORT} --workers 1"]
