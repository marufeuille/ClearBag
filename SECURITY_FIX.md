# セキュリティ修正: allUsers 権限の削除

## 問題点

Cloud Functions `school-agent-v2` が `--allow-unauthenticated` でデプロイされていたため、`allUsers` に対して `roles/cloudfunctions.invoker` 権限が付与されていました。

**リスク**:
- エンドポイントURLが漏洩すると、誰でもFunctionを実行可能
- 意図しない実行によるコスト増加
- 不正なデータ操作の可能性

## 修正内容

### 1. デプロイスクリプトの修正 (`deploy_v2.sh`)

```diff
- --allow-unauthenticated \
+ --no-allow-unauthenticated \
```

### 2. Cloud Schedulerの設定

すでに `--oidc-service-account-email` が設定されているため、追加の変更は不要:

```bash
--oidc-service-account-email="$SERVICE_ACCOUNT_EMAIL"
```

これにより、CloudSchedulerはOIDCトークンを使用してFunctionを認証付きで呼び出します。

### 3. アクセス制御の仕組み

**修正後のアクセス制御**:

```
┌─────────────────────┐
│ Cloud Scheduler     │
│ (Service Account)   │
└──────────┬──────────┘
           │ OIDC Token
           ▼
┌─────────────────────┐
│ Cloud Functions     │
│ (認証必須)          │  ✅ Service Account → 許可
│                     │  ❌ allUsers → 拒否
└─────────────────────┘
```

**修正前の問題**:

```
┌─────────────────────┐
│ 誰でも (allUsers)   │
└──────────┬──────────┘
           │ HTTP Request
           ▼
┌─────────────────────┐
│ Cloud Functions     │
│ (認証不要)          │  ✅ 誰でも → 許可 ⚠️
└─────────────────────┘
```

## 適用方法

### 新規デプロイ

修正済みのスクリプトを使用:

```bash
./deploy_v2.sh
```

### 既存Functionの修正

#### 方法1: デプロイスクリプトで再デプロイ（推奨）

```bash
./deploy_v2.sh
```

再デプロイにより自動的に正しい権限設定が適用されます。

#### 方法2: 手動で権限を削除

```bash
# 現在の権限を確認
gcloud functions get-iam-policy school-agent-v2 \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID

# allUsers権限を削除
gcloud functions remove-iam-policy-binding school-agent-v2 \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID \
  --member="allUsers" \
  --role="roles/cloudfunctions.invoker"

# 削除を確認
gcloud functions get-iam-policy school-agent-v2 \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID
```

## 動作確認

### 1. 直接アクセスの拒否を確認

```bash
# Function URLを取得
FUNCTION_URL=$(gcloud functions describe school-agent-v2 \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID \
  --format="value(serviceConfig.uri)")

# 認証なしでアクセス → 403 Forbiddenになることを確認
curl -X POST "$FUNCTION_URL"
# Expected: <html><head>...</head><body>Forbidden</body></html>
```

### 2. CloudSchedulerからのアクセスを確認

```bash
# Schedulerジョブを手動実行
gcloud scheduler jobs run school-agent-v2-scheduler \
  --location=asia-northeast1 \
  --project=YOUR_PROJECT_ID

# ログで成功を確認
gcloud functions logs read school-agent-v2 \
  --region=asia-northeast1 \
  --project=YOUR_PROJECT_ID \
  --limit=10
```

## 影響範囲

- ✅ CloudSchedulerからの実行: **影響なし**（OIDCトークンで認証）
- ❌ 直接のHTTPアクセス: **403 Forbiddenで拒否される**（意図した動作）
- ✅ コスト: 不正実行がブロックされるため**削減**
- ✅ セキュリティ: 認証必須により**向上**

## 参考資料

- [Cloud Functions - 認証](https://cloud.google.com/functions/docs/securing/authenticating)
- [Cloud Scheduler - OIDC認証](https://cloud.google.com/scheduler/docs/http-target-auth#using-oidc-authentication)
- [IAMポリシーのベストプラクティス](https://cloud.google.com/iam/docs/policies)
