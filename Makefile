# ClearBag ローカル開発 Makefile
#
# 使い方:
#   make dev-infra     エミュレーター起動 (Firestore + fake-gcs)
#   make dev-backend   FastAPI バックエンド起動 (ホットリロード)
#   make dev-frontend  Next.js フロントエンド起動
#   make dev           インフラ起動後、backend/frontend を並列起動するガイド表示
#   make stop          エミュレーター停止
#   make test          Python テスト実行
#   make lint          リント実行

.PHONY: dev-infra dev-backend dev-frontend dev stop test lint help

# ── インフラ (エミュレーター) ────────────────────────────────────────────────
dev-infra:
	@echo "==> Firestore + fake-gcs エミュレーターを起動します..."
	docker compose up -d
	@echo "==> エミュレーター起動確認中..."
	docker compose ps
	@echo ""
	@echo "  Firestore: http://localhost:8088"
	@echo "  GCS:       http://localhost:4443"

# ── バックエンド ─────────────────────────────────────────────────────────────
dev-backend:
	@if [ ! -f .env.local ]; then \
		echo "==> .env.local が見つかりません。.env.local.example からコピーします..."; \
		cp .env.local.example .env.local; \
		echo "==> .env.local を編集して PROJECT_ID などを設定してください。"; \
	fi
	@echo "==> FastAPI バックエンドを起動します (port 8000)..."
	@set -a; . ./.env.local; set +a; \
		uv run uvicorn v2.entrypoints.api.app:app \
			--reload \
			--host 0.0.0.0 \
			--port 8000

# ── フロントエンド ───────────────────────────────────────────────────────────
dev-frontend:
	@if [ ! -f frontend/.env.local ]; then \
		echo "==> frontend/.env.local が見つかりません。.env.local.example からコピーします..."; \
		cp frontend/.env.local.example frontend/.env.local; \
		echo "==> frontend/.env.local を編集して Firebase 設定を記入してください。"; \
	fi
	@echo "==> Next.js フロントエンドを起動します (port 3000)..."
	cd frontend && npm run dev

# ── 全体起動ガイド ────────────────────────────────────────────────────────────
dev:
	@echo "============================================================"
	@echo "  ClearBag ローカル開発環境を起動するには:"
	@echo ""
	@echo "  Terminal 1:  make dev-infra"
	@echo "  Terminal 2:  make dev-backend"
	@echo "  Terminal 3:  make dev-frontend"
	@echo ""
	@echo "  または、1つのターミナルで:"
	@echo "  make dev-infra && (make dev-backend &) && make dev-frontend"
	@echo "============================================================"
	@echo ""
	@$(MAKE) dev-infra

# ── 停止 ────────────────────────────────────────────────────────────────────
stop:
	@echo "==> エミュレーターを停止します..."
	docker compose down

# ── テスト ───────────────────────────────────────────────────────────────────
test:
	uv run pytest tests/ -v

# ── リント ───────────────────────────────────────────────────────────────────
lint:
	uv run ruff check v2/ tests/
	uv run ruff format --check v2/ tests/

# ── ヘルプ ───────────────────────────────────────────────────────────────────
help:
	@echo "利用可能なコマンド:"
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}' || true
	@echo ""
	@echo "  dev-infra            エミュレーター起動 (Firestore + fake-gcs)"
	@echo "  dev-backend          FastAPI バックエンド起動 (ホットリロード)"
	@echo "  dev-frontend         Next.js フロントエンド起動"
	@echo "  dev                  起動ガイドを表示しインフラを起動"
	@echo "  stop                 エミュレーター停止"
	@echo "  test                 Python テスト実行"
	@echo "  lint                 リント実行"
