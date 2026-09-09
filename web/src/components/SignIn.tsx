"use client";

import { useAuth } from "@/lib/auth";

/**
 * Sign-in, presented as an offer rather than a demand.
 *
 * Signed out is a first-class state here: the label says what signing in
 * gets you ("keep your reports"), not that you must. Nothing behind it is
 * inaccessible - only ownership is.
 */
export function SignIn() {
  const { user, loading, configured, signIn, signOut } = useAuth();

  if (!configured) return null;

  if (loading) {
    return (
      <span className="font-mono text-[11px] text-ink-faint">checking…</span>
    );
  }

  if (user) {
    return (
      <div className="flex items-center gap-2.5">
        {user.photoURL ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={user.photoURL}
            alt=""
            width={26}
            height={26}
            className="rounded-full border border-border"
          />
        ) : null}
        <div className="leading-tight">
          <div className="text-[12.5px] font-semibold text-ink">{user.name}</div>
          <button
            type="button"
            onClick={() => signOut()}
            className="text-[11px] text-ink-faint hover:text-ink"
          >
            Sign out
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2.5">
      <span className="hidden text-[11px] leading-snug text-ink-faint sm:block">
        Sign in to keep
        <br />
        your reports
      </span>
      <button
        type="button"
        onClick={() => signIn()}
        className="flex items-center gap-2 rounded-lg border border-border-strong bg-surface px-3 py-2 text-[12.5px] font-semibold text-ink transition-colors hover:border-accent hover:text-accent-strong"
      >
        <GoogleMark />
        Sign in with Google
      </button>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg width="15" height="15" viewBox="0 0 18 18" aria-hidden="true">
      <path
        fill="#4285F4"
        d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92a8.78 8.78 0 0 0 2.68-6.62z"
      />
      <path
        fill="#34A853"
        d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.34A8.99 8.99 0 0 0 9 18z"
      />
      <path
        fill="#FBBC05"
        d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.94H.96a9 9 0 0 0 0 8.12l3.01-2.34z"
      />
      <path
        fill="#EA4335"
        d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.59C13.46.89 11.43 0 9 0A8.99 8.99 0 0 0 .96 4.94l3.01 2.34C4.68 5.16 6.66 3.58 9 3.58z"
      />
    </svg>
  );
}
