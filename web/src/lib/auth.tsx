"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

/**
 * Google sign-in, deliberately optional.
 *
 * Every view works signed out. What signing in buys is ownership: reports
 * gain an author and follow you between machines instead of living in one
 * browser. The people most likely to open the program rollup - leadership,
 * an auditor, someone evaluating the tool - are the least likely to have
 * an account, and a login wall would lose them before the tool got a
 * chance to be read.
 *
 * The Firebase SDK is imported lazily so that a build without config, or a
 * browser where it fails to load, degrades to signed-out rather than
 * breaking the page. `configured` says which of the two it is, so the UI
 * can hide the button instead of offering one that cannot work.
 *
 * The ID token is fetched per request rather than cached: the SDK handles
 * refresh, and holding a stale one is how "signed in but 401" happens.
 */

export type AuthUser = {
  uid: string;
  name: string;
  email: string;
  photoURL: string;
};

type AuthState = {
  user: AuthUser | null;
  loading: boolean;
  configured: boolean;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  getToken: () => Promise<string | null>;
};

const FIREBASE_CONFIG = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
};

const CONFIGURED = Boolean(FIREBASE_CONFIG.apiKey && FIREBASE_CONFIG.projectId);

const AuthContext = createContext<AuthState>({
  user: null,
  loading: false,
  configured: false,
  signIn: async () => {},
  signOut: async () => {},
  getToken: async () => null,
});

// Held at module scope so the SDK is initialised once per tab, not per
// component mount.
let authPromise: Promise<unknown> | null = null;

async function getAuth() {
  if (!CONFIGURED) return null;
  if (!authPromise) {
    authPromise = (async () => {
      const { initializeApp, getApps } = await import("firebase/app");
      const { getAuth: fbGetAuth } = await import("firebase/auth");
      const app = getApps().length
        ? getApps()[0]
        : initializeApp(FIREBASE_CONFIG as Record<string, string>);
      return fbGetAuth(app);
    })();
  }
  try {
    return await authPromise;
  } catch {
    return null;
  }
}

/** So non-React callers (the API client) can attach a token. */
export async function currentIdToken(): Promise<string | null> {
  const auth = (await getAuth()) as {
    currentUser?: { getIdToken: () => Promise<string> } | null;
  } | null;
  if (!auth?.currentUser) return null;
  try {
    return await auth.currentUser.getIdToken();
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(CONFIGURED);

  useEffect(() => {
    if (!CONFIGURED) return;
    let cancelled = false;
    let unsubscribe: (() => void) | undefined;

    (async () => {
      const auth = await getAuth();
      if (!auth || cancelled) {
        if (!cancelled) setLoading(false);
        return;
      }
      const { onAuthStateChanged } = await import("firebase/auth");
      unsubscribe = onAuthStateChanged(
        auth as Parameters<typeof onAuthStateChanged>[0],
        (fbUser) => {
          if (cancelled) return;
          setUser(
            fbUser
              ? {
                  uid: fbUser.uid,
                  name: fbUser.displayName || fbUser.email || "Signed in",
                  email: fbUser.email || "",
                  photoURL: fbUser.photoURL || "",
                }
              : null,
          );
          setLoading(false);
        },
      );
    })();

    return () => {
      cancelled = true;
      unsubscribe?.();
    };
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      configured: CONFIGURED,
      signIn: async () => {
        const auth = await getAuth();
        if (!auth) return;
        const { GoogleAuthProvider, signInWithPopup } = await import(
          "firebase/auth"
        );
        try {
          await signInWithPopup(
            auth as Parameters<typeof signInWithPopup>[0],
            new GoogleAuthProvider(),
          );
        } catch {
          // A closed popup is the usual case and is not an error worth
          // shouting about - the user simply chose not to sign in.
        }
      },
      signOut: async () => {
        const auth = await getAuth();
        if (!auth) return;
        const { signOut: fbSignOut } = await import("firebase/auth");
        await fbSignOut(auth as Parameters<typeof fbSignOut>[0]);
      },
      getToken: currentIdToken,
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  return useContext(AuthContext);
}
