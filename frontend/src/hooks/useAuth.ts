/**
 * 認証状態フック
 *
 * Firebase Auth の認証状態をリアクティブに監視し、
 * コンポーネントから uid や user オブジェクトにアクセスできるようにする。
 */

"use client";

import { User, onAuthStateChanged } from "firebase/auth";
import { useEffect, useState } from "react";

import { auth, signInWithGoogle, signOut } from "@/lib/firebase";

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
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      setState({ user, loading: false });
    });
    return unsubscribe;
  }, []);

  const handleSignIn = async () => {
    await signInWithGoogle();
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
