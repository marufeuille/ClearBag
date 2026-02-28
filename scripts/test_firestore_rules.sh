#!/usr/bin/env bash
# Firestore セキュリティルール検証スクリプト
#
# 使い方:
#   # dev 環境に対して実行（デフォルト）
#   ./scripts/test_firestore_rules.sh
#
#   # prod 環境に対して実行
#   PROJECT_ID=clearbag-prod ./scripts/test_firestore_rules.sh
#
#   # Firebase Emulator に対して実行（CI 用）
#   FIRESTORE_EMULATOR_HOST=127.0.0.1:8080 ./scripts/test_firestore_rules.sh
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-clearbag-dev}"

# エミュレーター環境変数が設定されていれば emulator に、なければ本番 API に向ける
if [ -n "${FIRESTORE_EMULATOR_HOST:-}" ]; then
  BASE_URL="http://${FIRESTORE_EMULATOR_HOST}/v1/projects/${PROJECT_ID}/databases/(default)/documents"
  TARGET="Emulator (${FIRESTORE_EMULATOR_HOST})"
else
  BASE_URL="https://firestore.googleapis.com/v1/projects/${PROJECT_ID}/databases/(default)/documents"
  TARGET="Real Firestore (${PROJECT_ID})"
fi

PASSED=0
FAILED=0

assert_denied() {
  local description="$1"
  local http_code="$2"

  if [ "$http_code" -eq 403 ] || [ "$http_code" -eq 401 ]; then
    echo "  PASS: ${description} (HTTP ${http_code})"
    PASSED=$((PASSED + 1))
  else
    echo "  FAIL: ${description} (HTTP ${http_code}, expected 403)"
    FAILED=$((FAILED + 1))
  fi
}

echo "=== Firestore Security Rules Test ==="
echo "Target: ${TARGET}"
echo ""

# Test 1: Unauthenticated read on users collection
code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/users/test-user")
assert_denied "Unauthenticated read on users" "$code"

# Test 2: Unauthenticated write on users collection
code=$(curl -s -o /dev/null -w "%{http_code}" \
  -X PATCH -H "Content-Type: application/json" \
  -d '{"fields":{"name":{"stringValue":"hacker"}}}' \
  "${BASE_URL}/users/test-user")
assert_denied "Unauthenticated write on users" "$code"

# Test 3: Unauthenticated read on families collection
code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/families/test-family")
assert_denied "Unauthenticated read on families" "$code"

# Test 4: Unauthenticated write on families collection
code=$(curl -s -o /dev/null -w "%{http_code}" \
  -X PATCH -H "Content-Type: application/json" \
  -d '{"fields":{"name":{"stringValue":"hacker-family"}}}' \
  "${BASE_URL}/families/test-family")
assert_denied "Unauthenticated write on families" "$code"

# Test 5: Unauthenticated read on nested subcollection
code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}/families/test-family/documents/test-doc")
assert_denied "Unauthenticated read on nested subcollection" "$code"

echo ""
echo "Results: ${PASSED} passed, ${FAILED} failed"

if [ "$FAILED" -gt 0 ]; then
  exit 1
fi
