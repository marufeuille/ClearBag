export default function PrivacyPage() {
  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">
        プライバシーポリシー
      </h1>

      <div className="prose prose-sm text-gray-600 flex flex-col gap-4">
        <section>
          <h2 className="text-lg font-semibold text-gray-700">収集する情報</h2>
          <ul className="list-disc list-inside space-y-1">
            <li>Googleアカウント情報（メールアドレス・表示名）</li>
            <li>アップロードされた文書ファイル（PDF・画像）</li>
            <li>AIによる解析結果（イベント・タスク情報）</li>
            <li>利用状況データ（ページ閲覧・操作ログ）</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">情報の利用目的</h2>
          <ul className="list-disc list-inside space-y-1">
            <li>サービスの提供・改善</li>
            <li>AI解析処理（Google Vertex AI Gemini を使用）</li>
            <li>通知・プッシュ通知の送信</li>
            <li>利用状況の分析・サービス改善（Google Analytics 4 を使用）</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">外部サービスへのデータ送信</h2>
          <p className="mb-2">以下の外部サービスにデータを送信・処理します。</p>
          <ul className="list-disc list-inside space-y-1">
            <li>
              <strong>Vertex AI Gemini</strong>（Google Cloud）:
              アップロードされた文書の解析に使用します。
            </li>
            <li>
              <strong>Google Analytics 4</strong>:
              ページ閲覧・操作イベントを収集します。氏名・メールアドレス等の直接的な個人情報は含みません。
            </li>
            <li>
              <strong>Firebase Authentication</strong>:
              Googleアカウントによる認証に使用します。
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">データの保存場所・保持期間</h2>
          <ul className="list-disc list-inside space-y-1">
            <li>
              <strong>保存場所</strong>: Google Cloud Platform（リージョン: asia-northeast1 / us-central1）
            </li>
            <li>
              <strong>アップロードファイル（GCS）</strong>: アカウント削除時に削除します。
            </li>
            <li>
              <strong>解析結果・設定（Firestore）</strong>: アカウント削除時に削除します。
            </li>
            <li>
              <strong>行動ログ（BigQuery）</strong>:
              uid・family_id・トークン使用量等の匿名化された利用ログを保持します。メールアドレス等の直接的な個人情報は含みません。
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">Cookie・トラッキング</h2>
          <ul className="list-disc list-inside space-y-1">
            <li>
              <strong>Firebase Authentication</strong>:
              ログインセッションの維持にCookieを使用します。
            </li>
            <li>
              <strong>Google Analytics 4</strong>:
              利用状況の分析のためCookieおよびローカルストレージを使用します。
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">ユーザーの権利</h2>
          <ul className="list-disc list-inside space-y-1">
            <li>
              <strong>アクセス権</strong>:
              サービス内でご自身のデータを閲覧できます。
            </li>
            <li>
              <strong>削除権</strong>:
              設定画面の「アカウントを削除」からアカウントと全データを削除できます。
              削除時、アップロードファイル・解析結果・プロファイル・タスク・イベントがすべて削除されます。
            </li>
            <li>
              <strong>ポータビリティ権</strong>:
              将来的な対応を予定しています。
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">第三者提供</h2>
          <p>
            法令に基づく場合を除き、ユーザーの同意なく個人情報を第三者に提供しません。
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">お問い合わせ</h2>
          <p>
            プライバシーに関するお問い合わせは、サービス内のフィードバックフォームよりご連絡ください。
          </p>
        </section>

        <p className="text-xs text-gray-400 mt-6">最終更新: 2026年3月</p>
      </div>
    </main>
  );
}
