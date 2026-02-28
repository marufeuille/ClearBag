#!/usr/bin/env bash
# bootstrap_wif.sh
#
# clearbag-dev プロジェクトの Workload Identity Federation を
# ゼロから手動構築し、GitHub Environment Secrets (dev) を更新するブートストラップスクリプト。
#
# Terraform は WIF で認証して初めて動くため、WIF 自体は Terraform 外で
# 一度だけ手動作成する必要がある（鶏と卵問題）。
#
# 使い方:
#   chmod +x scripts/bootstrap_wif.sh
#   ./scripts/bootstrap_wif.sh
#
# 前提:
#   - gcloud CLI がインストール済みで、clearbag-dev のオーナー権限を持つアカウントでログイン済み
#   - gh CLI がインストール済みで、対象リポジトリへの admin 権限でログイン済み
#   - clearbag-dev-terraform-backend バケットが存在すること（既存）
#
# 冪等性: リソースが既に存在する場合はスキップするため、再実行しても安全。

set -euo pipefail

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

DEV_PROJECT="clearbag-dev"
GITHUB_REPO="marufeuille/ClearBag"

DEV_STATE_BUCKET="clearbag-dev-terraform-backend"

DEV_POOL_ID="github-actions"
DEV_PROVIDER_ID="github-oidc"
DEV_SA_ID="github-actions-deploy"

# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

info()  { echo "[INFO]  $*"; }
ok()    { echo "[OK]    $*"; }
skip()  { echo "[SKIP]  $*"; }
error() { echo "[ERROR] $*" >&2; exit 1; }

section() { echo ""; echo "=== $* ==="; }

# ---------------------------------------------------------------------------
# 前提チェック
# ---------------------------------------------------------------------------

section "前提チェック"

for cmd in gcloud gh; do
  if ! command -v "$cmd" &>/dev/null; then
    error "$cmd がインストールされていません。"
  fi
done
ok "gcloud / gh が利用可能です"

gcloud projects describe "$DEV_PROJECT" &>/dev/null || error "$DEV_PROJECT にアクセスできません。ログイン状態を確認してください。"
ok "$DEV_PROJECT へのアクセスを確認しました"

DEV_PROJECT_NUMBER=$(gcloud projects describe "$DEV_PROJECT" --format="value(projectNumber)")
info "dev project number: $DEV_PROJECT_NUMBER"

# ---------------------------------------------------------------------------
# Phase A: clearbag-dev — WIF Bootstrap
# ---------------------------------------------------------------------------

section "Phase A: clearbag-dev — API 有効化"

gcloud services enable \
  sts.googleapis.com \
  iamcredentials.googleapis.com \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  --project="$DEV_PROJECT"
ok "API 有効化完了"

section "Phase A: clearbag-dev — WIF Pool 作成"

if gcloud iam workload-identity-pools describe "$DEV_POOL_ID" \
    --project="$DEV_PROJECT" --location="global" &>/dev/null; then
  skip "WIF Pool '$DEV_POOL_ID' は既に存在します"
else
  gcloud iam workload-identity-pools create "$DEV_POOL_ID" \
    --project="$DEV_PROJECT" \
    --location="global" \
    --display-name="GitHub Actions"
  ok "WIF Pool '$DEV_POOL_ID' を作成しました"
fi

section "Phase A: clearbag-dev — WIF Provider 作成"

DEV_ALLOWED_AUD="https://iam.googleapis.com/projects/${DEV_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${DEV_POOL_ID}/providers/${DEV_PROVIDER_ID}"

if gcloud iam workload-identity-pools providers describe "$DEV_PROVIDER_ID" \
    --project="$DEV_PROJECT" \
    --location="global" \
    --workload-identity-pool="$DEV_POOL_ID" &>/dev/null; then
  skip "WIF Provider '$DEV_PROVIDER_ID' は既に存在します"
else
  gcloud iam workload-identity-pools providers create-oidc "$DEV_PROVIDER_ID" \
    --project="$DEV_PROJECT" \
    --location="global" \
    --workload-identity-pool="$DEV_POOL_ID" \
    --display-name="GitHub OIDC" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
    --attribute-condition="assertion.repository == '${GITHUB_REPO}'" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --allowed-audiences="$DEV_ALLOWED_AUD"
  ok "WIF Provider '$DEV_PROVIDER_ID' を作成しました"
fi

section "Phase A: clearbag-dev — デプロイ用 SA 作成"

DEV_SA_EMAIL="${DEV_SA_ID}@${DEV_PROJECT}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe "$DEV_SA_EMAIL" \
    --project="$DEV_PROJECT" &>/dev/null; then
  skip "SA '$DEV_SA_EMAIL' は既に存在します"
else
  gcloud iam service-accounts create "$DEV_SA_ID" \
    --project="$DEV_PROJECT" \
    --display-name="GitHub Actions デプロイ用 SA"
  ok "SA '$DEV_SA_EMAIL' を作成しました"
fi

section "Phase A: clearbag-dev — WIF バインド"

DEV_WIF_MEMBER="principalSet://iam.googleapis.com/projects/${DEV_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${DEV_POOL_ID}/attribute.repository/${GITHUB_REPO}"

gcloud iam service-accounts add-iam-policy-binding "$DEV_SA_EMAIL" \
  --project="$DEV_PROJECT" \
  --role="roles/iam.workloadIdentityUser" \
  --member="$DEV_WIF_MEMBER"
ok "WIF バインドを設定しました（既存でも上書き安全）"

section "Phase A: clearbag-dev — state バケットへの権限付与"

gcloud storage buckets add-iam-policy-binding "gs://${DEV_STATE_BUCKET}" \
  --member="serviceAccount:${DEV_SA_EMAIL}" \
  --role="roles/storage.admin"
ok "state バケット '$DEV_STATE_BUCKET' への権限を付与しました"

# ---------------------------------------------------------------------------
# Phase B: GitHub Environment Secrets 更新 (dev のみ)
# ---------------------------------------------------------------------------

section "Phase B: GitHub Environment Secrets 更新 (dev)"

DEV_WIF_PROVIDER="projects/${DEV_PROJECT_NUMBER}/locations/global/workloadIdentityPools/${DEV_POOL_ID}/providers/${DEV_PROVIDER_ID}"

info "WIF_PROVIDER:        $DEV_WIF_PROVIDER"
info "WIF_SERVICE_ACCOUNT: $DEV_SA_EMAIL"

gh secret set WIF_PROVIDER        --env dev --body "$DEV_WIF_PROVIDER" --repo "$GITHUB_REPO"
gh secret set WIF_SERVICE_ACCOUNT --env dev --body "$DEV_SA_EMAIL"     --repo "$GITHUB_REPO"

ok "GitHub Environment Secrets (dev) を更新しました"

# ---------------------------------------------------------------------------
# 完了
# ---------------------------------------------------------------------------

section "完了"
echo ""
echo "clearbag-dev の WIF Bootstrap が完了しました。"
echo "PR の terraform plan dev ジョブを Re-run してください:"
echo "  gh run rerun --failed <run-id>"
echo ""
echo "WIF Provider ID : $DEV_WIF_PROVIDER"
echo "SA Email        : $DEV_SA_EMAIL"
