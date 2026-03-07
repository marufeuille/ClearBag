/**
 * 認証状態フック
 *
 * Firebase Auth の認証状態をリアクティブに監視し、
 * コンポーネントから uid や user オブジェクトにアクセスできるようにする。
 */

"use client";

import { User, onAuthStateChanged } from "firebase/auth";
import { useEffect, useState } from "react";

import { auth, getGoogleRedirectResult, signInWithGoogle, signOut } from "@/lib/firebase";
import { sendEvent } from "@/lib/analytics";

interface AuthState {
  user: User | null;
  loading: boolean;
}

// E2E テスト時は Firebase Auth をバイパスしてモックユーザーを使用
const IS_E2E = process.env.NEXT_PUBLIC_E2E === "true";
const E2E_USER = IS_E2E
  ? ({ uid: "e2e-test-user" } as unknown as User)
  : null;

export function useAuth(): AuthState & {
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
} {
  const [state, setState] = useState<AuthState>({
    user: E2E_USER,
    loading: !IS_E2E,
  });

  useEffect(() => {
    if (IS_E2E) return;
    // モバイルリダイレクト認証後の結果を処理する
    getGoogleRedirectResult()
      .then((result) => {
        if (result?.user) {
          sendEvent({ action: "sign_in", category: "auth", label: "redirect" });
        }
      })
      .catch((error) => {
        console.error("[Auth] getRedirectResult failed:", error?.code, error?.message);
      });
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setState({ user, loading: false });
    });
    return unsubscribe;
  }, []);

  const handleSignIn = async () => {
    const result = await signInWithGoogle();
    // signInWithPopup は UserCredential を返す（redirect は null）
    if (result?.user) {
      sendEvent({ action: "sign_in", category: "auth", label: "popup" });
    }
  };

  const handleSignOut = async () => {
    await signOut();
  };

  return {
    ...state,
    signIn: handleSignIn,
    signOut: handleSignOut,
  };
}
