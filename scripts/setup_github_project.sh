#!/usr/bin/env bash
# setup_github_project.sh
#
# GitHub Projects V2「ClearBag Roadmap」をセットアップするスクリプト
#
# 前提条件:
#   - gh CLI v2.30+ がインストール済み: brew upgrade gh
#   - project スコープを持つトークン: gh auth refresh -s project
#
# 使い方:
#   ./scripts/setup_github_project.sh
#
# 実行後にやること（Web UI）:
#   1. project-url を auto-add-to-project.yml に記載する（スクリプト末尾に表示）
#   2. GitHub Settings > Secrets > Actions に PROJECT_TOKEN（PAT）を登録
#   3. Board / Backlog ビューを Web UI で設定

set -euo pipefail

OWNER="marufeuille"
REPO="ClearBag"
PROJECT_TITLE="ClearBag Roadmap"

# ── 色付きログ ───────────────────────────────────────────────────────────────
info()    { echo -e "\033[0;34m[INFO]\033[0m  $*"; }
success() { echo -e "\033[0;32m[OK]\033[0m    $*"; }
warn()    { echo -e "\033[0;33m[WARN]\033[0m  $*"; }
error()   { echo -e "\033[0;31m[ERROR]\033[0m $*" >&2; exit 1; }

# ── 前提チェック ─────────────────────────────────────────────────────────────
command -v gh >/dev/null 2>&1 || error "gh CLI が見つかりません。brew install gh を実行してください。"

GH_VERSION=$(gh --version | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
GH_MAJOR=$(echo "$GH_VERSION" | cut -d. -f1)
GH_MINOR=$(echo "$GH_VERSION" | cut -d. -f2)
if [[ "$GH_MAJOR" -lt 2 ]] || [[ "$GH_MAJOR" -eq 2 && "$GH_MINOR" -lt 30 ]]; then
  error "gh CLI v2.30+ が必要です（現在: v${GH_VERSION}）。brew upgrade gh を実行してください。"
fi
info "gh CLI v${GH_VERSION} を確認しました"

# project スコープ確認
if ! gh auth status 2>&1 | grep -q "project"; then
  warn "project スコープが見当たりません。gh auth refresh -s project を実行してください。"
  warn "続行しますが、権限エラーが発生した場合はスコープを確認してください。"
fi

# ── Step 1: プロジェクト作成（冪等性: 既存なら再利用）─────────────────────
info "プロジェクトを確認中..."
EXISTING_PROJECT=$(gh project list --owner "$OWNER" --format json --jq \
  ".projects[] | select(.title == \"$PROJECT_TITLE\") | .number" 2>/dev/null || true)

if [[ -n "$EXISTING_PROJECT" ]]; then
  PROJECT_NUM="$EXISTING_PROJECT"
  success "既存プロジェクトを再利用します（#${PROJECT_NUM}）"
else
  info "プロジェクト「${PROJECT_TITLE}」を作成中..."
  PROJECT_NUM=$(gh project create --owner "$OWNER" --title "$PROJECT_TITLE" \
    --format json --jq '.number')
  success "プロジェクト #${PROJECT_NUM} を作成しました"
fi

PROJECT_URL="https://github.com/users/${OWNER}/projects/${PROJECT_NUM}"
info "プロジェクト URL: ${PROJECT_URL}"

# ── Step 2: Priority フィールド作成（冪等性: 既存なら再利用）──────────────
info "Priority フィールドを確認中..."
FIELD_ID=$(gh project field-list "$PROJECT_NUM" --owner "$OWNER" \
  --format json --jq '.fields[] | select(.name == "Priority") | .id' 2>/dev/null || true)

if [[ -n "$FIELD_ID" ]]; then
  success "既存の Priority フィールドを再利用します（ID: ${FIELD_ID}）"
else
  info "Priority フィールドを作成中..."
  FIELD_ID=$(gh project field-create "$PROJECT_NUM" --owner "$OWNER" \
    --name "Priority" \
    --data-type "SINGLE_SELECT" \
    --single-select-options "P0: Blocker,P1: High,P2: Medium,P3: Low" \
    --format json --jq '.id')
  success "Priority フィールドを作成しました（ID: ${FIELD_ID}）"
fi

# オプション ID を取得
info "Priority オプション ID を取得中..."
OPTIONS_JSON=$(gh project field-list "$PROJECT_NUM" --owner "$OWNER" \
  --format json --jq '.fields[] | select(.name == "Priority") | .options')

get_option_id() {
  local name="$1"
  echo "$OPTIONS_JSON" | jq -r ".[] | select(.name == \"$name\") | .id"
}

OPT_P0=$(get_option_id "P0: Blocker")
OPT_P1=$(get_option_id "P1: High")
OPT_P2=$(get_option_id "P2: Medium")
OPT_P3=$(get_option_id "P3: Low")

info "P0 ID: ${OPT_P0}"
info "P1 ID: ${OPT_P1}"
info "P2 ID: ${OPT_P2}"
info "P3 ID: ${OPT_P3}"

# ── Step 3: 全 open issue をプロジェクトに追加 ────────────────────────────
info "全 open issue をプロジェクトに追加中..."
ISSUE_NUMS=$(gh issue list --repo "${OWNER}/${REPO}" --state open \
  --json number --jq '.[].number')

declare -A ITEM_IDS  # issue番号 → project item ID のマップ

for num in $ISSUE_NUMS; do
  ISSUE_URL="https://github.com/${OWNER}/${REPO}/issues/${num}"
  ITEM_ID=$(gh project item-add "$PROJECT_NUM" --owner "$OWNER" \
    --url "$ISSUE_URL" --format json --jq '.id' 2>/dev/null || true)
  if [[ -n "$ITEM_ID" ]]; then
    ITEM_IDS[$num]="$ITEM_ID"
    info "  Issue #${num} → item ${ITEM_ID}"
  else
    warn "  Issue #${num} の追加をスキップ（既に追加済みの可能性）"
    # 既存アイテムの ID を取得
    ITEM_ID=$(gh project item-list "$PROJECT_NUM" --owner "$OWNER" \
      --format json --jq \
      ".items[] | select(.content.number == ${num}) | .id" 2>/dev/null || true)
    if [[ -n "$ITEM_ID" ]]; then
      ITEM_IDS[$num]="$ITEM_ID"
    fi
  fi
done
success "全 issue の追加が完了しました"

# ── Step 4: Priority フィールドを一括設定 ─────────────────────────────────
info "Priority フィールドを設定中..."

set_priority() {
  local issue_num="$1"
  local option_id="$2"
  local label="$3"
  local item_id="${ITEM_IDS[$issue_num]:-}"

  if [[ -z "$item_id" ]]; then
    warn "  Issue #${issue_num} の item ID が不明のためスキップ"
    return
  fi

  gh project item-edit "$PROJECT_NUM" --owner "$OWNER" \
    --id "$item_id" \
    --field-id "$FIELD_ID" \
    --single-select-option-id "$option_id" >/dev/null 2>&1 && \
    info "  Issue #${issue_num} → ${label}" || \
    warn "  Issue #${issue_num} の Priority 設定に失敗"
}

# P1: High
for num in 71 70 68 67; do
  set_priority "$num" "$OPT_P1" "P1: High"
done

# P2: Medium
for num in 92 90 89 75 74 72 62 61 60; do
  set_priority "$num" "$OPT_P2" "P2: Medium"
done

# P3: Low
for num in 79 78 77 76; do
  set_priority "$num" "$OPT_P3" "P3: Low"
done

success "Priority フィールドの一括設定が完了しました"

# ── 完了メッセージ ────────────────────────────────────────────────────────
echo ""
echo "════════════════════════════════════════════════════════════════"
echo " セットアップ完了！"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo " プロジェクト URL: ${PROJECT_URL}"
echo " プロジェクト番号: ${PROJECT_NUM}"
echo ""
echo " 残りの手動作業:"
echo ""
echo " 1. ワークフローのプロジェクト番号を更新:"
echo "    .github/workflows/auto-add-to-project.yml の project-url を:"
echo "    ${PROJECT_URL}"
echo "    に書き換えてください。"
echo ""
echo " 2. PROJECT_TOKEN シークレットを登録:"
echo "    https://github.com/${OWNER}/${REPO}/settings/secrets/actions"
echo "    → New repository secret → Name: PROJECT_TOKEN"
echo "    → Value: project スコープを持つ PAT"
echo ""
echo " 3. Web UI でビューを作成:"
echo "    ${PROJECT_URL}"
echo "    - Board ビュー: Status でグループ（Todo / In Progress / Done）"
echo "    - Backlog ビュー: Table, Priority ソート, Milestone グループ"
echo ""
echo " 4. 検証:"
echo "    gh project item-list ${PROJECT_NUM} --owner ${OWNER} | wc -l"
echo "════════════════════════════════════════════════════════════════"
