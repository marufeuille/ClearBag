"use client";

import { useEffect } from "react";

/**
 * Service Worker を手動登録するクライアントコンポーネント。
 *
 * next-pwa v5.6.0 は Next.js 15 App Router + output:"export" 環境で
 * SW 登録スクリプトの HTML 注入に失敗するため、このコンポーネントで代替する。
 * development 環境では sw.js が生成されないため何もしない。
 */
export default function ServiceWorkerRegistrar() {
  useEffect(() => {
    if (
      process.env.NODE_ENV === "development" ||
      !("serviceWorker" in navigator)
    ) {
      return;
    }

    navigator.serviceWorker.register("/sw.js").catch((err) => {
      console.error("[SW] 登録に失敗しました:", err);
    });
  }, []);

  return null;
}
