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

export function useAuth(): AuthState & {
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
} {
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
  });

  useEffect(() => {
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
