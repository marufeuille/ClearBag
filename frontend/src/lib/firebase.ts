/**
 * Firebase 初期化
 *
 * 環境変数（NEXT_PUBLIC_FIREBASE_*）から設定を読み込む。
 * Firebase Auth の Google サインインと ID トークン取得を提供する。
 */

import { getApp, getApps, initializeApp } from "firebase/app";
import {
  GoogleAuthProvider,
  getAuth,
  getRedirectResult,
  signInWithPopup,
  signInWithRedirect,
  signOut as fbSignOut,
} from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY!,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN!,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID!,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET!,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID!,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID!,
};

// SSR/HMR で二重初期化を防ぐ
const app = getApps().length === 0 ? initializeApp(firebaseConfig) : getApp();
export const auth = getAuth(app);

/**
 * iOS Safari かどうかを判定。
 * iOS Safari はユーザー操作起点でもポップアップをブロックするため、
 * リダイレクト方式が必要な唯一のケース。
 * Android Chrome はユーザー操作起点のポップアップを許可する。
 */
function isIOSSafari(): boolean {
  return /iPhone|iPad|iPod/i.test(navigator.userAgent);
}

/**
 * Google サインイン
 * - PC / Android Chrome: ポップアップ方式
 * - iOS Safari: リダイレクト方式（ポップアップがブロックされるため）
 */
export async function signInWithGoogle() {
  const provider = new GoogleAuthProvider();
  if (isIOSSafari()) {
    return signInWithRedirect(auth, provider);
  }
  return signInWithPopup(auth, provider);
}

/**
 * リダイレクト認証後の結果を取得する。
 * モバイルでのリダイレクト方式では、ページ再読み込み後にこれを呼ぶ必要がある。
 */
export async function getGoogleRedirectResult() {
  return getRedirectResult(auth);
}

/** サインアウト */
export async function signOut() {
  return fbSignOut(auth);
}

/**
 * 現在のユーザーの Firebase ID トークンを取得。
 * API リクエストの Authorization ヘッダーに使う。
 */
export async function getIdToken(): Promise<string> {
  const user = auth.currentUser;
  if (!user) throw new Error("Not authenticated");
  return user.getIdToken();
}
