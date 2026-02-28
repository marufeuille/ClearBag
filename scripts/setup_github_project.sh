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

# item-edit に必要な GraphQL node ID を取得（--owner フラグ非対応のため）
PROJECT_ID=$(gh project list --owner "$OWNER" --format json \
  --jq ".projects[] | select(.number == ${PROJECT_NUM}) | .id")

PROJECT_URL="https://github.com/users/${OWNER}/projects/${PROJECT_NUM}"
info "プロジェクト URL: ${PROJECT_URL}"
info "プロジェクト ID: ${PROJECT_ID}"

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

# issue 番号から Priority オプション ID を返す（Bash 3.2 互換の case 文）
priority_option_for() {
  local num="$1"
  case "$num" in
    71|70|68|67)                  echo "$OPT_P1" ;;
    92|90|89|75|74|72|62|61|60)  echo "$OPT_P2" ;;
    79|78|77|76)                  echo "$OPT_P3" ;;
    *)                             echo "" ;;
  esac
}

priority_label_for() {
  local num="$1"
  case "$num" in
    71|70|68|67)                  echo "P1: High" ;;
    92|90|89|75|74|72|62|61|60)  echo "P2: Medium" ;;
    79|78|77|76)                  echo "P3: Low" ;;
    *)                             echo "（未設定）" ;;
  esac
}

# ── Step 3 & 4: 全 open issue をプロジェクトに追加し、Priority を設定 ──────
info "全 open issue をプロジェクトに追加中..."
ISSUE_NUMS=$(gh issue list --repo "${OWNER}/${REPO}" --state open \
  --json number --jq '.[].number')

for num in $ISSUE_NUMS; do
  ISSUE_URL="https://github.com/${OWNER}/${REPO}/issues/${num}"

  # item-add: 既に追加済みの場合は既存 item ID を返す
  ITEM_ID=$(gh project item-add "$PROJECT_NUM" --owner "$OWNER" \
    --url "$ISSUE_URL" --format json --jq '.id' 2>/dev/null || true)

  # item-add が空を返した場合（重複追加などで失敗）は item-list から取得
  if [[ -z "$ITEM_ID" ]]; then
    warn "  Issue #${num} の追加をスキップ（既に追加済みの可能性）"
    ITEM_ID=$(gh project item-list "$PROJECT_NUM" --owner "$OWNER" \
      --format json --jq \
      ".items[] | select(.content.number == ${num}) | .id" 2>/dev/null || true)
  fi

  if [[ -z "$ITEM_ID" ]]; then
    warn "  Issue #${num}: item ID を取得できませんでした"
    continue
  fi

  info "  Issue #${num} → item ${ITEM_ID}"

  # Priority フィールドを設定
  OPT_ID=$(priority_option_for "$num")
  if [[ -n "$OPT_ID" ]]; then
    LABEL=$(priority_label_for "$num")
    # item-edit は --owner 非対応。--project-id に GraphQL node ID を渡す
    gh project item-edit \
      --id "$ITEM_ID" \
      --field-id "$FIELD_ID" \
      --project-id "$PROJECT_ID" \
      --single-select-option-id "$OPT_ID" >/dev/null 2>&1 && \
      info "    Priority → ${LABEL}" || \
      warn "    Issue #${num} の Priority 設定に失敗"
  fi
done

success "全 issue の追加と Priority 設定が完了しました"

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
