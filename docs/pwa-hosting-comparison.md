# PWAホスティング先の比較 - コスト最適化

## 前提条件

### 想定利用状況
- **ユーザー数**: 2名(妻・祖母)
- **月間通知数**: 60通(1日1通×30日×2人)
- **月間アクセス**: 推定200-300リクエスト
- **データ転送量**: 推定1-2GB/月(PWAアプリ本体 + 通知配信)
- **ストレージ**: 10MB以下(HTML/CSS/JS + アイコン)

---

## 🥇 最推奨: Cloudflare Pages

### 料金
**完全無料**

### 無料枠の詳細
- ✅ **帯域幅**: 無制限!
- ✅ **リクエスト数**: 無制限!
- ✅ **サイト数**: 無制限!
- ✅ **カスタムドメイン**: 100個まで
- ✅ **CDN**: 全世界300+拠点に無料配信
- ⚠️ **ビルド数**: 月500回まで(十分)
- ⚠️ **同時ビルド**: 1つまで
- ⚠️ **ファイルサイズ**: 最大25MB/ファイル、最大20,000ファイル

### メリット
- 🎯 **帯域幅無制限が最大の強み**: ユーザー数が増えても追加コスト0円
- 🚀 **超高速CDN**: Cloudflareの世界最速級CDN
- 🔒 **無料SSL/HTTPS**: 自動取得・更新
- 🌐 **カスタムドメイン対応**: 独自ドメイン使用可能
- 🔄 **Git連携**: GitHub/GitLab連携で自動デプロイ
- 🛡️ **DDoS保護**: 無料で標準装備
- 📊 **Web Analytics**: 基本的なアクセス解析が無料

### デメリット
- ⚠️ **サーバーレス関数制限**: Workers(エッジ関数)は1日100,000リクエストまで無料
- ⚠️ **ビルド時間**: 複雑なビルドには不向き(PWAは影響なし)

### PWA対応
- ✅ Service Worker完全対応
- ✅ manifest.json対応
- ✅ HTTPS標準対応(PWA必須)
- ✅ Push API対応

### デプロイ方法
```bash
# Wranglerを使う場合
npm install -g wrangler
wrangler pages deploy ./dist

# または、GitHub連携で自動デプロイ
# 1. Cloudflare Dashboardでリポジトリ連携
# 2. ビルドコマンド設定
# 3. mainブランチへのpushで自動デプロイ
```

### 想定月額コスト
**0円** (無制限プラン)

---

## 🥈 次点: Vercel

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

## 🥉 3位: Firebase Hosting

### 料金
**Sparkプラン(無料)**

### 無料枠の詳細
- ✅ **ストレージ**: 10GB
- ✅ **データ転送**: 10GB/月
- ✅ **カスタムドメイン**: 対応
- ✅ **SSL証明書**: 自動
- ✅ **CDN**: Google Cloud CDN

### メリット
- 🔥 **Firebaseエコシステム**: Firestore, Auth, FCMと統合しやすい
- 📊 **Analytics**: Google Analyticsと統合
- 🔄 **バージョン管理**: 過去のデプロイ履歴を保持
- 🌐 **カスタムドメイン**: 簡単設定

### デメリット
- ❌ **転送量制限**: 10GB/月(超過時は従量課金)
- 💰 **超過時のコスト**: $0.15/GB(10GB超過ごとに約$1.50)
- ⚠️ **Blazeプランへの移行必要**: 無料枠超過時

### PWA対応
- ✅ Service Worker完全対応
- ✅ PWA公式ドキュメントあり
- ✅ manifest.json対応

### デプロイ方法
```bash
npm install -g firebase-tools
firebase login
firebase init hosting
firebase deploy
```

### 想定月額コスト
- **無料枠内**: 0円(転送量10GB未満)
- **超過時**: 約$0.15/GB × 超過GB数

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

| 項目 | Cloudflare Pages | Vercel | Firebase Hosting | GitHub Pages |
|------|------------------|--------|------------------|--------------|
| **月額基本料** | 0円 | 0円 | 0円 | 0円 |
| **帯域幅** | ∞ 無制限 | 100GB | 10GB | 100GB |
| **ストレージ** | 25MB/file | - | 10GB | 1GB |
| **カスタムドメイン** | ✅ | ✅ | ✅ | ✅ |
| **SSL/HTTPS** | ✅ 自動 | ✅ 自動 | ✅ 自動 | ✅ 自動 |
| **CDN速度** | ★★★★★ | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| **PWA対応** | ★★★★★ | ★★★★★ | ★★★★★ | ★★☆☆☆ |
| **デプロイ容易性** | ★★★★☆ | ★★★★★ | ★★★★☆ | ★★★☆☆ |
| **商用利用** | ✅ 可能 | ⚠️ 規約制限 | ✅ 可能 | ⚠️ 規約制限 |
| **超過時コスト** | 0円 | $20/月 | ~$0.15/GB | 制限あり |

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

### 構成
- **フロントエンド(PWA)**: Cloudflare Pages
- **バックエンド(通知送信)**: Cloud Functions gen2(既存)

### 月額コスト
| 項目 | コスト |
|------|--------|
| Cloudflare Pages | **0円** |
| Cloud Functions gen2 | **0円**(無料枠内) |
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

**🎯 最終決定: Cloudflare Pages + Cloud Functions gen2**

### 理由
1. **完全無料**: ユーザー2名の規模では永久に0円
2. **既存システムに統合**: 新規サービス不要、`PWANotifier`アダプタ追加のみ
3. **スケーラビリティ**: ユーザー100人まで無料枠内
4. **高パフォーマンス**: Cloudflare世界最速級CDN + Google Cloud Functions
5. **運用負荷ゼロ**: 自動スケーリング、自動SSL、`deploy_v2.sh`で自動デプロイ

### 実装ロードマップへの反映
- Phase 1に「Cloudflare Pagesへのデプロイ」を追加
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
