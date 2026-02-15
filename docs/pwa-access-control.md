# PWAアクセス制限の実装方法

## 背景

### 要件
- **対象ユーザー**: 妻・祖母の2名のみ
- **目的**: 第三者からのアクセスを防ぐ
- **技術的制約**: PWAは静的サイト(HTML/CSS/JS)

---

## アクセス制限の3つのレベル

### 比較表

| レベル | 方法 | セキュリティ | 実装コスト | 推奨度 |
|--------|------|-------------|-----------|--------|
| **レベル1** | URL難読化 | ★☆☆☆☆ | ★★★★★(極小) | ⚠️ 簡易対応 |
| **レベル2** | Basic認証 | ★★★☆☆ | ★★★★☆(小) | 🥈 中程度 |
| **レベル3** | Firebase Auth | ★★★★★ | ★★★☆☆(中) | 🥇 最推奨 |

---

## レベル1: URL難読化(簡易対応)

### 概要
推測困難なランダムURLでPWAをホスティング。

### 実装方法
```
https://your-pwa.web.app/a3f8d9c2-4e7b-11ec-81d3-0242ac130003
```

ランダムなUUID v4をURLパスに使用。

### メリット
- ✅ 実装コストゼロ
- ✅ Firebase Hostingでそのまま使用可能
- ✅ 追加の認証コード不要

### デメリット
- ❌ セキュリティ極めて低い
- ❌ URLが漏れたら誰でもアクセス可能
- ❌ ブラウザ履歴、リファラーから漏洩リスク
- ❌ 「セキュリティ」とは呼べない

### 実装例
```bash
# Firebase Hostingでのデプロイ
firebase deploy --only hosting

# デプロイ先
# https://your-project.web.app/a3f8d9c2-4e7b-11ec-81d3-0242ac130003/
```

### 想定コスト
**0円** (追加コストなし)

### 推奨度
⚠️ **非推奨** - 家族内での一時的な利用のみ

---

## レベル2: Basic認証(Cloud Functions)

### 概要
Cloud FunctionsをリバースプロキシとしてBasic認証を追加。

### アーキテクチャ
```
ユーザー
  ↓ (Basic認証)
Cloud Functions(認証ゲートウェイ)
  ↓ (認証成功時のみ)
Firebase Hosting(PWA)
```

### 実装方法

#### 1. Cloud Functionsで認証ゲートウェイを作成

```python
# v2/entrypoints/pwa_gateway.py
import functions_framework
from flask import request, Response
import base64
import os

# 環境変数からユーザー情報取得(Secret Managerで管理)
VALID_USERS = {
    "wife": os.environ.get("PWA_PASSWORD_WIFE"),
    "grandma": os.environ.get("PWA_PASSWORD_GRANDMA")
}

def check_auth(username, password):
    """認証チェック"""
    return VALID_USERS.get(username) == password

def authenticate():
    """認証要求レスポンス"""
    return Response(
        'Could not verify your access level for that URL.\n'
        'You have to login with proper credentials', 401,
        {'WWW-Authenticate': 'Basic realm="Login Required"'}
    )

@functions_framework.http
def pwa_gateway(request):
    """Basic認証ゲートウェイ"""
    auth = request.authorization

    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()

    # 認証成功 → Firebase HostingのPWAにプロキシ
    # (実際にはFirebase Hosting URLにリダイレクト)
    return redirect("https://your-project.web.app/")
```

#### 2. デプロイ設定

```bash
# deploy_pwa_gateway.sh
gcloud functions deploy pwa-gateway \
  --gen2 \
  --runtime=python313 \
  --region=asia-northeast1 \
  --source=. \
  --entry-point=pwa_gateway \
  --trigger-http \
  --allow-unauthenticated \
  --set-secrets PWA_PASSWORD_WIFE=pwa-password-wife:latest,PWA_PASSWORD_GRANDMA=pwa-password-grandma:latest
```

#### 3. Secret Managerにパスワード登録

```bash
# 妻用パスワード
echo -n "wife-strong-password" | gcloud secrets create pwa-password-wife \
  --data-file=- \
  --replication-policy="automatic"

# 祖母用パスワード
echo -n "grandma-strong-password" | gcloud secrets create pwa-password-grandma \
  --data-file=- \
  --replication-policy="automatic"
```

### メリット
- ✅ 実装コストが低い(Cloud Functions 1つ追加のみ)
- ✅ ブラウザ標準のBasic認証ダイアログ
- ✅ HTTPS通信で暗号化
- ✅ Secret Managerでパスワード管理

### デメリット
- ❌ ブラウザがパスワードを平文保存(Base64エンコードのみ)
- ❌ ログアウト機能がない(ブラウザ再起動まで保持)
- ⚠️ ユーザー体験が悪い(毎回ダイアログ表示)
- ⚠️ Cloud Functions経由でアクセスするため、若干遅延

### 想定コスト
- **Cloud Functions**: 無料枠内(200万リクエスト/月)
- **追加コスト**: **0円/月**

### 推奨度
🥈 **中程度** - 簡易的なアクセス制限として実用的

---

## レベル3: Firebase Authentication(最推奨)

### 概要
Firebase Authenticationで本格的なユーザー認証を実装。

### アーキテクチャ
```
ユーザー
  ↓ (ログイン画面)
Firebase Authentication
  ↓ (Firebase IDトークン発行)
PWA(Service Worker)
  ↓ (トークン検証)
Cloud Functions(通知送信)
```

### 実装方法

#### 1. Firebase Authentication初期化

```bash
# Firebase Authenticationを有効化
firebase init auth
```

#### 2. PWAにログイン画面を追加

```javascript
// login.js
import { initializeApp } from 'firebase/app';
import { getAuth, signInWithEmailAndPassword, onAuthStateChanged } from 'firebase/auth';

// Firebase設定(既存のGCPプロジェクト)
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project",
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// ログイン処理
async function login(email, password) {
  try {
    const userCredential = await signInWithEmailAndPassword(auth, email, password);
    // ログイン成功 → メイン画面へ
    window.location.href = '/main.html';
  } catch (error) {
    alert('ログイン失敗: ' + error.message);
  }
}

// 認証状態の監視
onAuthStateChanged(auth, (user) => {
  if (!user) {
    // 未ログイン → ログイン画面へリダイレクト
    if (window.location.pathname !== '/login.html') {
      window.location.href = '/login.html';
    }
  }
});
```

#### 3. ログイン画面HTML

```html
<!-- login.html -->
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ログイン - 学校通知アプリ</title>
  <link rel="stylesheet" href="/styles.css">
</head>
<body>
  <div class="login-container">
    <h1>学校通知アプリ</h1>
    <form id="login-form">
      <input type="email" id="email" placeholder="メールアドレス" required>
      <input type="password" id="password" placeholder="パスワード" required>
      <button type="submit">ログイン</button>
    </form>
  </div>
  <script type="module" src="/login.js"></script>
</body>
</html>
```

#### 4. Firebase Authenticationでユーザー作成

```bash
# Firebase CLIでユーザー作成
firebase auth:import users.json

# users.json
[
  {
    "localId": "wife",
    "email": "wife@example.com",
    "passwordHash": "...",
    "displayName": "妻"
  },
  {
    "localId": "grandma",
    "email": "grandma@example.com",
    "passwordHash": "...",
    "displayName": "祖母"
  }
]
```

または、Firebase Consoleから手動作成:
1. Firebase Console → Authentication → Users → Add user
2. メールアドレス: `wife@example.com`
3. パスワード: 強力なパスワードを設定

#### 5. Service Workerでトークン検証(セキュリティ強化)

```javascript
// service-worker.js
import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);

// 通知購読前にトークン検証
self.addEventListener('push', async (event) => {
  const user = auth.currentUser;

  if (!user) {
    console.error('未認証ユーザー');
    return;
  }

  // IDトークン取得
  const token = await user.getIdToken();

  // 通知表示
  const data = event.data.json();
  self.registration.showNotification(data.title, {
    body: data.body,
    icon: '/icon.png',
  });
});
```

#### 6. Cloud FunctionsでIDトークン検証

```python
# v2/adapters/pwa_notifier.py
from firebase_admin import auth, initialize_app
from pywebpush import webpush

# Firebase Admin SDK初期化
initialize_app()

class PWANotifier(Notifier):
    def __init__(self, vapid_private_key: str, vapid_claims: dict):
        self._vapid_key = vapid_private_key
        self._vapid_claims = vapid_claims

    def _get_subscriptions(self):
        """Google Sheetsから購読情報取得(IDトークン付き)"""
        # ここでIDトークン検証
        # subscriptionsにはIDトークンと購読情報が含まれる
        pass

    def notify_file_processed(self, filename, summary, events, tasks, file_link):
        subscriptions = self._get_subscriptions()

        for sub in subscriptions:
            # IDトークン検証
            try:
                decoded_token = auth.verify_id_token(sub['id_token'])
                uid = decoded_token['uid']
            except Exception as e:
                print(f"Invalid token: {e}")
                continue

            # 通知送信
            webpush(
                subscription_info=sub['subscription'],
                data=json.dumps(payload),
                vapid_private_key=self._vapid_key,
                vapid_claims=self._vapid_claims
            )
```

### メリット
- ✅ **本格的なセキュリティ**: Firebase IDトークン(JWT)で認証
- ✅ **Google Cloud統一**: 既存のGCPプロジェクトに統合
- ✅ **ログイン状態保持**: リフレッシュトークンで自動更新(1時間有効)
- ✅ **ログアウト機能**: `signOut()`で明示的にログアウト可能
- ✅ **パスワードリセット**: `sendPasswordResetEmail()`で実装可能
- ✅ **多要素認証(MFA)**: Firebase Authで2FA追加可能(将来)
- ✅ **ユーザー管理**: Firebase Consoleで一元管理

### デメリット
- ⚠️ **実装コスト中**: ログイン画面、認証フローの実装が必要
- ⚠️ **初期設定**: Firebase Authenticationの有効化、ユーザー作成

### 想定コスト
- **Firebase Authentication**: 月50,000回まで無料(SMSなし)
- **想定利用**: 2ユーザー × 月30ログイン = 60回 → **無料枠内**
- **追加コスト**: **0円/月**

### 推奨度
🥇 **最推奨** - 本格的なPWAアプリとして実装

---

## 詳細比較表

| 項目 | URL難読化 | Basic認証 | Firebase Auth |
|------|----------|----------|---------------|
| **セキュリティレベル** | ★☆☆☆☆ | ★★★☆☆ | ★★★★★ |
| **実装コスト** | ★★★★★(極小) | ★★★★☆(小) | ★★★☆☆(中) |
| **ユーザー体験** | ★★★★★ | ★★☆☆☆ | ★★★★★ |
| **ログアウト機能** | ❌ なし | ❌ なし | ✅ あり |
| **パスワード変更** | ❌ 不可 | ⚠️ 手動 | ✅ 自動 |
| **GCP統合** | ✅ | ✅ | ✅ |
| **追加コスト** | 0円 | 0円 | 0円 |
| **家族2名向け** | ⚠️ 簡易 | 🥈 実用的 | 🥇 最適 |

---

## 最終推奨: Firebase Authentication

### 決定理由

#### 1. Google Cloud完全統合
- 既存のGCPプロジェクトに統合
- Firebase Hosting + Firebase Authで一元管理
- Secret Manager不要(Firebase Authが管理)

#### 2. セキュリティ
- Firebase IDトークン(JWT)で本格的な認証
- HTTPS通信で暗号化
- トークンの自動更新(1時間有効)
- ログアウト機能あり

#### 3. ユーザー体験
- 美しいログイン画面を自由にデザイン可能
- パスワード保存機能(ブラウザ標準)
- パスワードリセット機能
- ログイン状態保持

#### 4. 拡張性
- 将来的に多要素認証(MFA)追加可能
- ユーザー数が増えても対応可能
- Firebase Consoleでユーザー管理

#### 5. コスト
- 完全無料(月50,000回まで)
- 2ユーザーの場合、永久に0円

---

## 実装ロードマップ

### Phase 1: Firebase Authentication基本実装

#### 1. Firebase Authentication有効化
```bash
firebase init auth
```

#### 2. ログイン画面作成
- `login.html` - ログインフォーム
- `login.js` - Firebase Auth統合
- `styles.css` - スタイリング

#### 3. 認証状態の監視
- `onAuthStateChanged`で未ログイン時にリダイレクト
- IDトークン取得・保存

#### 4. ユーザー作成
- Firebase Consoleで妻・祖母のアカウント作成
- メールアドレス + パスワード設定

#### 5. デプロイ
```bash
firebase deploy --only hosting,auth
```

**工数見積: 半日**

### Phase 2: Cloud FunctionsでIDトークン検証

#### 1. Firebase Admin SDK追加
```bash
pip install firebase-admin
```

#### 2. `PWANotifier`でトークン検証
- 購読情報にIDトークンを含める
- Cloud FunctionsでIDトークン検証
- 検証成功時のみ通知送信

**工数見積: 2-3時間**

### Phase 3: UX改善

#### 1. パスワードリセット機能
```javascript
sendPasswordResetEmail(auth, email)
```

#### 2. ログアウトボタン
```javascript
signOut(auth)
```

#### 3. プロフィール画面
- ログインユーザー情報表示
- パスワード変更機能

**工数見積: 半日**

---

## セキュリティベストプラクティス

### 1. HTTPS必須
Firebase HostingはデフォルトでHTTPS。

### 2. Firebase Security Rules
```javascript
// firestore.rules (購読情報をFirestoreに保存する場合)
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /subscriptions/{userId} {
      // 自分の購読情報のみ読み書き可能
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

### 3. IDトークンの有効期限
- Firebase IDトークンは1時間で自動更新
- リフレッシュトークンで長期間ログイン状態保持

### 4. Secret Managerでの秘密鍵管理
```bash
# VAPID秘密鍵をSecret Managerで管理
gcloud secrets create school-agent-vapid-private-key \
  --data-file=vapid_private.pem \
  --replication-policy="automatic"
```

---

## まとめ

### 推奨構成: Firebase Authentication

**アクセス制限**:
- ログイン画面でメールアドレス + パスワード認証
- Firebase IDトークン(JWT)で本格的なセキュリティ
- ログアウト、パスワードリセット機能

**コスト**:
- 完全無料(月50,000回まで)
- ユーザー2名: **0円/月**

**実装工数**:
- Phase 1: 半日(ログイン画面)
- Phase 2: 2-3時間(トークン検証)
- **合計: 1日程度**

**Google Cloud統合**:
- Firebase Hosting + Firebase Authentication
- 既存GCPプロジェクトに統合
- Cloud Loggingで一元管理

---

## 参考資料

### Firebase Authentication
- [Use Firebase in a progressive web app (PWA)](https://firebase.google.com/docs/web/pwa)
- [Firebase Authentication 公式ドキュメント](https://firebase.google.com/docs/auth)
- [Security Rules and Firebase Authentication](https://firebase.google.com/docs/rules/rules-and-auth)

### Basic認証
- [Cloud Functions HTTP認証](https://cloud.google.com/functions/docs/securing/authenticating)

### セキュリティベストプラクティス
- [Firebase Security Rules](https://firebase.google.com/docs/rules/basics)
- [Manage User Sessions](https://firebase.google.com/docs/auth/admin/manage-sessions)
