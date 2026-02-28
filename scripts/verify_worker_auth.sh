#!/usr/bin/env bash
# verify_worker_auth.sh
#
# Issue #65: Worker エンドポイントの OIDC 認証が正しく機能していることを検証する。
#
# 【使い方】
#   chmod +x scripts/verify_worker_auth.sh
#   ./scripts/verify_worker_auth.sh
#   ./scripts/verify_worker_auth.sh https://clearbag-api-dev-12345.asia-northeast1.run.app
#
# BASE_URL を省略すると gcloud から自動取得を試みる。
# PROJECT_ID / REGION 環境変数で対象プロジェクト・リージョンを変更可能。
#
# 【期待する動作】
#   PR #86 マージ前: 401 以外 (200, 500 など) → 認証なしで呼び出せてしまう
#   PR #86 マージ後: 401 Unauthorized → 正しく保護されている
#
# 【終了コード】
#   0: 全テスト PASS（OIDC 認証が正しく機能している）
#   1: 1件以上 FAIL（認証なしでアクセスできてしまっている）

set -euo pipefail

# ── URL 解決 ──────────────────────────────────────────────────────────────────

BASE_URL="${1:-}"
PROJECT_ID="${PROJECT_ID:-clearbag-dev}"
REGION="${REGION:-asia-northeast1}"
SERVICE_NAME="clearbag-api-dev"

if [ -z "$BASE_URL" ]; then
  echo "ℹ  BASE_URL が未指定のため gcloud から取得します..."
  if ! command -v gcloud &>/dev/null; then
    echo "❌ gcloud が見つかりません。BASE_URL を引数で指定してください"
    echo "   例: $0 https://clearbag-api-dev-12345.${REGION}.run.app"
    exit 1
  fi
  BASE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='value(status.url)' 2>/dev/null) || {
    echo "❌ gcloud から URL を取得できませんでした。BASE_URL を引数で指定してください"
    exit 1
  }
fi

BASE_URL="${BASE_URL%/}"  # 末尾スラッシュを除去
echo "🔍 検証対象: ${BASE_URL}"
echo ""

# ── ヘルパー関数 ──────────────────────────────────────────────────────────────

PASS=0
FAIL=0

_check() {
  local description="$1"
  local expected_status="$2"
  shift 2
  local curl_args=("$@")

  echo "--- ${description} ---"
  echo "  期待: HTTP ${expected_status}"

  local tmp_body
  tmp_body=$(mktemp)
  local actual_status
  actual_status=$(curl -s -o "${tmp_body}" -w "%{http_code}" "${curl_args[@]}" 2>/dev/null)

  if [ "${actual_status}" = "${expected_status}" ]; then
    echo "  ✅ PASS (HTTP ${actual_status})"
    PASS=$((PASS + 1))
  else
    echo "  ❌ FAIL (HTTP ${actual_status}, expected ${expected_status})"
    local body
    body=$(head -c 300 "${tmp_body}" 2>/dev/null || true)
    [ -n "${body}" ] && echo "     Response: ${body}"
    FAIL=$((FAIL + 1))
  fi

  rm -f "${tmp_body}"
  echo ""
}

# ── テストケース ──────────────────────────────────────────────────────────────
#
# マージ後の期待動作: 全て 401 Unauthorized
# マージ前の現状:     全て 401 以外 (200 または 500)

_check \
  "POST /worker/analyze — 認証ヘッダーなし" \
  "401" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"uid":"dummy","family_id":"dummy","document_id":"dummy","storage_path":"dummy","mime_type":"application/pdf"}' \
  "${BASE_URL}/worker/analyze"

_check \
  "POST /worker/morning-digest — 認証ヘッダーなし" \
  "401" \
  -X POST \
  -H "Content-Type: application/json" \
  "${BASE_URL}/worker/morning-digest"

_check \
  "POST /worker/analyze — 無効なトークン (Bearer invalid.token.here)" \
  "401" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid.token.here" \
  -d '{"uid":"dummy","family_id":"dummy","document_id":"dummy","storage_path":"dummy","mime_type":"application/pdf"}' \
  "${BASE_URL}/worker/analyze"

# ── サマリー ──────────────────────────────────────────────────────────────────

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  結果: PASS=${PASS}  FAIL=${FAIL}"

if [ "${FAIL}" -gt 0 ]; then
  echo ""
  echo "  ❌ OIDC 認証が正しく機能していません"
  echo ""
  echo "  確認事項:"
  echo "    1. PR #86 が dev ブランチにマージ・デプロイ済みか"
  echo "    2. Cloud Run の WORKER_SERVICE_ACCOUNT_EMAIL 環境変数が設定されているか"
  echo "       gcloud run services describe ${SERVICE_NAME} \\"
  echo "         --project=${PROJECT_ID} --region=${REGION} \\"
  echo "         --format='value(spec.template.spec.containers[0].env)'"
  exit 1
else
  echo ""
  echo "  ✅ Worker エンドポイントの OIDC 認証が正しく機能しています"
fi
