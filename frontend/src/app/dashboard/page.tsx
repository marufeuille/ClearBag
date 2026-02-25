"use client";

import { useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { NavBar } from "@/components/NavBar";
import { UploadArea } from "@/components/UploadArea";
import { DocumentList } from "@/components/DocumentList";

export default function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const handleUploaded = () => {
    setSuccessMsg("解析キューに登録しました。数分後に結果が表示されます。");
    setErrorMsg(null);
    setRefreshKey((k) => k + 1);
    setTimeout(() => setSuccessMsg(null), 5000);
  };

  const handleError = (msg: string) => {
    setErrorMsg(msg);
    setSuccessMsg(null);
  };

  return (
    <AuthGuard>
      <div className="min-h-screen bg-gray-50">
        <NavBar />

        <main className="max-w-2xl mx-auto px-4 py-6 pb-nav flex flex-col gap-6">
          {/* アップロードセクション */}
          <section>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
              お便りを登録
            </h2>
            <UploadArea onUploaded={handleUploaded} onError={handleError} />

            {successMsg && (
              <div className="mt-3 flex items-center gap-2 text-sm text-green-700 bg-green-50 rounded-xl px-4 py-3 border border-green-100">
                <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                {successMsg}
              </div>
            )}
            {errorMsg && (
              <div className="mt-3 flex items-center gap-2 text-sm text-red-700 bg-red-50 rounded-xl px-4 py-3 border border-red-100">
                <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {errorMsg}
              </div>
            )}
          </section>

          {/* ドキュメント一覧セクション */}
          <section>
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
              登録済みドキュメント
            </h2>
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <DocumentList refreshKey={refreshKey} />
            </div>
          </section>
        </main>
      </div>
    </AuthGuard>
  );
}
