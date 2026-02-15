# PWAホスティング先の比較 - コスト最適化

## 前提条件

### 想定利用状況
- **ユーザー数**: 2名(妻・祖母)
- **月間通知数**: 60通(1日1通×30日×2人)
- **月間アクセス**: 推定200-300リクエスト
- **データ転送量**: 推定1-2GB/月(PWAアプリ本体 + 通知配信)
- **ストレージ**: 10MB以下(HTML/CSS/JS + アイコン)

---

## 🥇 最推奨: Firebase Hosting(Google Cloud統一案)

### 料金
**Sparkプラン(無料)**

### 無料枠の詳細
- ✅ **ストレージ**: 10GB
- ✅ **データ転送**: 10GB/月
- ✅ **カスタムドメイン**: 対応
- ✅ **SSL証明書**: 自動発行・更新
- ✅ **CDN**: Google Cloud CDN(世界中の拠点)
- ✅ **PWA専用機能**: URL rewrite, カスタムヘッダー、ローカライゼーション
- ✅ **Firebase統合**: Firestore, Auth, Cloud Functionsと完全統合

### メリット
- 🎯 **Google Cloud完全統合**: Cloud Functions gen2と同じGCPプロジェクト
- 🔑 **認証情報の統一**: 同じサービスアカウント、Secret Manager
- 📊 **ログの一元管理**: Cloud Loggingで全て統合
- 🚀 **PWA専用設計**: Service Worker、Push API、manifest.json最適化
- 🔒 **無料SSL/HTTPS**: 自動取得・更新
- 🔄 **Git連携**: GitHub Actions + Firebase CLI で自動デプロイ
- 🌐 **カスタムドメイン**: 独自ドメイン使用可能
- 📱 **Firebase連携**: 将来的にFirestore(購読情報保存)やAuthを追加しやすい

### デメリット
- ⚠️ **転送量制限**: 10GB/月(超過時は従量課金)
- 💰 **超過時のコスト**: $0.15/GB(10GB超過ごとに約$1.50)

### 想定コスト(ユーザー2人の場合)
- **月間転送量**: 推定1-2GB(PWAアプリ本体 + 通知配信)
- **コスト**: **0円/月**(10GB無料枠内)

### PWA対応
- ✅ **Service Worker完全対応**
- ✅ **manifest.json対応**
- ✅ **HTTPS標準対応**(PWA必須)
- ✅ **Push API対応**
- ✅ **公式PWAドキュメント**: [Firebase PWA Guide](https://firebase.google.com/docs/hosting)

### デプロイ方法
```bash
# Firebase CLI インストール
npm install -g firebase-tools

# Firebaseプロジェクト初期化(既存GCPプロジェクトと紐付け)
firebase login
firebase init hosting
# → 既存のGCPプロジェクトIDを選択

# デプロイ
firebase deploy --only hosting

# または、GitHub Actions で自動デプロイ
# .github/workflows/deploy-pwa.yml に設定
```

### Google Cloud統一のメリット

#### 1. 認証情報の統一
```bash
# 同じサービスアカウントを使用
SERVICE_ACCOUNT_EMAIL=$(grep -o '"client_email": "[^"]*' service_account.json | cut -d'"' -f4)

# Firebase HostingもCloud Functionsも同じ権限で管理
```

#### 2. ログの一元管理
- Cloud Loggingで全てのログを統合表示
- PWAアクセスログ + Cloud Functionsログを一箇所で確認

#### 3. Secret Managerの統合
```bash
# 既存のSecret Manager設定をそのまま使用
VAPID_PRIVATE_KEY_SECRET="school-agent-vapid-private-key"

# Firebase HostingからもSecret Manager経由でVAPID鍵を参照可能
```

#### 4. IAM権限の統一
- 同じGCPプロジェクト内で完結
- 権限管理が一元化

### 想定月額コスト
**0円** (無料枠10GB内)

---

## 🥈 次点: Cloudflare Pages

### 料金
**完全無料**

### 無料枠の詳細
- ✅ **帯域幅**: 無制限!
- ✅ **リクエスト数**: 無制限!
- ✅ **サイト数**: 無制限!
- ✅ **カスタムドメイン**: 100個まで
- ✅ **CDN**: 全世界300+拠点に無料配信

### メリット
- 🎯 **帯域幅無制限が最大の強み**: ユーザー数が増えても追加コスト0円
- 🚀 **超高速CDN**: Cloudflareの世界最速級CDN
- 🔒 **無料SSL/HTTPS**: 自動取得・更新
- 🔄 **Git連携**: GitHub/GitLab連携で自動デプロイ

### デメリット
- ❌ **別サービス管理**: Google Cloudと別アカウント、別認証
- ⚠️ **ログ分散**: Firebase HostingとCloudflare Pagesで別々のダッシュボード

### 想定月額コスト
**0円** (無制限プラン)

---

## 🥉 3位: Vercel

### 料金
**Hobby(無料)プラン**

### 無料枠の詳細
- ✅ **帯域幅**: 100GB/月
- ✅ **サーバーレス関数実行**: 100GB-Hours/月
- ✅ **サーバーレス関数実行時間**: 10秒/実行
- ✅ **ビルド**: 6,000分/月
- ✅ **カスタムドメイン**: 対応
- ⚠️ **商用利用**: 個人プロジェクトのみ(規約上)

### メリット
- 🚀 **デプロイが超簡単**: Git pushだけで自動デプロイ
- 📱 **プレビューURL**: PRごとに自動生成
- 🔄 **ゼロダウンタイムデプロイ**: ロールバックも簡単
- 🌐 **Edge Network**: 世界中に高速配信
- 📊 **Analytics**: Web Vitals含む詳細な解析(有料)

### デメリット
- ❌ **帯域幅制限**: 100GB/月(超過時は有料プランへ移行必須)
- ⚠️ **商用利用制限**: 規約上、個人・趣味プロジェクト限定
- 💰 **超過時のコスト**: Pro($20/月)へのアップグレード必須

### PWA対応
- ✅ Service Worker完全対応
- ✅ manifest.json対応
- ✅ HTTPS標準対応

### デプロイ方法
```bash
# Vercel CLIを使う場合
npm install -g vercel
vercel --prod

# または、GitHub連携で自動デプロイ
# 1. vercel.comでGitHubリポジトリ連携
# 2. 自動ビルド・デプロイ
```

### 想定月額コスト
- **無料枠内**: 0円(帯域幅100GB未満)
- **超過時**: $20/月(Proプラン)

---

## ❌ 非推奨: GitHub Pages

### 料金
**完全無料**

### 無料枠の詳細
- ✅ **帯域幅**: 100GB/月(ソフトリミット)
- ✅ **ストレージ**: 1GB
- ✅ **カスタムドメイン**: 対応
- ⚠️ **ビルド**: 1時間に10回まで

### メリット
- 💰 **完全無料**: GitHubアカウントがあれば利用可能
- 🔄 **Git連携**: リポジトリpushで自動デプロイ
- 🌐 **カスタムドメイン**: 対応

### デメリット
- ❌ **PWA制約が多い**: サブディレクトリホスティング時のService Workerスコープ問題
- ❌ **パフォーマンス**: CDNがCloudflare/Vercelより遅い
- ❌ **ビルド機能弱い**: GitHub Actionsを別途設定する必要
- ⚠️ **商用利用制限**: 規約上、ビジネス利用は推奨されない

### PWA対応
- ⚠️ **Service Worker**: スコープ設定に注意(`/<repo>/`など)
- ⚠️ **manifest.json**: パス設定が複雑
- ✅ **HTTPS**: 標準対応

### 想定月額コスト
**0円**

---

## 詳細比較表

| 項目 | Firebase Hosting | Cloudflare Pages | Vercel | GitHub Pages |
|------|------------------|------------------|--------|--------------|
| **月額基本料** | 0円 | 0円 | 0円 | 0円 |
| **帯域幅** | 10GB | ∞ 無制限 | 100GB | 100GB |
| **ストレージ** | 10GB | 25MB/file | - | 1GB |
| **GCP統合** | ✅ 完全統合 | ❌ 別サービス | ❌ 別サービス | ❌ 別サービス |
| **認証情報** | ✅ 統一 | ❌ 別アカウント | ❌ 別アカウント | ❌ 別アカウント |
| **ログ管理** | ✅ Cloud Logging | ❌ 分散 | ❌ 分散 | ❌ 分散 |
| **SSL/HTTPS** | ✅ 自動 | ✅ 自動 | ✅ 自動 | ✅ 自動 |
| **CDN速度** | ★★★★☆ | ★★★★★ | ★★★★★ | ★★★☆☆ |
| **PWA対応** | ★★★★★ | ★★★★★ | ★★★★★ | ★★☆☆☆ |
| **商用利用** | ✅ 可能 | ✅ 可能 | ⚠️ 規約制限 | ⚠️ 規約制限 |
| **超過時コスト** | ~$0.15/GB | 0円 | $20/月 | 制限あり |

---

## 最終推奨: Cloudflare Pages

### 決定理由

1. **完全無料かつ無制限**
   - 帯域幅無制限 = ユーザー数増加に対応可能
   - 追加コストのリスクゼロ

2. **PWA完全対応**
   - Service Worker、manifest.json問題なし
   - HTTPSデフォルト

3. **世界最速級CDN**
   - 300+拠点の配信網
   - レイテンシ最小

4. **商用利用可能**
   - 規約上の制限なし
   - 安心して運用できる

5. **運用コストゼロ**
   - DDoS保護、Web Analytics含めて完全無料
   - 保守コストなし

### デプロイ手順(詳細)

#### 1. Cloudflareアカウント作成
https://dash.cloudflare.com/sign-up

#### 2. GitHubリポジトリ作成
```bash
# PWAプロジェクトのディレクトリ構造
pwa-notification/
├── index.html
├── manifest.json
├── service-worker.js
├── app.js
├── style.css
└── icons/
    ├── icon-192.png
    └── icon-512.png
```

#### 3. Cloudflare Pagesに接続
1. Cloudflare Dashboard → Pages → Create a project
2. Connect to Git → GitHubリポジトリ選択
3. ビルド設定:
   - **Framework preset**: None
   - **Build command**: (空欄) ※静的ファイルの場合
   - **Build output directory**: `/` または `/dist`
4. Deploy!

#### 4. カスタムドメイン設定(任意)
1. Pages → Custom domains → Set up a custom domain
2. DNS設定でCNAMEレコード追加
3. SSL自動発行(数分で完了)

---

## バックエンド(Python)のデプロイ先

PWAのフロントエンドはCloudflare Pages、バックエンド(プッシュ通知送信)は別途必要。

### 推奨: Cloud Functions gen2(Google Cloud) - **既存実装を拡張**

#### 現状
- **既にCloud Functions gen2で稼働中**: `school-agent-v2`
- **エントリーポイント**: `v2/entrypoints/cloud_function.py`
- **デプロイスクリプト**: `deploy_v2.sh`

#### 料金
- **無料枠**: 月200万リクエストまで無料
- **CPU時間**: 月40万GB秒まで無料
- **ネットワーク**: 月5GB Egress無料

#### 想定コスト
- **月60通の通知送信**: 完全無料枠内
- **月間実行時間**: 推定60秒(1通1秒 × 60通) → 無料枠の0.0015%

#### メリット
- ✅ **既存システムに統合**: 新規デプロイ不要、同じFunctionに機能追加するだけ
- ✅ **自動スケーリング**: リクエスト数に応じて自動拡張
- ✅ **Python完全対応**: pywebpushライブラリ利用可能
- ✅ **秘密情報管理**: Secret Manager統合済み
- ✅ **ログ統合**: Cloud Loggingで既存ログと一元管理

#### 実装方針
既存の`Notifier`ポートに`PWANotifier`を追加するだけ:

```python
# v2/adapters/pwa_notifier.py
from pywebpush import webpush
from v2.domain.ports import Notifier

class PWANotifier(Notifier):
    def __init__(self, vapid_private_key: str, vapid_claims: dict, subscriptions: list[dict]):
        self._vapid_key = vapid_private_key
        self._vapid_claims = vapid_claims
        self._subscriptions = subscriptions

    def notify_file_processed(self, filename, summary, events, tasks, file_link):
        # Web Push送信処理
        ...
```

既存の`deploy_v2.sh`で自動デプロイされる。

#### Cloud Runとの比較

| 項目 | Cloud Functions gen2 | Cloud Run |
|------|---------------------|-----------|
| **既存統合** | ✅ 既に使用中 | ❌ 新規構築必要 |
| **デプロイ** | ✅ `deploy_v2.sh`で自動 | ❌ Dockerfile作成必要 |
| **コード変更** | ✅ アダプタ追加のみ | ❌ コンテナ化必要 |
| **無料枠** | 200万req/月 | 200万req/月 |
| **起動速度** | ★★★★☆ | ★★★★★ |
| **適用ケース** | HTTP関数 | コンテナ全般 |

**結論**: Cloud Functions gen2で十分。わざわざCloud Runに移行する理由なし。

---

## 総合コスト見積もり

### 構成(Google Cloud統一)
- **フロントエンド(PWA)**: Firebase Hosting
- **バックエンド(通知送信)**: Cloud Functions gen2(既存)
- **購読情報保存**: Google Sheets(既存) or Firestore(将来)
- **秘密鍵管理**: Secret Manager(既存)

### 月額コスト
| 項目 | コスト |
|------|--------|
| Firebase Hosting | **0円**(10GB無料枠内) |
| Cloud Functions gen2 | **0円**(200万req無料枠内) |
| Google Sheets API | **0円**(既存利用) |
| Secret Manager | **0円**(既存利用) |
| **合計** | **0円/月** |

### スケーリング時のコスト予測

#### ユーザー数が10人に増えた場合
- 月間通知数: 300通(1日1通×30日×10人)
- Cloud Run実行時間: 300秒/月
- **コスト**: 依然として無料枠内(**0円**)

#### ユーザー数が100人に増えた場合
- 月間通知数: 3,000通
- Cloud Run実行時間: 3,000秒/月(50分)
- **コスト**: 依然として無料枠内(**0円**)

#### ユーザー数が1,000人に増えた場合
- 月間通知数: 30,000通
- Cloud Run実行時間: 30,000秒/月(8.3時間)
- **コスト**: 無料枠超過、推定 **$1-2/月**

---

## まとめ

**🎯 最終決定: Firebase Hosting + Cloud Functions gen2 (Google Cloud統一)**

### 理由
1. **Google Cloud完全統合**: 全てのサービスが同じGCPプロジェクト内
2. **運用管理の一元化**:
   - 認証情報: 同じサービスアカウント
   - ログ: Cloud Loggingで一元管理
   - 権限: IAMで統一管理
   - Secret Manager: VAPID鍵も同じSecret Managerで管理
3. **完全無料**: ユーザー2名の規模では永久に0円(10GB無料枠内)
4. **既存システムに統合**: Cloud Functions gen2に`PWANotifier`追加のみ
5. **PWA専用設計**: Firebase HostingはPWAに最適化済み
6. **拡張性**: 将来的にFirestore(購読情報)やAuth追加が容易

### Google Cloud統一の具体的メリット

#### 運用面
- ダッシュボード1つで全て管理(GCP Console)
- ログ検索が統一(Cloud Logging)
- アラート設定が統一(Cloud Monitoring)
- コスト管理が統一(Cloud Billing)

#### セキュリティ面
- サービスアカウント1つで完結
- Secret Manager統一(VAPID鍵、Slack Token等)
- IAM権限の一元管理
- 監査ログの統合

#### 開発面
- デプロイスクリプトの統一(`deploy_v2.sh`に追加)
- 環境変数の統一管理
- CI/CDパイプラインの統合

### 実装ロードマップへの反映
- Phase 1に「Firebase Hostingへのデプロイ」を追加
- バックエンドは「既存Cloud Functionsに`PWANotifier`追加」のみ

---

## 参考資料

### Cloudflare Pages
- [Cloudflare Pages 公式ドキュメント](https://developers.cloudflare.com/pages/)
- [Cloudflare Pagesの制限事項まとめ](https://www.serversus.work/topics/46jju7q0czyqlqis33e6/)
- [個人開発に役立つ Cloudflare Pages 無料枠でHPコストゼロ運用](https://izanami.dev/post/b0f59b2e-dd6b-4352-af1d-ae14f7cec707)

### Vercel
- [Vercel 料金プラン](https://vercel.com/pricing)
- [NetlifyとVercelの特徴と優位性について](https://qiita.com/GS-AI/items/c9fcf73bac2e10793406)

### Firebase Hosting
- [Firebase Hosting 料金](https://firebase.google.com/pricing)
- [Learn about usage levels, quotas, and pricing for Hosting](https://firebase.google.com/docs/hosting/usage-quotas-pricing)

### GitHub Pages PWA
- [Turning a GitHub page into a Progressive Web App](https://christianheilmann.com/2022/01/13/turning-a-github-page-into-a-progressive-web-app/)
- [ServiceWorker for github pages](https://gist.github.com/kosamari/7c5d1e8449b2fbc97d372675f16b566e)

### 比較記事
- [Awesome Web Hosting 2026](https://github.com/iSoumyaDey/Awesome-Web-Hosting-2026)
- [Cloudflare Pages・Vercel ・Netlify の違いや使い分けをまとめる](https://zenn.dev/catnose99/scraps/6780379210136f)
