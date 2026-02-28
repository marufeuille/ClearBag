/**
 * Web Push サブスクリプション管理ユーティリティ
 *
 * ブラウザの Push API を操作し、バックエンドに
 * サブスクリプション情報を登録・削除する。
 */

import { deletePushSubscription, registerPushSubscription } from "./api";

/**
 * SW が登録済みであればその Registration を返す。
 * 未登録の場合は /sw.js を登録してから返す。
 * navigator.serviceWorker.ready は SW が未登録だと永遠に resolve しないため、
 * このヘルパーでフォールバック登録を行う。
 */
async function ensureServiceWorker(): Promise<ServiceWorkerRegistration> {
  const registrations = await navigator.serviceWorker.getRegistrations();
  if (registrations.length > 0) {
    return registrations[0];
  }
  return navigator.serviceWorker.register("/sw.js");
}

/** VAPID 公開鍵（Base64url → Uint8Array<ArrayBuffer> 変換） */
function urlBase64ToUint8Array(base64String: string): Uint8Array<ArrayBuffer> {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  const buffer = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; i++) {
    buffer[i] = rawData.charCodeAt(i);
  }
  return buffer;
}

/** ブラウザが Web Push をサポートしているか */
export function isPushSupported(): boolean {
  return (
    typeof window !== "undefined" &&
    "serviceWorker" in navigator &&
    "PushManager" in window &&
    "Notification" in window
  );
}

/** 現在の通知許可状態を返す */
export function getPermissionState(): NotificationPermission {
  if (typeof window === "undefined" || !("Notification" in window)) {
    return "default";
  }
  return Notification.permission;
}

/**
 * ブラウザに通知許可を要求し、Push サブスクリプションを作成してバックエンドに登録する。
 *
 * @returns 登録成功した場合 true、ユーザーが拒否した場合 false
 * @throws ブラウザ非対応・VAPID鍵未設定・バックエンドエラーの場合
 */
export async function subscribePush(): Promise<boolean> {
  if (!isPushSupported()) {
    throw new Error("Web Push はこのブラウザでサポートされていません");
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return false;
  }

  const vapidPublicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
  if (!vapidPublicKey) {
    throw new Error("VAPID 公開鍵が設定されていません");
  }

  // ensureServiceWorker で未登録の場合も /sw.js を登録してから取得する
  // タイムアウトは SW の activate 待ちなど想定外の遅延への安全弁として維持する
  const registration = await Promise.race<ServiceWorkerRegistration>([
    ensureServiceWorker(),
    new Promise<never>((_, reject) =>
      setTimeout(
        () => reject(new Error("Service Worker の準備がタイムアウトしました。ページを再読み込みしてお試しください")),
        10000
      )
    ),
  ]);
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  });

  const json = subscription.toJSON();
  const keys = json.keys as { auth: string; p256dh: string };

  await registerPushSubscription(subscription.endpoint, {
    auth: keys.auth,
    p256dh: keys.p256dh,
  });

  return true;
}

/**
 * Push サブスクリプションを解除してバックエンドからも削除する。
 */
export async function unsubscribePush(): Promise<void> {
  if (!isPushSupported()) return;

  const registration = await Promise.race<ServiceWorkerRegistration>([
    ensureServiceWorker(),
    new Promise<never>((_, reject) =>
      setTimeout(
        () => reject(new Error("Service Worker の準備がタイムアウトしました。ページを再読み込みしてお試しください")),
        10000
      )
    ),
  ]);
  const subscription = await registration.pushManager.getSubscription();
  if (subscription) {
    await subscription.unsubscribe();
  }

  await deletePushSubscription();
}
