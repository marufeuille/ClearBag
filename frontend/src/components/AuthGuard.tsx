"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { getFamily } from "@/lib/api";
import { ApiError } from "@/lib/api";

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * 認証済みかつアクティベート済みユーザーのみコンテンツを表示するガードコンポーネント。
 * 未認証の場合はトップページへリダイレクトする。
 * 未アクティベートの場合は「招待リンクが必要です」案内画面を表示する。
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [activationStatus, setActivationStatus] = useState<"checking" | "activated" | "not_activated">("checking");

  useEffect(() => {
    if (!loading && !user) {
      router.push("/");
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (!user) return;
    getFamily()
      .then(() => setActivationStatus("activated"))
      .catch((err) => {
        if (err instanceof ApiError && err.status === 403 && err.detail === "ACTIVATION_REQUIRED") {
          setActivationStatus("not_activated");
        } else {
          setActivationStatus("activated"); // その他エラーは各ページでハンドリング
        }
      });
  }, [user]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">読み込み中...</p>
      </div>
    );
  }

  if (!user) return null;

  if (activationStatus === "checking") {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">読み込み中...</p>
      </div>
    );
  }

  if (activationStatus === "not_activated") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="bg-white rounded-2xl shadow-sm p-8 max-w-sm w-full mx-4 text-center">
          <div className="w-14 h-14 rounded-2xl bg-blue-50 flex items-center justify-center mx-auto mb-4">
            <svg className="w-7 h-7 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-700 mb-2">招待リンクが必要です</h2>
          <p className="text-sm text-gray-500">
            ClearBag を利用するには、既存ユーザーからの招待リンクが必要です。
            招待メールを確認してリンクからアクセスしてください。
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
