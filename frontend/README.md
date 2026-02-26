# ClearBag フロントエンド

Next.js 15 + Firebase Auth を使用した B2C Web アプリ。

## 開発環境セットアップ

```bash
npm install
npx playwright install chromium   # 初回のみ
```

## 開発サーバー起動

```bash
npm run dev        # http://localhost:3000
```

## テスト

### フロントエンド E2E テスト（Playwright）

```bash
npm run test:e2e
```

- Playwright が `next dev --port 3001` を自動起動（`NEXT_PUBLIC_E2E=true` で Firebase Auth をバイパス）
- API 呼び出しはテスト内で `page.route()` によりモック

#### テストケース

| ファイル | 説明 |
|---|---|
| `e2e/smoke.spec.ts` | 各ページがエラーなく表示されること（5ページ） |
| `e2e/dashboard.spec.ts` | ファイルアップロード後にドキュメント一覧が更新されること |

**カバーするページ:** `/dashboard` / `/calendar` / `/tasks` / `/profiles` / `/settings`

#### E2E モードの仕組み

`NEXT_PUBLIC_E2E=true` 環境変数をセットすると:

- `useAuth.ts`: `onAuthStateChanged` をスキップし、モックユーザーを即時返却
- `api.ts`: `getIdToken()` の代わりに固定トークン `"e2e-test-token"` を使用

実際の Firebase / バックエンド API への接続は一切行わない。

### バックエンド E2E テスト（Firestore Emulator）

```bash
# Docker で Firestore Emulator を起動
docker run -d -p 8080:8080 --name firestore-emulator \
  google/cloud-sdk:emulators \
  gcloud emulators firestore start --host-port=0.0.0.0:8080

# テスト実行（プロジェクトルートから）
FIRESTORE_EMULATOR_HOST=localhost:8080 uv run pytest tests/e2e/ -m e2e -v
```

## コミット前チェックリスト

frontend/ のコードを変更した場合は、コミット前に必ず以下を実行すること:

```bash
npm run test:e2e
```

## ビルド・デプロイ

```bash
npm run build           # 本番ビルド
npm run deploy          # Firebase Hosting へデプロイ
```
