"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { joinFamily, ApiError } from "@/lib/api";

type JoinStatus = "idle" | "joining" | "success" | "invalid_token" | "expired" | "email_mismatch" | "error";

function InviteContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");
  const { user, loading, signIn } = useAuth();
  const [status, setStatus] = useState<JoinStatus>("idle");
  const [familyName, setFamilyName] = useState("");

  useEffect(() => {
    if (!token || !user || status !== "idle") return;
    setStatus("joining");
    joinFamily(token)
      .then((result) => {
        setFamilyName(result.name);
        setStatus("success");
        setTimeout(() => router.push("/dashboard"), 2000);
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError) {
          if (err.status === 404) setStatus("invalid_token");
          else if (err.status === 400) setStatus("expired");
          else if (err.status === 403 && err.detail === "EMAIL_MISMATCH") setStatus("email_mismatch");
          else setStatus("error");
        } else {
          setStatus("error");
        }
      });
  }, [user, token, status, router]);

  if (!token) {
    return (
      <div className="text-center">
        <p className="text-red-500 text-sm">無効な招待リンクです。</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center gap-2">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
        <p className="text-gray-400 text-sm text-center">読み込み中...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="text-center">
        <p className="text-sm text-gray-600 mb-4">
          ファミリーへの招待があります。Google アカウントでサインインして参加してください。
        </p>
        <button
          onClick={() => signIn()}
          className="bg-blue-500 text-white px-6 py-2 rounded-xl text-sm font-medium hover:bg-blue-600"
        >
          Google でサインイン
        </button>
      </div>
    );
  }

  if (status === "joining") {
    return <p className="text-gray-400 text-sm text-center">参加処理中...</p>;
  }

  if (status === "success") {
    return (
      <div className="text-center">
        <p className="text-green-600 text-sm font-medium">
          「{familyName}」に参加しました！
        </p>
        <p className="text-gray-400 text-xs mt-1">ダッシュボードに移動します...</p>
      </div>
    );
  }

  if (status === "invalid_token") {
    return <p className="text-red-500 text-sm text-center">この招待リンクは無効です。</p>;
  }

  if (status === "expired") {
    return (
      <p className="text-red-500 text-sm text-center">
        この招待は使用済みまたは期限切れです。
      </p>
    );
  }

  if (status === "email_mismatch") {
    return (
      <p className="text-red-500 text-sm text-center">
        招待先のメールアドレスとログイン中のアカウントが一致しません。
      </p>
    );
  }

  return (
    <p className="text-red-500 text-sm text-center">
      エラーが発生しました。もう一度お試しください。
    </p>
  );
}

export default function InvitePage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-sm p-8 max-w-sm w-full mx-4">
        <h1 className="text-lg font-semibold text-gray-700 mb-6 text-center">
          ファミリーに参加
        </h1>
        <Suspense
          fallback={
            <div className="flex flex-col items-center gap-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
              <p className="text-gray-400 text-sm text-center">読み込み中...</p>
            </div>
          }
        >
          <InviteContent />
        </Suspense>
      </div>
    </div>
  );
}
