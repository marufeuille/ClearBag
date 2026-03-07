"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { registerWithCode, ApiError } from "@/lib/api";

type RegisterStatus =
  | "idle"
  | "registering"
  | "success"
  | "already_activated"
  | "invalid_code"
  | "expired"
  | "exhausted"
  | "error";

function RegisterContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const code = searchParams.get("code");
  const { user, loading, signIn } = useAuth();
  const [regStatus, setRegStatus] = useState<RegisterStatus>("idle");

  useEffect(() => {
    if (!code || !user || regStatus !== "idle") return;
    setRegStatus("registering");
    registerWithCode(code)
      .then((result) => {
        if (result.already_activated) {
          setRegStatus("already_activated");
        } else {
          setRegStatus("success");
        }
        setTimeout(() => router.push("/dashboard"), 2000);
      })
      .catch((err: unknown) => {
        if (err instanceof ApiError) {
          if (err.status === 404) setRegStatus("invalid_code");
          else if (err.detail === "CODE_EXPIRED") setRegStatus("expired");
          else if (err.detail === "CODE_EXHAUSTED") setRegStatus("exhausted");
          else setRegStatus("error");
        } else {
          setRegStatus("error");
        }
      });
  }, [user, code, regStatus, router]);

  if (!code) {
    return (
      <div className="text-center">
        <p className="text-red-500 text-sm">無効な招待コードです。正しいURLでアクセスしてください。</p>
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
          Google アカウントでサインインして ClearBag に登録してください。
        </p>
        <button
          onClick={() => signIn()}
          className="bg-blue-500 text-white px-6 py-2 rounded-xl text-sm font-medium hover:bg-blue-600"
        >
          Google でサインインして登録
        </button>
      </div>
    );
  }

  if (regStatus === "registering") {
    return <p className="text-gray-400 text-sm text-center">登録処理中...</p>;
  }

  if (regStatus === "already_activated") {
    return (
      <div className="text-center">
        <p className="text-blue-600 text-sm font-medium">すでに登録済みです</p>
        <p className="text-gray-400 text-xs mt-1">ダッシュボードに移動します...</p>
      </div>
    );
  }

  if (regStatus === "success") {
    return (
      <div className="text-center">
        <p className="text-green-600 text-sm font-medium">登録完了！</p>
        <p className="text-gray-400 text-xs mt-1">ダッシュボードに移動します...</p>
      </div>
    );
  }

  if (regStatus === "invalid_code") {
    return (
      <p className="text-red-500 text-sm text-center">
        この招待コードは無効です。正しいURLでアクセスしてください。
      </p>
    );
  }

  if (regStatus === "expired") {
    return (
      <p className="text-red-500 text-sm text-center">
        この招待コードの有効期限が切れています。
      </p>
    );
  }

  if (regStatus === "exhausted") {
    return (
      <p className="text-red-500 text-sm text-center">
        この招待コードは上限に達しました。別のコードをお試しください。
      </p>
    );
  }

  return (
    <p className="text-red-500 text-sm text-center">
      エラーが発生しました。もう一度お試しください。
    </p>
  );
}

export default function RegisterPage() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-sm p-8 max-w-sm w-full mx-4">
        <h1 className="text-lg font-semibold text-gray-700 mb-6 text-center">
          ClearBag に登録
        </h1>
        <Suspense
          fallback={
            <div className="flex flex-col items-center gap-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
              <p className="text-gray-400 text-sm text-center">読み込み中...</p>
            </div>
          }
        >
          <RegisterContent />
        </Suspense>
      </div>
    </div>
  );
}
