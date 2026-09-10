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

import contextvars
import json
import logging
import os
import time
from typing import Any, Dict, Optional, Set

from ag_ui_adk import (
    ADKAgent,
    AGUIToolset,
    CONTEXT_STATE_KEY,
    add_adk_fastapi_endpoint,
)
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from mechnari_agent import agent as mechnari_agent

logger = logging.getLogger(__name__)

# Frontend tools do not arrive on their own. ag-ui-adk walks the agent tree
# looking for an AGUIToolset placeholder and swaps in a per-run
# ClientProxyToolset built from the tools the browser declared; an agent
# with no placeholder simply never sees them. Without this line the model
# was told nothing about goToView or fillPartIntake, so every "switch to
# the company view" turned into an apology or into whatever backend tool
# read closest - which looked like the model preferring its own tools and
# was really the model not having the choice.
#
# Root only, deliberately. The sub-agents answer questions about scores and
# gaps; none of them should be driving the interface, and keeping the
# placeholder off them is what makes the instruction "do not transfer for a
# UI request" true rather than merely asked for.
#
# New list rather than .append(): KNOWLEDGE_BASE_TOOLS is a shared module
# constant, and `adk run` should not inherit a web-only placeholder.
mechnari_agent.root_agent.tools = [
    *mechnari_agent.root_agent.tools,
    AGUIToolset(),
]

# Screen context does not reach the model on its own either.
#
# The browser sends it - `useAgentContext` puts it on RunAgentInput.context,
# and it is on the wire, verified by reading the outgoing request body. What
# ag-ui-adk does with it is store it in session state under
# `_ag_ui_context`, where it is "accessible to instruction providers". That
# is the whole of the integration: nothing puts it in front of the model.
# So the agent, holding a full description of the screen in its own session
# state, answered "I cannot see which screen you are currently on" - which
# is the most confusing possible failure, because the frontend is provably
# correct and the wiring looks complete from both ends.
#
# Wrapping the instruction here rather than in mechnari_agent/agent.py keeps
# ag_ui_adk out of the CLI agent: `adk run` and /api/copilot/ask have no
# screen and want the plain string. Same reasoning as the toolset above -
# this module adds the web-only half.

_BASE_INSTRUCTION = mechnari_agent.root_agent.instruction

# Enough for the screen state the views actually register; a runaway page
# should lose its tail rather than crowd out the engineer's question.
_MAX_CONTEXT_CHARS = 4000


def _screen_context_block(state: Any) -> str:
    """Render whatever the browser sent this turn, or "" if it sent nothing."""
    try:
        entries = state.get(CONTEXT_STATE_KEY) or []
    except Exception:  # noqa: BLE001 - a missing state is simply no context
        return ""
    if not entries:
        return ""

    lines = []
    for entry in entries:
        description = str(entry.get("description", "")).strip()
        value = entry.get("value")
        if not isinstance(value, str):
            # CopilotKit stringifies before sending; a dict here means some
            # other client, and json is still the readable form.
            value = json.dumps(value, ensure_ascii=False)
        lines.append("%s\n%s" % (description, value[:_MAX_CONTEXT_CHARS]))

    return (
        "\n\n--- What the engineer has on screen right now ---\n"
        "Sent by the browser with this message, so it is current. Use it to "
        "resolve 'this', 'here' and 'the one I have open', and answer from it "
        "directly rather than saying you cannot see the screen. It describes "
        "the view, not the engineering record: any number you quote still "
        "comes from a tool.\n\n"
        + "\n\n".join(lines)
    )


def _instruction_with_screen_context(ctx: ReadonlyContext) -> str:
    return _BASE_INSTRUCTION + _screen_context_block(ctx.state)


mechnari_agent.root_agent.instruction = _instruction_with_screen_context


# --- One client-side tool call per turn ----------------------------------
#
# Asked "let's draft a DFMEA for a bracket, steel, supports lines", the model
# does the sensible thing and emits BOTH calls at once: fillPartIntake and
# buildDfmea, in a single turn. Gemini is entitled to; parallel function
# calling is a documented feature.
#
# ag-ui-adk surfaces only the first one. The browser therefore returns one
# result, the session records one function_response against a turn holding
# two function_calls, and the next request dies at Vertex with:
#
#   "Please ensure that the number of function response parts is equal to
#    the number of function call parts of the function call turn."
#
# To the engineer that is a chat that answers once and then never speaks
# again - which is exactly how it was reported. Nothing in the UI says a
# request failed, because the failure is in the *following* run.
#
# Measured rather than guessed: with fillPartIntake alone the follow-up
# succeeds; adding goToView, reanalyseAsPartType or openExistingPartDfmea
# keeps succeeding; adding buildDfmea fails every time, because buildDfmea
# is the one the model wants to chain onto the fill. Dumping the ADK session
# showed the turn holding CALL:fillPartIntake and CALL:buildDfmea with a
# single response against it.
#
# So keep one, drop the rest. The dropped call is not lost work: followUp is
# true on every frontend tool, so the model gets another turn the moment the
# result lands and can call buildDfmea then - which is also the order the
# engineer wants, since the form should be right before the analysis runs.
#
# Enforced here rather than only asked for in the instruction. A prompt that
# says "one at a time" is a preference the model may decline; this is the
# invariant the protocol actually requires.

_CLIENT_TOOL_NAMES: contextvars.ContextVar[Set[str]] = contextvars.ContextVar(
    "mechnari_client_tool_names", default=frozenset()
)


def _note_client_tools(callback_context, llm_request) -> None:
    """Record which of this run's tools live in the browser.

    Read off the request rather than hardcoded, because the frontend owns
    that list: a tool added in CopilotActions.tsx and not here would
    otherwise be exactly the one that slips through.
    """
    tools = getattr(llm_request, "tools_dict", None) or {}
    _CLIENT_TOOL_NAMES.set(
        frozenset(
            name for name, tool in tools.items()
            if getattr(tool, "is_long_running", False)
        )
    )
    return None


def _one_client_tool_per_turn(callback_context, llm_response) -> Optional[LlmResponse]:
    """Drop every client-side call after the first in the same turn."""
    content = getattr(llm_response, "content", None)
    parts = list(content.parts) if content and content.parts else []
    calls = [p for p in parts if getattr(p, "function_call", None)]
    if len(calls) < 2:
        return None

    client_names = _CLIENT_TOOL_NAMES.get()
    first_client = next(
        (p for p in calls if p.function_call.name in client_names), None
    )
    if first_client is None:
        # All server-side: they resolve inside this turn, so the counts
        # match and there is nothing to fix.
        return None

    kept = [p for p in parts
            if not getattr(p, "function_call", None) or p is first_client]
    dropped = [p.function_call.name for p in calls if p is not first_client]
    logger.info(
        "Deferred %s to a later turn; %s is client-side and only one such "
        "call can be answered per turn.",
        ", ".join(dropped), first_client.function_call.name,
    )
    return llm_response.model_copy(
        update={"content": types.Content(role=content.role, parts=kept)}
    )


mechnari_agent.root_agent.before_model_callback = _note_client_tools
mechnari_agent.root_agent.after_model_callback = _one_client_tool_per_turn


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
    """Whether a credential path is configured at all - an API key, or the
    ambient Google Cloud identity when running against Vertex."""
    return mechnari_agent._api_key_present()


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
        return {"ok": False,
                "reason": "No credential configured: set GOOGLE_API_KEY, or "
                          "GOOGLE_GENAI_USE_VERTEXAI=true with Google Cloud "
                          "credentials available."}

    now = time.time()
    cached = _key_check_cache["result"]
    if cached is not None and now - _key_check_cache["checked_at"] < _KEY_CHECK_TTL_SECONDS:
        return cached

    try:
        from google import genai

        if mechnari_agent.USE_VERTEX:
            # Vertex reads project/location and ADC from the environment.
            # A generate call is the honest check here: models.list does not
            # exercise the same publisher-model path, and a wrong model name
            # 404s on Vertex while looking fine on AI Studio.
            client = genai.Client()
            client.models.generate_content(
                model=mechnari_agent.MODEL, contents="ping"
            )
        else:
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
