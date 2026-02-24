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
        <main className="max-w-2xl mx-auto px-4 py-6 flex flex-col gap-6">
          <section>
            <h2 className="text-lg font-semibold text-gray-700 mb-3">
              お便りを登録
            </h2>
            <UploadArea onUploaded={handleUploaded} onError={handleError} />
            {successMsg && (
              <p className="mt-2 text-sm text-green-600">{successMsg}</p>
            )}
            {errorMsg && (
              <p className="mt-2 text-sm text-red-600">{errorMsg}</p>
            )}
          </section>

          <section>
            <h2 className="text-lg font-semibold text-gray-700 mb-3">
              登録済みドキュメント
            </h2>
            <div className="bg-white rounded-2xl shadow-sm p-4">
              <DocumentList refreshKey={refreshKey} />
            </div>
          </section>
        </main>
      </div>
    </AuthGuard>
  );
}
