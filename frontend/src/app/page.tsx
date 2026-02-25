"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export default function HomePage() {
  const { user, loading, signIn } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user) {
      router.push("/dashboard");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-50">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-500 border-t-transparent" />
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <div className="flex flex-col items-center justify-center min-h-screen px-6 py-16 text-center">

        {/* ロゴマーク */}
        <div className="mb-6">
          <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-blue-600 shadow-xl shadow-blue-200">
            <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
        </div>

        <h1 className="text-5xl font-extrabold text-gray-900 tracking-tight">
          Clear<span className="text-blue-600">Bag</span>
        </h1>
        <p className="mt-4 text-lg text-gray-500 max-w-xs leading-relaxed">
          学校のお便りをAIが読み取り
          <br />
          カレンダーとタスクに自動登録
        </p>

        {/* 機能ハイライト */}
        <div className="mt-12 grid grid-cols-3 gap-4 max-w-xs w-full">
          {[
            { emoji: "📸", label: "写真を撮るだけ" },
            { emoji: "✨", label: "AIが自動解析" },
            { emoji: "📅", label: "カレンダー連携" },
          ].map(({ emoji, label }) => (
            <div
              key={label}
              className="flex flex-col items-center gap-2 bg-white/70 rounded-2xl p-3 shadow-sm border border-white"
            >
              <span className="text-2xl">{emoji}</span>
              <span className="text-xs text-gray-600 font-medium leading-tight text-center">
                {label}
              </span>
            </div>
          ))}
        </div>

        {/* サインインボタン */}
        <div className="mt-10 w-full max-w-xs flex flex-col gap-4">
          <button
            onClick={signIn}
            className="group flex items-center justify-center gap-3 w-full rounded-2xl bg-white px-6 py-4 shadow-md border border-gray-100 font-semibold text-gray-700 transition-all hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0 active:shadow-sm"
          >
            <GoogleIcon />
            Google でサインイン
          </button>

          <p className="text-xs text-gray-400">
            無料プランで月5枚まで解析できます
          </p>
          <p className="text-xs text-gray-400">
            <a href="/terms" className="hover:text-gray-600 transition-colors">利用規約</a>
            <span className="mx-1.5">·</span>
            <a href="/privacy" className="hover:text-gray-600 transition-colors">プライバシーポリシー</a>
          </p>
        </div>
      </div>
    </main>
  );
}

function GoogleIcon() {
  return (
    <svg className="h-5 w-5 flex-shrink-0" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
    </svg>
  );
}
