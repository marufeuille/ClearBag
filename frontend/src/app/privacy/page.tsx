export default function PrivacyPage() {
  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">
        プライバシーポリシー
      </h1>

      <div className="prose prose-sm text-gray-600 flex flex-col gap-4">
        <section>
          <h2 className="text-lg font-semibold text-gray-700">
            収集する情報
          </h2>
          <ul className="list-disc list-inside">
            <li>Googleアカウント情報（メールアドレス・表示名）</li>
            <li>アップロードされた文書ファイル</li>
            <li>AIによる解析結果（イベント・タスク情報）</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">情報の利用目的</h2>
          <ul className="list-disc list-inside">
            <li>サービスの提供・改善</li>
            <li>AI解析処理（Google Vertex AI Gemini を使用）</li>
            <li>通知メール・プッシュ通知の送信</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">第三者提供</h2>
          <p>
            法令に基づく場合を除き、ユーザーの同意なく個人情報を第三者に提供しません。
            ただし、Google Cloud Platform（Firebase・Vertex AI・Cloud Storage等）
            のサービスにデータを送信・保存します。
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">データの保管</h2>
          <p>
            アップロードされたファイルおよび解析結果はGoogle Cloud Storage /
            Firestoreに保存されます。アカウント削除時にすべてのデータを削除します。
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">お問い合わせ</h2>
          <p>
            プライバシーに関するお問い合わせは、サービス内のフィードバック
            フォームよりご連絡ください。
          </p>
        </section>

        <p className="text-xs text-gray-400 mt-6">最終更新: 2026年2月</p>
      </div>
    </main>
  );
}
