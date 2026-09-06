"""
Mechnari.ai - Google ADK Agent Definition
==========================================
Built to the ADK Python conventions documented at https://adk.dev:

- an agent package exposing a module-level `root_agent`, which is what
  `adk run mechnari_agent` and `adk web` look for
- plain typed Python functions as tools, which ADK inspects and wraps as
  FunctionTools automatically
- specialists composed under a coordinator via `sub_agents`, so ADK can
  delegate to them
- a graph `Workflow` for the fixed review pipeline, which is the ADK 2.x
  replacement for the older SequentialAgent template workflow

The division of labour is the point of the architecture. The agents read
findings and write English; the deterministic engines behind the tools own
every number. No agent is given a tool that would let it compute or revise
a severity, an occurrence, a detection score or an Action Priority, so an
LLM cannot move a score in a document an engineer signs.
"""

import asyncio
import os
import sys

# The deterministic engines live at the repository root; ADK loads this
# package by directory, so make sure the root is importable either way.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv  # noqa: E402
from google.adk import Agent, Runner, Workflow  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

import mechnari_tools  # noqa: E402

# ADK reads GOOGLE_API_KEY from the environment. It looks for a .env beside
# the agent package; this repository keeps one at the root, so load that too.
load_dotenv(os.path.join(_ROOT, ".env"))

APP_NAME = "mechnari_dfmea"

# A floating alias rather than a pinned snapshot: the previous build pinned a
# model that was later retired, which silently sent every call into the
# fallback path. Pin a dated model here only when a release needs to freeze.
MODEL = "gemini-flash-latest"

_NUMBERS_RULE = (
    "The tools are the only source of numbers. Never calculate, estimate, "
    "adjust or round a severity, occurrence, detection score, Action Priority "
    "or claim rate yourself, and never present a figure that did not come "
    "back from a tool call. If a tool returns status 'error', say what failed "
    "and stop rather than filling the gap with a plausible number. Always "
    "quote the 8D record identifiers a finding rests on."
)


def build_gap_analyst() -> Agent:
    return Agent(
        name="gap_analyst",
        model=MODEL,
        description=(
            "Finds failure modes proven on this kind of part that the DFMEA on "
            "file never analysed, and explains why each one applies."
        ),
        instruction=(
            "You are a reliability engineer reviewing a DFMEA for completeness on "
            "agricultural tractor programs.\n\n"
            "Call find_unanalysed_failure_modes for the part in question. For each "
            "finding, state the failure mode, the effect and its severity, which "
            "part or retired program the lesson was learned from, and the warranty "
            "evidence behind it. Lead with the safety and regulatory findings.\n\n"
            "A finding inherited at FAMILY level is a general lesson for that class "
            "of part; one inherited at TYPE level is specific to this kind of part. "
            "Say which, because it changes how strongly it applies.\n\n"
            + _NUMBERS_RULE
        ),
        tools=mechnari_tools.GAP_TOOLS,
    )


def build_risk_scorer() -> Agent:
    return Agent(
        name="risk_scorer",
        model=MODEL,
        description=(
            "Explains a part's risk scores and where the warranty record "
            "disagrees with the DFMEA on file."
        ),
        instruction=(
            "You are a quality engineer explaining DFMEA scores to a design team.\n\n"
            "Use get_risk_scores for the rescored rows, get_occurrence_evidence "
            "where Occurrence is disputed, and check_severity_consistency for "
            "severity that diverges from the organization standard.\n\n"
            "Explain risk by Action Priority, not RPN. If asked why, the reason is "
            "that multiplying the three scores misranks risk: a rare, hard-to-detect "
            "safety failure can score below a common nuisance. Mention RPN only as "
            "the legacy figure. If a tool reports that the Action Priority table is "
            "not yet verified, say so when you quote an AP value.\n\n"
            "Distinguish evidence measured on the part itself (OWN_PART) from a rate "
            "carried over from sibling parts (TYPE_HISTORY). Never present the "
            "second as a measurement of this part.\n\n"
            + _NUMBERS_RULE
        ),
        tools=mechnari_tools.RISK_TOOLS,
    )


def build_mitigation_writer() -> Agent:
    return Agent(
        name="mitigation_writer",
        model=MODEL,
        description=(
            "Turns findings into specific design, material and validation "
            "actions for a named component."
        ),
        instruction=(
            "You are a principal engineer writing design actions for heavy "
            "agricultural machinery.\n\n"
            "Work only from the findings and the component profile you are given. "
            "Write at most three actions, each one of: a material or compound "
            "change, a geometry or routing change, or a validation test mandate.\n\n"
            "Every action must suit the component's actual material, medium and "
            "operating environment. Do not recommend an elastomer change for a "
            "steel valve or a brazed joint, and do not repeat generic boilerplate "
            "that would read the same for any part. If the findings do not support "
            "a specific action, say that a physical review is needed and stop.\n\n"
            "No formal change-order paperwork, no filler."
        ),
        tools=[],
    )


# --- Coordinator: the entry point for `adk run` and `adk web` ------------

root_agent = Agent(
    name="mechnari_dfmea_copilot",
    model=MODEL,
    description=(
        "DFMEA reliability copilot for agricultural tractor programs, grounded "
        "in the company's own warranty and 8D history."
    ),
    instruction=(
        "You are Mechnari, a DFMEA copilot for heavy machinery engineering teams.\n\n"
        "Resolve what the user is asking about to a part_id first, using list_parts "
        "or get_part_profile if they describe a component in words.\n\n"
        "Delegate: completeness questions - what is missing, what was never checked "
        "- go to gap_analyst. Scoring questions - why this severity, is the "
        "occurrence right, what is the Action Priority - go to risk_scorer. Requests "
        "for what to do about a finding go to mitigation_writer, after the relevant "
        "findings have been gathered.\n\n"
        "Answer briefly and concretely, the way an engineer writes to another "
        "engineer. No marketing language.\n\n"
        + _NUMBERS_RULE
    ),
    tools=mechnari_tools.KNOWLEDGE_BASE_TOOLS,
    sub_agents=[build_gap_analyst(), build_risk_scorer(), build_mitigation_writer()],
)


# --- Fixed review pipeline as an ADK 2.x graph workflow ------------------
# Each node's return value is passed to the next as its input, so the review
# runs gaps -> scoring -> actions in order. Agents are rebuilt rather than
# reused, because an agent instance belongs to one parent.

dfmea_review_workflow = Workflow(
    name="dfmea_review_workflow",
    description="Full DFMEA review of one part: gaps, then scoring, then actions.",
    edges=[
        (
            "START",
            build_gap_analyst(),
            build_risk_scorer(),
            build_mitigation_writer(),
        )
    ],
)


# --- Programmatic entry point for the Streamlit dashboard ----------------

def _api_key_present() -> bool:
    return bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))


async def _run(question: str, user_id: str, session_id: str) -> str:
    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    runner = Runner(
        agent=root_agent, app_name=APP_NAME, session_service=session_service
    )
    message = types.Content(role="user", parts=[types.Part(text=question)])

    answer = ""
    try:
        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=message
        ):
            if event.is_final_response() and event.content and event.content.parts:
                answer = "".join(
                    part.text for part in event.content.parts if part.text
                ).strip()
    finally:
        await runner.close()
    return answer


def ask_copilot(question: str, session_id: str = "dashboard") -> dict:
    """
    Run one question through the ADK agent and return a result dict.

    Returns {"status": "success", "answer": ...} or {"status": "unavailable",
    "reason": ...}. The caller decides what to show; this never raises, because
    the dashboard has a deterministic fallback and a copilot outage must not
    take the risk analysis down with it.
    """
    if not _api_key_present():
        return {
            "status": "unavailable",
            "reason": "No GOOGLE_API_KEY or GEMINI_API_KEY in the environment.",
        }

    try:
        answer = asyncio.run(_run(question, "dashboard_user", session_id))
    except Exception as exc:  # noqa: BLE001 - surfaced to the user, not masked
        # Behind a TLS-inspecting corporate proxy this is where the failure
        # lands. Point REQUESTS_CA_BUNDLE and SSL_CERT_FILE at the corporate
        # root CA rather than disabling certificate verification.
        return {"status": "unavailable", "reason": "%s: %s" % (type(exc).__name__, exc)}

    if not answer:
        return {"status": "unavailable", "reason": "The agent returned no content."}
    return {"status": "success", "answer": answer}


if __name__ == "__main__":
    print("root_agent      :", root_agent.name)
    print("sub_agents      :", [a.name for a in root_agent.sub_agents])
    print("coordinator tools:", [t.__name__ for t in mechnari_tools.KNOWLEDGE_BASE_TOOLS])
    print("workflow        :", dfmea_review_workflow.name)
    print("model           :", MODEL)
    print("API key present :", _api_key_present())
    print("\nRun interactively with:  adk run mechnari_agent")
