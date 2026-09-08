"""
Mechnari.ai - AG-UI endpoint for the ADK agent
===============================================
Exposes the same `root_agent` that mechnari_agent/agent.py already defines
over the AG-UI protocol (https://docs.ag-ui.com), so a CopilotKit frontend
can stream the agent's output token by token instead of waiting on one
blocking request.

This does not replace `/api/copilot/ask`. That route stays because it is
synchronous, dependency-light and already covered by tests - useful as a
fallback and for anything that just wants an answer without an SSE client.
This module adds a second way to reach the *same* agent, not a second agent.

The division of labour is unchanged and still enforced by
test_mechnari_tools.py: the agent narrates, the deterministic engines own
every number. AG-UI streams what the agent says; it does not give the agent
any tool it did not already have.
"""

import os
import time
from typing import Any, Dict

from ag_ui_adk import ADKAgent, add_adk_fastapi_endpoint

from mechnari_agent import agent as mechnari_agent

# There is no per-user auth in this build - the three role views are tabs,
# not accounts - so every AG-UI conversation runs as one service user, the
# same way ask_copilot() uses a fixed "dashboard_user".
AGUI_USER_ID = "web_user"

# AG-UI sends a threadId per conversation. Mapping it onto the ADK session
# id is what makes a follow-up question ("and why is that severity 9?")
# land in the same session as the question before it.
adk_agent = ADKAgent(
    adk_agent=mechnari_agent.root_agent,
    app_name=mechnari_agent.APP_NAME,
    user_id=AGUI_USER_ID,
    use_in_memory_services=True,
    use_thread_id_as_session_id=True,
    session_timeout_seconds=3600,
)

AGUI_PATH = "/api/ag-ui"


def mount(app) -> None:
    """Attach the AG-UI streaming endpoint to an existing FastAPI app."""
    add_adk_fastapi_endpoint(app, adk_agent, path=AGUI_PATH)


def api_key_present() -> bool:
    """Whether a Gemini key is configured at all."""
    return bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))


_key_check_cache: Dict[str, Any] = {"checked_at": 0.0, "result": None}
_KEY_CHECK_TTL_SECONDS = 120


def api_key_works() -> Dict[str, Any]:
    """
    Whether the configured Gemini key actually authenticates.

    Presence is not the useful question - a key that is set but rejected
    looks identical to a working one from the frontend's side, and the
    failure only shows up as an AG-UI RUN_ERROR that CopilotKit's popup
    renders silently. Asking the API directly is the only honest answer.

    Uses models.list rather than a generation call: it is the cheapest
    request that still exercises authentication, and it costs no tokens.
    Cached, because this is called on page load.
    """
    if not api_key_present():
        return {"ok": False, "reason": "No GOOGLE_API_KEY or GEMINI_API_KEY is set."}

    now = time.time()
    cached = _key_check_cache["result"]
    if cached is not None and now - _key_check_cache["checked_at"] < _KEY_CHECK_TTL_SECONDS:
        return cached

    try:
        from google import genai

        client = genai.Client(
            api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        )
        next(iter(client.models.list()), None)
        result = {"ok": True, "reason": ""}
    except Exception as exc:  # noqa: BLE001 - reported, not masked
        message = str(exc)
        if "401" in message or "UNAUTHENTICATED" in message:
            reason = "The Gemini API key is set but not authenticating (401)."
        else:
            reason = "%s: %s" % (type(exc).__name__, message[:200])
        result = {"ok": False, "reason": reason}

    _key_check_cache["result"] = result
    _key_check_cache["checked_at"] = now
    return result
