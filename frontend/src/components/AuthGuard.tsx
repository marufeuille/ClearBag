"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { getFamily, ApiError } from "@/lib/api";
import { AppSkeleton } from "@/components/AppSkeleton";
import {
  loadActivationCache,
  saveActivationCache,
  clearActivationCache,
} from "@/lib/activationCache";

type ActivationStatus = "checking" | "activated" | "not_activated";

interface AuthGuardProps {
  children: React.ReactNode;
}

/**
 * 認証済みかつアクティベート済みユーザーのみコンテンツを表示するガードコンポーネント。
 * 未認証の場合はトップページへリダイレクトする。
 * 未アクティベートの場合は「招待リンクが必要です」案内画面を表示する。
 *
 * アクティベーション確認の優先順位:
 *   ② localStorage キャッシュ（同期・即時）→ 2回目以降は Cold Start を完全回避
 *   ① JWT Custom Claims（非同期・API 呼び出し不要）→ キャッシュなし時の高速パス
 *   フォールバック: getFamily() API 呼び出し（初回のみ発生しうる）
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [activationStatus, setActivationStatus] = useState<ActivationStatus>("checking");

  useEffect(() => {
    if (!loading && !user) {
      router.push("/");
    }
  }, [user, loading, router]);

  useEffect(() => {
    if (!user) return;

    const uid = user.uid;

    // ② localStorage キャッシュを確認（同期・即時 → UI を即座に表示）
    if (loadActivationCache(uid)) {
      setActivationStatus("activated");
      // バックグラウンドで再検証（UI はブロックしない）
      getFamily()
        .then(() => saveActivationCache(uid))
        .catch((err) => {
          if (
            err instanceof ApiError &&
            err.status === 403 &&
            err.detail === "ACTIVATION_REQUIRED"
          ) {
            // アクティベーションが取り消された場合のみキャッシュを破棄して UI に反映
            clearActivationCache(uid);
            setActivationStatus("not_activated");
          }
        });
      return;
    }

    // ① JWT Custom Claims を確認（API 呼び出し不要）
    // ② のキャッシュがない初回 or TTL 切れ時のみ到達する
    (async () => {
      try {
        const tokenResult = await user.getIdTokenResult();
        if (tokenResult.claims["is_activated"] === true) {
          saveActivationCache(uid);
          setActivationStatus("activated");
          return;
        }
      } catch {
        // claims 取得失敗は無視してフォールバックへ
      }

      // フォールバック: API 呼び出し（初回のみ Cold Start が発生しうる）
      try {
        await getFamily();
        saveActivationCache(uid);
        setActivationStatus("activated");
      } catch (err) {
        if (
          err instanceof ApiError &&
          err.status === 403 &&
          err.detail === "ACTIVATION_REQUIRED"
        ) {
          setActivationStatus("not_activated");
        } else {
          setActivationStatus("activated"); // その他エラーは各ページでハンドリング
        }
      }
    })();
  }, [user]);

  // ③ FullScreenLoading → AppSkeleton（ページ構造が見えて待ち感が減る）
  if (loading) return <AppSkeleton />;

  if (!user) return null;

  if (activationStatus === "checking") return <AppSkeleton />;

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
