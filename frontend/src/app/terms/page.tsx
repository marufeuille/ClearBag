export default function TermsPage() {
  return (
    <main className="max-w-2xl mx-auto px-4 py-10">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">利用規約</h1>

      <div className="prose prose-sm text-gray-600 flex flex-col gap-4">
        <section>
          <h2 className="text-lg font-semibold text-gray-700">
            第1条（サービスの目的）
          </h2>
          <p>
            ClearBag（以下「本サービス」）は、学校配布物の内容をAIが自動解析し、
            カレンダー・タスクへの一括登録を支援するサービスです。
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">
            第2条（利用資格）
          </h2>
          <p>
            本サービスは、Googleアカウントを保有する方が利用できます。
            未成年者の方は保護者の同意を得た上でご利用ください。
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">
            第3条（禁止事項）
          </h2>
          <ul className="list-disc list-inside">
            <li>個人情報を含む文書の不正な共有・転載</li>
            <li>本サービスへの不正アクセス・リバースエンジニアリング</li>
            <li>その他法令に違反する行為</li>
          </ul>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">
            第4条（免責事項）
          </h2>
          <p>
            AIによる解析結果の正確性は保証されません。重要な日程や持ち物は
            必ず原本の配布物で確認してください。
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-gray-700">
            第5条（変更・終了）
          </h2>
          <p>
            本サービスの内容は予告なく変更または終了する場合があります。
          </p>
        </section>

        <p className="text-xs text-gray-400 mt-6">最終更新: 2026年2月</p>
      </div>
    </main>
  );
}
