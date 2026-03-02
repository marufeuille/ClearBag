/**
 * Web Share Target フック
 *
 * Service Worker が Cache API に保存した共有ファイルを検知し、
 * uploadDocument() で自動アップロードする。
 *
 * フロー:
 *   1. URL に ?shared=true がある → キャッシュからファイルを取得
 *   2. タイムスタンプを確認（5分以内のみ有効）
 *   3. uploadDocument() で既存のアップロード API に投げる
 *   4. 成功 / 失敗を呼び出し元に返す
 *   5. router.replace() で URL パラメータを削除（リロード時の再実行防止）
 *
 * エラーパス:
 *   - ?share_error=no_file  : SW がファイルを受け取れなかった
 *   - ?share_error=failed   : SW 内で例外が発生した
 *   - キャッシュ期限切れ     : ファイルは破棄、エラーメッセージを返す
 */

"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { uploadDocument } from "@/lib/api";
import {
  SHARE_TARGET_CACHE_NAME,
  SHARE_TARGET_CACHE_KEY,
  SHARE_TARGET_TTL_MS,
} from "@/lib/share-target";

interface ShareTargetState {
  processing: boolean;
  documentId: string | null;
  error: string | null;
}

export function useShareTarget(): ShareTargetState {
  const router = useRouter();
  const searchParams = useSearchParams();
  const processedRef = useRef(false);

  const [state, setState] = useState<ShareTargetState>({
    processing: false,
    documentId: null,
    error: null,
  });

  useEffect(() => {
    const shared = searchParams.get("shared");
    const shareError = searchParams.get("share_error");

    // SW 側でエラーが発生した場合
    if (shareError) {
      const message =
        shareError === "no_file"
          ? "共有されたファイルを受け取れませんでした。"
          : "ファイルの共有処理中にエラーが発生しました。";
      setState({ processing: false, documentId: null, error: message });
      router.replace("/dashboard/");
      return;
    }

    if (shared !== "true") return;
    // React Strict Mode の二重実行防止
    if (processedRef.current) return;
    processedRef.current = true;

    // URL パラメータを即座にクリーンアップ（リロード時の再実行防止）
    router.replace("/dashboard/");

    setState({ processing: true, documentId: null, error: null });

    (async () => {
      try {
        const cache = await caches.open(SHARE_TARGET_CACHE_NAME);
        const cached = await cache.match(SHARE_TARGET_CACHE_KEY);

        if (!cached) {
          setState({
            processing: false,
            documentId: null,
            error: "共有ファイルが見つかりませんでした。もう一度お試しください。",
          });
          return;
        }

        // タイムスタンプで有効期限チェック
        const timestamp = cached.headers.get("X-Share-Target-Timestamp");
        if (timestamp) {
          const age = Date.now() - parseInt(timestamp, 10);
          if (age > SHARE_TARGET_TTL_MS) {
            await cache.delete(SHARE_TARGET_CACHE_KEY);
            setState({
              processing: false,
              documentId: null,
              error: "共有ファイルの有効期限が切れました。再度共有してください。",
            });
            return;
          }
        }

        const blob = await cached.blob();
        const filename = cached.headers.get("X-Share-Target-Filename");
        const decodedFilename = filename
          ? decodeURIComponent(filename)
          : "shared-file";
        const file = new File([blob], decodedFilename, {
          type: blob.type || "application/octet-stream",
        });

        // キャッシュを使い捨て（再実行防止）
        await cache.delete(SHARE_TARGET_CACHE_KEY);

        const result = await uploadDocument(file);
        setState({ processing: false, documentId: result.id, error: null });
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "アップロードに失敗しました。";
        setState({ processing: false, documentId: null, error: message });
      }
    })();
  }, [searchParams, router]);

  return state;
}
