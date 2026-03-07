/**
 * アプリ全体のスケルトン UI
 *
 * AuthGuard の認証・アクティベーション確認中に表示する。
 * NavBar（ヘッダー + ボトムナビ）の骨格とコンテンツプレースホルダーを
 * animate-pulse で表示し、FullScreenLoading（白地 + スピナー）より
 * 体感速度が速く見えるようにする。
 */

export function AppSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* トップヘッダー */}
      <header className="sticky top-0 z-30 bg-white border-b border-gray-100">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="h-6 w-28 rounded-lg bg-gray-100 animate-pulse" />
          <div className="h-6 w-16 rounded-lg bg-gray-100 animate-pulse" />
        </div>
      </header>

      {/* コンテンツエリア */}
      <main className="max-w-2xl mx-auto px-4 py-6 pb-24 flex flex-col gap-6">
        {/* アップロードエリア相当 */}
        <div className="h-44 rounded-2xl bg-gray-100 animate-pulse" />
        {/* ドキュメント一覧相当 */}
        <div className="flex flex-col gap-2">
          <div className="h-3 w-24 rounded bg-gray-100 animate-pulse" />
          <div className="rounded-2xl bg-white border border-gray-100 overflow-hidden divide-y divide-gray-50">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex items-center gap-3 px-5 py-4">
                <div className="w-9 h-9 rounded-xl bg-gray-100 animate-pulse flex-shrink-0" />
                <div className="flex-1 flex flex-col gap-1.5">
                  <div className="h-3 w-2/3 rounded bg-gray-100 animate-pulse" />
                  <div className="h-2.5 w-1/2 rounded bg-gray-100 animate-pulse" />
                </div>
                <div className="h-6 w-12 rounded-full bg-gray-100 animate-pulse" />
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* ボトムナビ */}
      <nav className="fixed bottom-0 inset-x-0 z-30 bg-white border-t border-gray-100">
        <div className="flex items-stretch max-w-2xl mx-auto h-16">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="flex-1 flex flex-col items-center justify-center gap-1.5 py-2">
              <div className="w-6 h-6 rounded-lg bg-gray-100 animate-pulse" />
              <div className="w-8 h-2 rounded bg-gray-100 animate-pulse" />
            </div>
          ))}
        </div>
      </nav>
    </div>
  );
}
