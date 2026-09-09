"""
Mechnari.ai - who is asking
============================
Verifies Google sign-in tokens, and is deliberately relaxed about their
absence.

Sign-in is optional by design. Every read view - the drafted DFMEA, the
review queue, the program rollup, the copilot - works signed out, because
the people who most need the rollup (leadership, an auditor, someone
evaluating the tool) are the least likely to have an account provisioned.
A login wall in front of an unfamiliar tool loses the reader before the
tool gets a chance to be judged.

What signing in buys is ownership: a report gains an author, and "my
reports" starts meaning something across machines instead of being
whatever happens to be in this browser.

So `current_user` returns None rather than raising when there is no
token, and routes decide for themselves whether they need one.
`require_user` exists for the ones that do.

Verification is real: the ID token is checked against Google's signing
keys by firebase_admin, so a caller cannot simply claim to be somebody.
An unverifiable token is treated as no token at all rather than as an
error - a stale token in an open tab should degrade to signed-out, not
break the page.
"""

import os
from typing import Any, Dict, Optional

from fastapi import Header, HTTPException

_initialised = False
_init_failed = False


def _ensure_app() -> bool:
    """Initialise firebase_admin once. False means token verification is
    unavailable, which is a valid state - the app runs signed-out."""
    global _initialised, _init_failed
    if _init_failed:
        return False
    if _initialised:
        return True
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        _init_failed = True
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials  # noqa: F401

        if not firebase_admin._apps:
            # Application Default Credentials: ADC locally, the service
            # account on Cloud Run. Same path Vertex and Firestore use, so
            # there is no extra secret to manage or leak.
            firebase_admin.initialize_app(options={"projectId": project})
        _initialised = True
        return True
    except Exception:  # noqa: BLE001 - degrade to signed-out
        _init_failed = True
        return False


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """The token's claims, or None if it cannot be trusted."""
    if not token or not _ensure_app():
        return None
    try:
        from firebase_admin import auth as fb_auth

        claims = fb_auth.verify_id_token(token)
    except Exception:  # noqa: BLE001 - an unverifiable token is no token
        return None

    uid = claims.get("uid") or claims.get("sub")
    if not uid:
        return None
    return {
        "uid": uid,
        "email": claims.get("email") or "",
        "name": claims.get("name") or claims.get("email") or "Signed-in user",
        "picture": claims.get("picture") or "",
    }


def current_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[Dict[str, Any]]:
    """FastAPI dependency. None when signed out, which is allowed."""
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return verify_token(parts[1])


def require_user(
    authorization: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """For routes that genuinely cannot work anonymously - writing to
    somebody's own report, for instance."""
    user = current_user(authorization)
    if user is None:
        raise HTTPException(401, "Sign in to do that.")
    return user


def auth_available() -> bool:
    """Whether sign-in can work at all here, so the UI can hide the button
    rather than offer one that fails."""
    return _ensure_app()
