/**
 * ClearBag カスタム Service Worker
 *
 * next-pwa の customWorkerDir: "worker" 設定により、
 * このファイルが Workbox SW に結合される。
 *
 * 担当する機能:
 *   - push イベント: バックエンドから受け取った通知を showNotification() で表示
 *   - notificationclick イベント: タップ時にアプリを開く
 */

// export {} でモジュールスコープにして lib.dom.d.ts の self 宣言と競合を回避する
export {};

import { registerRoute } from "workbox-routing";
import { NetworkOnly } from "workbox-strategies";

const sw = self as unknown as ServiceWorkerGlobalScope;

interface PushPayload {
  title: string;
  body: string;
  url?: string;
  tag?: string;
}

// Firebase Auth / Google Sign-In が利用する外部エンドポイントは
// SW の runtime cache を通さず常にネットワークへ流す。
registerRoute(
  ({ url }) =>
    /^https:\/\/apis\.google\.com\/js\/api\.js/i.test(url.href) ||
    /^https:\/\/accounts\.google\.com\//i.test(url.href),
  new NetworkOnly(),
  "GET"
);

sw.addEventListener("push", (event: PushEvent) => {
  if (!event.data) return;

  let payload: PushPayload;
  try {
    payload = event.data.json() as PushPayload;
  } catch {
    payload = { title: "ClearBag", body: event.data.text() };
  }

  const { title, body, url = "/" } = payload;

  event.waitUntil(
    sw.registration.showNotification(title, {
      body,
      icon: "/icon-192.png",
      badge: "/icon-badge-72.png",
      tag: payload.tag ?? "clearbag-default",
      data: { url },
    })
  );
});

sw.addEventListener("notificationclick", (event: NotificationEvent) => {
  event.notification.close();

  const url: string = (event.notification.data as { url?: string })?.url ?? "/";

  event.waitUntil(
    sw.clients
      .matchAll({ type: "window", includeUncontrolled: true })
      .then((clientList) => {
        // 既にアプリウィンドウが開いていればフォーカス
        for (const client of clientList) {
          if ("focus" in client) {
            (client as WindowClient).navigate(url);
            return (client as WindowClient).focus();
          }
        }
        // 開いていなければ新規オープン
        return sw.clients.openWindow(url);
      })
  );
});
