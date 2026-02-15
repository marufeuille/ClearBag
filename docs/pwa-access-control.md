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
Firebase Authenticationで本格的なユーザー認証を実装。**Googleアカウントログイン + 許可リスト**で特定のアカウントのみアクセス可能にする。

### アーキテクチャ
```
ユーザー
  ↓ (Googleアカウントでログイン)
Firebase Authentication
  ↓ (許可リスト照合)
  ↓ (Firebase IDトークン発行)
PWA(Service Worker)
  ↓ (トークン検証)
Cloud Functions(通知送信)
```

### 認証方式の選択肢

#### 方式A: Googleアカウントログイン + 許可リスト(最推奨)
妻・祖母の既存Googleアカウントでログイン。事前に登録したメールアドレスのみ許可。

**メリット**:
- ✅ パスワード管理不要(Googleアカウントを使用)
- ✅ ログインが簡単(「Googleでログイン」ボタン)
- ✅ 許可リストで厳密に制御
- ✅ 2段階認証もGoogleアカウント側で対応

**デメリット**:
- ⚠️ Googleアカウントが必要(ほぼ全員が保有)

#### 方式B: メールアドレス + パスワード
専用のメールアドレス・パスワードを発行。

**メリット**:
- ✅ Googleアカウント不要

**デメリット**:
- ❌ パスワード管理が必要
- ❌ パスワードを忘れた場合の対応が必要

**結論**: 方式A(Googleアカウント + 許可リスト)を推奨

### 実装方法(Googleアカウント + 許可リスト)

#### 1. Firebase Authentication初期化

```bash
# Firebase Authenticationを有効化
firebase init auth
```

Firebase Consoleで設定:
1. Firebase Console → Authentication → Sign-in method
2. 「Google」を有効化
3. プロジェクトのサポートメール設定

#### 2. 許可リストの準備

**Google Sheetsに許可リスト追加**:
```
既存のGoogle Sheets(設定管理用)に新しいシート「allowed_users」を追加

| email | name | role |
|-------|------|------|
| wife@gmail.com | 妻 | user |
| grandma@gmail.com | 祖母 | user |
```

または、**Firestoreに保存**:
```javascript
// allowed_usersコレクション
{
  "wife@gmail.com": {
    "name": "妻",
    "role": "user",
    "created_at": "2026-01-01"
  },
  "grandma@gmail.com": {
    "name": "祖母",
    "role": "user",
    "created_at": "2026-01-01"
  }
}
```

#### 3. PWAにGoogleログイン画面を追加

```javascript
// login.js
import { initializeApp } from 'firebase/app';
import {
  getAuth,
  signInWithPopup,
  GoogleAuthProvider,
  onAuthStateChanged
} from 'firebase/auth';

// Firebase設定(既存のGCPプロジェクト)
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project",
};

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// Googleログイン処理
async function loginWithGoogle() {
  try {
    const result = await signInWithPopup(auth, provider);
    const user = result.user;

    // 許可リスト照合(Cloud Functionsで実施)
    const response = await fetch('/api/check-allowed-user', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${await user.getIdToken()}`
      },
      body: JSON.stringify({ email: user.email })
    });

    if (!response.ok) {
      // 許可されていないユーザー
      await auth.signOut();
      alert('このアカウントは許可されていません');
      return;
    }

    // ログイン成功 → メイン画面へ
    window.location.href = '/main.html';

  } catch (error) {
    console.error('ログイン失敗:', error);
    alert('ログインに失敗しました');
  }
}

// 認証状態の監視
onAuthStateChanged(auth, async (user) => {
  if (!user) {
    // 未ログイン → ログイン画面へリダイレクト
    if (window.location.pathname !== '/login.html') {
      window.location.href = '/login.html';
    }
  } else {
    // ログイン済み → 許可リスト照合
    const response = await fetch('/api/check-allowed-user', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${await user.getIdToken()}`
      },
      body: JSON.stringify({ email: user.email })
    });

    if (!response.ok) {
      // 許可リストにない
      await auth.signOut();
      window.location.href = '/login.html';
    }
  }
});
```

#### 4. ログイン画面HTML

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
    <h1>📚 学校通知アプリ</h1>
    <p>保護者専用ページ</p>
    <button id="google-login-btn" class="google-btn">
      <img src="/google-icon.svg" alt="Google">
      Googleでログイン
    </button>
  </div>
  <script type="module" src="/login.js"></script>
  <script>
    document.getElementById('google-login-btn').addEventListener('click', loginWithGoogle);
  </script>
</body>
</html>
```

```css
/* styles.css */
.login-container {
  max-width: 400px;
  margin: 100px auto;
  padding: 40px;
  text-align: center;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.google-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 12px 24px;
  font-size: 16px;
  border: 1px solid #ddd;
  border-radius: 5px;
  background: white;
  cursor: pointer;
  transition: background 0.2s;
}

.google-btn:hover {
  background: #f8f8f8;
}

.google-btn img {
  width: 20px;
  height: 20px;
}
```

#### 5. Cloud Functionsで許可リスト照合API作成

```python
# v2/entrypoints/pwa_auth.py
import functions_framework
from firebase_admin import auth, initialize_app
from flask import jsonify, request
import os

# Firebase Admin SDK初期化
initialize_app()

# 許可リスト(Google Sheetsから取得、またはハードコード)
ALLOWED_EMAILS = [
    "wife@gmail.com",
    "grandma@gmail.com"
]

# または、Google Sheetsから動的に取得
def get_allowed_emails():
    """Google Sheetsから許可リストを取得"""
    # 既存のConfigSourceを使用
    from v2.adapters.sheets import GoogleSheetsConfigSource

    spreadsheet_id = os.environ.get("SPREADSHEET_ID")
    config = GoogleSheetsConfigSource(spreadsheet_id)
    # allowed_usersシートから取得
    # 実装は省略
    return ALLOWED_EMAILS

@functions_framework.http
def check_allowed_user(request):
    """
    許可リスト照合API

    Authorization: Bearer <Firebase ID Token>
    """
    # CORS対応
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST',
            'Access-Control-Allow-Headers': 'Authorization, Content-Type',
        }
        return ('', 204, headers)

    # IDトークン検証
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Unauthorized'}), 401

    id_token = auth_header.split('Bearer ')[1]

    try:
        # Firebase IDトークン検証
        decoded_token = auth.verify_id_token(id_token)
        email = decoded_token.get('email')

        # 許可リスト照合
        allowed_emails = get_allowed_emails()

        if email in allowed_emails:
            return jsonify({
                'allowed': True,
                'email': email,
                'name': decoded_token.get('name')
            }), 200
        else:
            return jsonify({'error': 'Not allowed'}), 403

    except Exception as e:
        print(f"Token verification failed: {e}")
        return jsonify({'error': 'Invalid token'}), 401
```

#### 6. Cloud Functionsデプロイ

```bash
# deploy_pwa_auth.sh
gcloud functions deploy check-allowed-user \
  --gen2 \
  --runtime=python313 \
  --region=asia-northeast1 \
  --source=. \
  --entry-point=check_allowed_user \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars SPREADSHEET_ID=$SPREADSHEET_ID
```

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
- ✅ **Googleアカウントログイン**: パスワード管理不要、ログインが簡単
- ✅ **許可リスト制御**: 事前登録したメールアドレスのみアクセス可能
- ✅ **本格的なセキュリティ**: Firebase IDトークン(JWT)で認証
- ✅ **Google Cloud統一**: 既存のGCPプロジェクトに統合
- ✅ **ログイン状態保持**: リフレッシュトークンで自動更新(1時間有効)
- ✅ **ログアウト機能**: `signOut()`で明示的にログアウト可能
- ✅ **2段階認証**: Googleアカウント側で設定可能
- ✅ **ユーザー管理**: Google Sheetsで許可リスト管理

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

## 最終推奨: Firebase Authentication(Googleログイン + 許可リスト)

### 決定理由

#### 1. 最も簡単なログイン体験
- **「Googleでログイン」ボタン1つ**: パスワード入力不要
- **既存のGoogleアカウント使用**: 妻・祖母のGmailアカウントで即ログイン
- **パスワード管理不要**: Googleアカウントのパスワードを使用

#### 2. 厳密なアクセス制御
- **許可リスト照合**: 事前登録したメールアドレスのみアクセス可能
- **Google Sheetsで管理**: 許可リストの追加・削除が簡単
- **不正アクセス防止**: 許可リストにないGoogleアカウントは即ログアウト

#### 3. Google Cloud完全統合
- 既存のGCPプロジェクトに統合
- Firebase Hosting + Firebase Authで一元管理
- Cloud Functionsで許可リスト照合

#### 4. セキュリティ
- Firebase IDトークン(JWT)で本格的な認証
- HTTPS通信で暗号化
- トークンの自動更新(1時間有効)
- 2段階認証(Googleアカウント側で設定可能)

#### 5. ユーザー体験
- ログインが超簡単(ボタン1回クリック)
- ログアウト機能あり
- ログイン状態保持(リフレッシュトークン)

#### 6. 拡張性
- 許可リストにメールアドレス追加で即座にユーザー追加可能
- 将来的に他の認証プロバイダー追加可能(Apple, Microsoft等)
- Firebase Consoleでログイン履歴確認

#### 7. コスト
- 完全無料(月50,000回まで)
- 2ユーザーの場合、永久に0円

---

## 実装ロードマップ

### Phase 1: Firebase Authentication基本実装(Googleログイン + 許可リスト)

#### 1. Firebase Authentication有効化
```bash
firebase init auth
```

Firebase Consoleで設定:
- Authentication → Sign-in method → Googleを有効化

#### 2. 許可リストの準備
Google Sheetsに`allowed_users`シート追加:
```
| email | name | role |
|-------|------|------|
| wife@gmail.com | 妻 | user |
| grandma@gmail.com | 祖母 | user |
```

#### 3. ログイン画面作成
- `login.html` - Googleログインボタン
- `login.js` - Firebase Auth + Google Provider統合
- `styles.css` - スタイリング

#### 4. Cloud Functionsで許可リスト照合API作成
- `v2/entrypoints/pwa_auth.py` - `/api/check-allowed-user`
- Firebase IDトークン検証 + 許可リスト照合

#### 5. デプロイ
```bash
# Firebase Hosting
firebase deploy --only hosting,auth

# Cloud Functions(許可リスト照合API)
gcloud functions deploy check-allowed-user \
  --gen2 \
  --runtime=python313 \
  --region=asia-northeast1 \
  --source=. \
  --entry-point=check_allowed_user \
  --trigger-http \
  --allow-unauthenticated
```

#### 6. ユーザーテスト
1. 妻・祖母にPWAのURLを共有
2. 「Googleでログイン」ボタンをクリック
3. Googleアカウント選択
4. 許可リスト照合 → ログイン成功!

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
