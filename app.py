"""
Mechnari.ai - Enterprise AI DFMEA Risk Copilot for Heavy Machinery Manufacturing
================================================================================
Three role views over one deterministic core, not five feature panels stacked
on one page. The jobs are genuinely different, so the screens are genuinely
different shapes:

  Design Engineer   - describe a new part, get a grounded draft DFMEA with
                       every row cited to a warranty record, and see what
                       single change would bring a High-priority row down.
  Quality Engineer   - review what design engineers submit and audit any
                       part already on file, against the organization's
                       failure-effect registry and the warranty ledger.
  Company &
  Leadership         - program-wide coverage, the backtest against manual
                        review, and where risk concentrates.

Every number on every screen still comes from the same deterministic
engines (gap_detection, risk_engine, retrieval, backtest) - this file only
decides who sees which of their outputs, and in what shape.
"""

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import backtest
import data_layer
import gap_detection
import queue_store
import retrieval
import risk_engine
from mechnari_agent import agent as mechnari_agent

# ADK reads GOOGLE_API_KEY from the environment; the agent package loads
# the same .env so `adk run` and the dashboard behave identically.
load_dotenv()


# =====================================================================
# CACHED ENGINE CALLS
# =====================================================================

@st.cache_data
def cached_parts() -> pd.DataFrame:
    return data_layer.parts()


@st.cache_data
def cached_gaps() -> pd.DataFrame:
    return gap_detection.detect_gaps()


@st.cache_data
def cached_gap_metrics() -> dict:
    return gap_detection.headline_metrics()


@st.cache_data
def cached_severity_drift() -> pd.DataFrame:
    return gap_detection.severity_consistency_findings()


@st.cache_data
def cached_risk_metrics() -> dict:
    return risk_engine.headline_metrics()


@st.cache_data
def cached_occurrence_findings() -> pd.DataFrame:
    return risk_engine.occurrence_findings()


@st.cache_data
def cached_ap_changes() -> pd.DataFrame:
    return risk_engine.ap_change_findings()


@st.cache_data
def cached_detection_findings() -> pd.DataFrame:
    return risk_engine.detection_findings()


@st.cache_data
def cached_retrieval_metrics() -> dict:
    return retrieval.evaluate_retrieval()


@st.cache_data
def cached_backtest(cutoff: str) -> dict:
    result = backtest.temporal_backtest(cutoff)
    return {
        "summary": result["summary"],
        "train_records": result["train_records"],
        "test_records": result["test_records"],
        "detail": result["detail"].to_dict("records"),
    }


@st.cache_data
def cached_backtest_sweep() -> pd.DataFrame:
    return backtest.sweep()


@st.cache_data
def cached_cold_start() -> dict:
    result = backtest.cold_start_backtest()
    result["detail"] = result["detail"].to_dict("records")
    return result


@st.cache_data
def cached_proposal(description: str, part_type_id: str) -> dict:
    proposal = retrieval.propose_dfmea(description, part_type_id=part_type_id or None)
    # Streamlit caches by value; frames come back as plain records so the
    # cache key stays stable across reruns.
    proposal = dict(proposal)
    proposal["neighbours"] = proposal["neighbours"].to_dict("records")
    proposal["candidates"] = proposal["candidates"].to_dict("records")
    proposal.pop("inference", None)
    return proposal


# =====================================================================
# PAGE CONFIG & STYLING
# =====================================================================

st.set_page_config(
    page_title="Mechnari.ai - Enterprise AI DFMEA Risk Copilot",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Streamlit's markdown renderer still runs its markdown pass before trusting
# this as HTML, and asterisk pairs inside /* ... */ CSS comments get read as
# emphasis markers and mangled - it truncated the whole style block the first
# time through. So the CSS injected below carries no C-style comments; the
# explanation lives here instead. One committed dark theme (see
# .streamlit/config.toml for the native-widget half of this) - a warm-black
# ground with a slight green bias, not a flat near-black, so cards and the
# sidebar read as distinct surfaces rather than one flat panel. Semantic
# colors (critical / warning / ok) are kept separate from the accent, since
# Action Priority already owns red/amber/green everywhere on this app - the
# accent (petrol teal) is reserved for actions and identity.
st.markdown("""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
    <style>
    :root {
        --bg: #0B1210;
        --bg-elevated: #101A17;
        --surface: #16211D;
        --surface-hover: #1C2925;
        --border: #263631;
        --border-strong: #37493F;
        --ink: #E7EEEC;
        --ink-soft: #9FB0AA;
        --ink-faint: #6D7E78;
        --accent: #3FA895;
        --accent-strong: #59C4B0;
        --accent-ink: #06120F;
        --accent-soft: #16302B;
        --accent-line: #2E5C51;
        --crit: #E4806A;
        --crit-soft: #2E1811;
        --warn: #E0AC55;
        --warn-soft: #2E230A;
        --ok: #7BC98D;
        --ok-soft: #16261B;
        --display: "Archivo", "Helvetica Neue", Arial, sans-serif;
        --body: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
        --mono: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
    }
    html, body, [class*="css"] { font-family: var(--body); }
    [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: var(--bg); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stMainBlockContainer"] { padding-top: 1.6rem; max-width: 1240px; }
    h1, h2, h3, h4, [data-testid="stHeading"] * {
        font-family: var(--display) !important;
        letter-spacing: -0.01em;
    }
    [data-testid="stMarkdownContainer"] p { color: var(--ink); }
    [data-testid="stCaptionContainer"] { color: var(--ink-faint) !important; }
    code { font-family: var(--mono) !important; }
    hr { border-color: var(--border) !important; }
    [data-testid="stSidebar"] {
        background: var(--bg-elevated);
        border-right: 1px solid var(--border);
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
        font-size: 1.25rem !important; margin-bottom: 0 !important;
    }
    [data-testid="stSidebarUserContent"] hr { margin: 0.9rem 0; }
    .mechnari-masthead {
        background: linear-gradient(135deg, var(--surface) 0%, var(--bg-elevated) 100%);
        border: 1px solid var(--border); border-left: 4px solid var(--accent);
        border-radius: 10px; padding: 22px 26px; margin-bottom: 22px;
    }
    .mechnari-masthead .eyebrow {
        font-family: var(--mono); font-size: 11px; letter-spacing: .12em;
        text-transform: uppercase; color: var(--accent); margin-bottom: 6px;
    }
    .mechnari-masthead h1 {
        font-size: 1.65rem !important; margin: 0 0 8px !important; color: var(--ink) !important;
    }
    .mechnari-masthead p {
        color: var(--ink-soft) !important; margin: 0; max-width: 74ch; line-height: 1.55;
    }
    .stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
        border-radius: 8px !important; font-family: var(--body) !important;
        font-weight: 600 !important; letter-spacing: .01em;
        transition: filter .12s ease, transform .04s ease;
    }
    .stButton > button:active, .stFormSubmitButton > button:active { transform: scale(.99); }
    [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
        background: var(--accent) !important; color: var(--accent-ink) !important; border: none !important;
    }
    [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {
        background: var(--accent-strong) !important;
    }
    [data-testid="stBaseButton-secondary"] {
        background: transparent !important; color: var(--ink) !important;
        border: 1px solid var(--border-strong) !important;
    }
    [data-testid="stBaseButton-secondary"]:hover {
        border-color: var(--accent) !important; color: var(--accent-strong) !important;
    }
    [data-testid="stTabs"] [role="tablist"] {
        gap: 4px; background: var(--surface); padding: 4px;
        border-radius: 10px; border: 1px solid var(--border); width: fit-content;
    }
    [data-testid="stTab"] {
        font-family: var(--body); font-weight: 600; font-size: 14px;
        border-radius: 7px !important; color: var(--ink-soft) !important;
        padding: 10px 18px !important;
    }
    [data-testid="stTab"][aria-selected="true"] {
        background: var(--accent-soft) !important; color: var(--accent-strong) !important;
    }
    [data-baseweb="tab-highlight"] { background: transparent !important; }
    [data-testid="stTabs"] [data-baseweb="tab-border"] { display: none; }
    [data-testid="stMetric"] {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: 10px; padding: 14px 16px 12px;
    }
    [data-testid="stMetricLabel"] {
        font-family: var(--mono) !important; font-size: 10.5px !important;
        letter-spacing: .07em; text-transform: uppercase; color: var(--ink-faint) !important;
    }
    [data-testid="stMetricLabel"] p {
        white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
        line-height: 1.35 !important;
    }
    [data-testid="stMetricValue"] {
        font-family: var(--display) !important; font-weight: 700 !important;
        color: var(--ink) !important; font-size: clamp(1.05rem, 4vw, 1.75rem) !important;
    }
    [data-testid="stMetricValue"] p { overflow: visible !important; text-overflow: clip !important; }
    [data-testid="stMetric"] { min-width: 0; }
    [data-testid="stMetricDelta"] { font-family: var(--mono) !important; font-size: 12.5px !important; }
    [data-testid="stExpander"] {
        background: var(--surface); border: 1px solid var(--border) !important;
        border-radius: 10px !important; overflow: hidden;
    }
    [data-testid="stExpander"] summary { font-weight: 600 !important; }
    [data-testid="stExpander"] summary:hover { background: var(--surface-hover) !important; }
    [data-testid="stExpanderDetails"] { border-top: 1px solid var(--border); }
    [data-testid="stForm"] {
        background: var(--surface); border: 1px solid var(--border);
        border-radius: 10px; padding: 18px 20px 8px;
    }
    [data-testid="stTextInputRootElement"], [data-testid="stTextAreaRootElement"],
    [data-baseweb="select"] > div {
        background: var(--bg-elevated) !important; border-color: var(--border-strong) !important;
        border-radius: 7px !important;
    }
    [data-testid="stWidgetLabel"] p {
        font-size: 12.5px !important; font-weight: 600 !important; color: var(--ink-soft) !important;
    }
    [data-testid="stAlertContentSuccess"] { color: var(--ok) !important; }
    [data-testid="stAlertContentWarning"] { color: var(--warn) !important; }
    [data-testid="stAlertContentError"] { color: var(--crit) !important; }
    [data-testid="stAlertContentInfo"] { color: var(--accent-strong) !important; }
    [data-testid="stAlert"] { border-radius: 9px !important; }
    [data-testid="stAlertContainer"] { border-radius: 9px !important; border: 1px solid transparent; }
    [data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) { background: var(--ok-soft) !important; border-color: var(--ok); }
    [data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) { background: var(--warn-soft) !important; border-color: var(--warn); }
    [data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) { background: var(--crit-soft) !important; border-color: var(--crit); }
    [data-testid="stAlertContainer"]:has([data-testid="stAlertContentInfo"]) { background: var(--accent-soft) !important; border-color: var(--accent-line); }
    [data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
    </style>
""", unsafe_allow_html=True)


# =====================================================================
# SIDEBAR
# =====================================================================

st.sidebar.image("https://img.icons8.com/color/96/tractor.png", width=70)
st.sidebar.title("⚙️ Mechnari.ai")
st.sidebar.caption("Enterprise AI DFMEA Risk Copilot (1,000+ Part Systems)")

st.sidebar.markdown("---")

# Regenerating the CSVs while the app runs leaves both this process's data
# cache and Streamlit's result cache holding the old knowledge base, which
# looks like the app ignoring your changes. This clears both.
if st.sidebar.button("🔄 Reload knowledge base", use_container_width=True):
    data_layer.reload()
    retrieval.reload()
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filter")

try:
    _all_packages = sorted(cached_parts()["system_package"].unique().tolist())
except data_layer.DatasetError:
    _all_packages = []
selected_package = st.sidebar.selectbox(
    "System Package (used across tabs):", ["All System Packages"] + _all_packages)

st.sidebar.markdown("---")
st.sidebar.subheader("📐 Program Scale")
st.sidebar.caption(
    "A DFMEA for one 10-14 part assembly runs about a week as a "
    "cross-functional workshop. A tractor is 1,000+ parts - on the order "
    "of 70-100 such workshops per program, run by different people at "
    "different times. That is the actual mechanism behind coverage drift, "
    "not a training gap."
)


# =====================================================================
# MASTHEAD
# =====================================================================

st.markdown("""
<div class="mechnari-masthead">
    <div class="eyebrow">Enterprise DFMEA Risk Copilot</div>
    <h1>Mechnari.ai — Grounded in Your Own Warranty History</h1>
    <p>Three views of the same deterministic core - Design Engineer, Quality Engineer, and
    Company &amp; Leadership - because drafting, auditing and reporting on risk are different jobs.</p>
</div>
""", unsafe_allow_html=True)


def _filtered(df: pd.DataFrame, column: str = "system_package") -> pd.DataFrame:
    if selected_package == "All System Packages" or df.empty or column not in df.columns:
        return df
    return df[df[column] == selected_package]


# =====================================================================
# DESIGN ENGINEER
# =====================================================================

_AP_BADGE = {"H": "🔴 High", "M": "🟠 Medium", "L": "🟢 Low"}


def _plain_candidate_row(row: pd.Series) -> dict:
    """The subset of a candidate row worth keeping once it leaves the engine."""
    return {
        "mode_id": str(row["mode_id"]),
        "failure_mode": str(row["failure_mode"]),
        "potential_cause": str(row["potential_cause"]),
        "effect_description": str(row["effect_description"]),
        "severity": int(row["severity"]),
        "occurrence": int(row["occurrence"]),
        "detection": int(row["detection"]),
        "action_priority": str(row["action_priority"]),
        "learned_from": str(row["learned_from"]),
        "evidence_ids": str(row["evidence_ids"]),
        "recommended_action": str(row["recommended_action"]),
    }


def render_design_engineer_tab() -> None:
    st.subheader("New Part Intake")
    st.caption(
        "Describe the part you're designing. Mechnari identifies what kind of part it "
        "is, pulls the failure modes the company has already proven on parts like it, "
        "and drafts a starting DFMEA - evidence on every row, and what single change "
        "would bring a High row down."
    )

    with st.form("intake_form"):
        c1, c2 = st.columns(2)
        with c1:
            part_name = st.text_input("Component name", value="New EPDM Fuel Return Line")
            material = st.text_input("Material / compound", value="EPDM rubber with textile braid")
        with c2:
            function = st.text_area(
                "Elementary function", height=104,
                value="Return unburnt diesel from the injector rail to the tank")

        try:
            type_options = data_layer.part_types().sort_values("part_type_name")
            type_labels = ["(let retrieval suggest)"] + type_options["part_type_name"].tolist()
            type_ids = [""] + type_options["part_type_id"].tolist()
            package_options = sorted(cached_parts()["system_package"].unique().tolist())
        except data_layer.DatasetError:
            type_labels, type_ids, package_options = ["(let retrieval suggest)"], [""], []

        cc1, cc2 = st.columns(2)
        with cc1:
            chosen_label = st.selectbox("Confirm part type (optional)", type_labels)
        with cc2:
            system_package = st.selectbox(
                "System package (for your own record)", package_options or ["Unspecified"])

        submitted = st.form_submit_button("🔍 Identify & Draft DFMEA", type="primary")

    if submitted:
        query = retrieval.describe(part_name, function, material)
        chosen_type = type_ids[type_labels.index(chosen_label)]
        try:
            proposal = cached_proposal(query, chosen_type)
        except data_layer.DatasetError as exc:
            st.warning("Knowledge base not ready: %s" % exc)
            proposal = {"status": "no_match", "reason": str(exc)}

        st.session_state.de_proposal = proposal
        st.session_state.de_intake = {
            "part_name": part_name, "function": function,
            "material": material, "system_package": system_package,
        }
        st.session_state.de_accept = {}

    proposal = st.session_state.get("de_proposal")
    intake = st.session_state.get("de_intake")

    if not proposal:
        st.info("Fill in the form above and click **Identify & Draft DFMEA**.")
        return

    if proposal["status"] != "success":
        st.warning(proposal["reason"])
        return

    neighbours = pd.DataFrame(proposal["neighbours"])
    candidates = pd.DataFrame(proposal["candidates"])

    if proposal["confirmed"]:
        st.success("Part type confirmed as **%s**." % proposal["part_type_name"])
    elif proposal["confident"]:
        st.success(
            "Suggested part type: **%s** (%.0f%% of the neighbour vote). %s"
            % (proposal["part_type_name"], proposal["confidence"] * 100, proposal["reason"]))
    else:
        st.warning(
            "Suggested part type: **%s**, but %s"
            % (proposal["part_type_name"],
               proposal["reason"][0].lower() + proposal["reason"][1:]))

    if not neighbours.empty:
        chip_line = "  ·  ".join(
            "`%.3f` %s (%s)" % (r["similarity"], r["part_id"], r["item_reference"])
            for _, r in neighbours.head(4).iterrows())
        st.caption("Closest historical parts: " + chip_line)

    if candidates.empty:
        st.info("No candidate failure modes are known for this part type yet.")
        return

    st.markdown("##### Draft DFMEA — %d candidate rows from company history" % len(candidates))
    st.caption(
        "Uncheck a row to leave it out of the draft. High rows show what single "
        "change - Occurrence or Detection, computed against the real AP table, not "
        "invented - would bring the priority down."
    )

    accept_state = st.session_state.setdefault("de_accept", {})
    for _, row in candidates.iterrows():
        mode_id = row["mode_id"]
        default_checked = accept_state.get(mode_id, True)
        badge = _AP_BADGE.get(row["action_priority"], row["action_priority"])
        header = "%s — S%d O%d D%d, %s" % (row["failure_mode"], row["severity"],
                                            row["occurrence"], row["detection"], badge)
        with st.expander(header, expanded=(row["action_priority"] == "H")):
            included = st.checkbox("Include in draft", value=default_checked,
                                   key="chk_" + mode_id)
            accept_state[mode_id] = included

            st.markdown("**Potential cause:** %s" % row["potential_cause"])
            st.markdown("**Effect:** %s" % row["effect_description"])
            st.markdown("**Learned from:** %s" % row["learned_from"])
            st.markdown("**Evidence:** %s" % row["evidence_ids"])
            st.markdown("**Recommended action:** %s" % row["recommended_action"])

            if row["action_priority"] != "L":
                levers = risk_engine.find_ap_levers(
                    row["severity"], row["occurrence"], row["detection"])
                if levers["levers"]:
                    lines = [
                        "- Improving **%s** from %d to %d would move this to **%s**."
                        % (lever["factor"].title(), lever["from"], lever["to"],
                           lever["resulting_ap"])
                        for lever in levers["levers"]
                    ]
                    st.info("**What would bring this down**\n" + "\n".join(lines))
                else:
                    st.caption(
                        "No single-factor change in Occurrence or Detection alone moves "
                        "this below %s at the current Severity - both would need to "
                        "improve together, or the effect itself needs to change." % badge)

    accepted_rows, declined_rows = [], []
    for _, row in candidates.iterrows():
        target = accepted_rows if accept_state.get(row["mode_id"], True) else declined_rows
        target.append(_plain_candidate_row(row))

    declined_high = [r for r in declined_rows if r["action_priority"] == "H"]
    if declined_high:
        st.warning(
            "%d declined row(s) are High priority - Quality will see these were "
            "considered and left out, not missed." % len(declined_high))

    st.markdown("---")
    fcol1, fcol2 = st.columns([3, 1])
    with fcol1:
        st.caption("%d of %d candidate rows included in the draft."
                   % (len(accepted_rows), len(candidates)))
    with fcol2:
        if st.button("📤 Send Draft to Quality Review", type="primary",
                     use_container_width=True):
            draft_id = queue_store.submit_draft(
                part_name=intake["part_name"], function=intake["function"],
                material=intake["material"], system_package=intake["system_package"],
                part_type_name=proposal["part_type_name"],
                accepted_rows=accepted_rows, declined_rows=declined_rows,
            )
            st.success(
                "Submitted as **%s**. Open the Quality Engineer tab to see it in "
                "the queue." % draft_id)

    st.markdown("---")
    with st.expander("📏 How good is this matching? Leave-one-out evaluation"):
        st.caption(
            "Each of the 50 parts is hidden in turn and the remaining 49 are asked "
            "what kind of part it is. Measured, not asserted."
        )
        try:
            metrics = cached_retrieval_metrics()
        except data_layer.DatasetError as exc:
            st.warning("Knowledge base not ready: %s" % exc)
        else:
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Mode recall", "%.0f%%" % (metrics["mode_recall"] * 100),
                          help="Of the failure modes that truly apply to the held-out "
                               "part, the share the proposal surfaces.")
            with m2:
                st.metric("True type among neighbours",
                          "%.0f%%" % (metrics["type_recall_at_k"] * 100))
            with m3:
                st.metric("Shortlist size", "%.0f of %d"
                          % (metrics["mean_modes_proposed"], metrics["catalog_size"]))
            st.caption(
                "Leading part type exactly right: %.0f%%. Top-1 type prediction is weak "
                "on a 50-part corpus over 17 types, which is why the agent proposes "
                "modes for every kind of part among the neighbours rather than asserting "
                "one." % (metrics["type_top1_accuracy"] * 100))

    st.markdown("---")
    st.subheader("🤖 Ask Mechnari Copilot")
    st.caption(
        "A Google ADK agent team: a coordinator delegates to a gap analyst, a risk "
        "scorer and a mitigation writer. The agents read findings through read-only "
        "tools and explain them - every score still comes from the deterministic engines."
    )

    try:
        parts_for_copilot = cached_parts()
    except data_layer.DatasetError:
        parts_for_copilot = pd.DataFrame()

    if not parts_for_copilot.empty:
        c_sel, c_q = st.columns([1, 2])
        with c_sel:
            part_options = ["%s - %s" % (r["part_id"], r["item_reference"])
                            for _, r in parts_for_copilot.iterrows()]
            selected_component_str = st.selectbox("Ask about an existing part:", part_options)
            selected_pid = selected_component_str.split(" - ")[0]
            selected_part_row = parts_for_copilot[
                parts_for_copilot["part_id"] == selected_pid].iloc[0]

        with c_q:
            default_prompt = (
                "Why does part '%s' (ID: %s) score the way it does, and what are "
                "the detailed design mitigation steps?"
                % (selected_part_row["item_reference"], selected_pid))
            user_question = st.text_area("Ask Mechnari Copilot AI:", value=default_prompt,
                                         height=90)
            ask_btn = st.button("💬 Ask Mechnari Copilot AI", type="primary")

        if ask_btn:
            with st.spinner("🤖 Mechnari agent team analysing %s..." % selected_pid):
                question = (
                    "Component %s (%s), a %s in %s, material %s.\n"
                    "Engineer's question: %s\n\n"
                    "Use your tools to ground the answer. Cover: what the DFMEA on "
                    "file never analysed for this kind of part, whether the scores "
                    "are supported by the warranty record, and what to do about it."
                    % (selected_pid, selected_part_row["item_reference"],
                       selected_part_row["material_type"],
                       selected_part_row["system_package"],
                       selected_part_row["material_type"], user_question))

                result = mechnari_agent.ask_copilot(question, session_id=selected_pid)

                if result["status"] == "success":
                    ai_response = result["answer"]
                else:
                    st.caption("Agent unavailable (%s). Showing the deterministic "
                               "analysis instead." % result["reason"])
                    ai_response = _deterministic_analysis_text(selected_pid, selected_part_row)

                st.markdown("### 🤖 Mechnari Copilot AI Response")
                st.info(ai_response)


def _deterministic_analysis_text(part_id: str, part_row: pd.Series) -> str:
    gaps = gap_detection.detect_gaps(part_id)
    scored = risk_engine.scored_worksheet(part_id)
    occurrence = risk_engine.occurrence_findings()
    occurrence = occurrence[occurrence["part_id"] == part_id]

    lines = [
        "### Deterministic analysis - %s (%s)" % (part_id, part_row["item_reference"]),
        "",
        "**Part type:** %s | **Material:** %s" % (
            scored["part_type_name"].iloc[0] if not scored.empty else "n/a",
            part_row["material_type"]),
        "",
        "**1. Failure modes known for this kind of part that this DFMEA never "
        "analysed (%d)**" % len(gaps),
    ]
    if gaps.empty:
        lines.append("- None. Coverage is complete for this part type.")
    else:
        for _, row in gaps.head(5).iterrows():
            lines.append("- **S=%d** %s - learned from %s (%s)" % (
                row["standard_severity"], row["failure_mode"],
                row["learned_from"], row["evidence_ids"]))

    lines += ["", "**2. Scores on file, checked against the warranty record**"]
    if occurrence.empty:
        lines.append("- Occurrence on file is consistent with the claims data.")
    else:
        for _, row in occurrence.head(5).iterrows():
            lines.append(
                "- %s: O filed %d, O from claims %d (%.1f per 1000 units, %d "
                "claims, %s) - %s" % (
                    row["failure_mode"], row["occurrence"], row["derived_occurrence"],
                    row["claims_per_1000"], row["field_claims"], row["evidence_scope"],
                    row["evidence_ids"]))

    lines += ["", "**3. Action Priority**"]
    if scored.empty:
        lines.append("- No DFMEA rows on file for this part.")
    else:
        for _, row in scored.head(5).iterrows():
            lines.append("- %s: AP %s on evidence (filed as %s), S=%d O=%d D=%d, "
                         "legacy RPN %d" % (
                             row["failure_mode"], row["ap_evidence_based"],
                             row["ap_as_filed"], row["severity_standard"],
                             row["evidence_occurrence"], row["detection"], row["rpn_legacy"]))
        if not risk_engine.AP_TABLE_VERIFIED:
            lines.append("")
            lines.append("_Action Priority cell values are provisional pending "
                         "verification against the DFMEA Action Priority table in "
                         "AIAG-VDA._")

    return "\n".join(lines)


# =====================================================================
# QUALITY ENGINEER
# =====================================================================

_STATUS_LABEL = {
    queue_store.STATUS_NEEDS_REVIEW: "🟠 Needs Review",
    queue_store.STATUS_RETURNED: "⚪ Returned",
    queue_store.STATUS_APPROVED: "🟢 Approved",
}


def _render_draft_audit(draft: dict) -> None:
    st.markdown("###### %s — %s" % (draft["draft_id"], draft["part_name"]))
    st.caption("%s · submitted by %s · %s"
               % (draft["part_type_name"], draft["submitted_by"],
                  draft["submitted_at"][:19].replace("T", " ")))

    accepted = draft["accepted_rows"]
    declined = draft["declined_rows"]
    high_declined = [r for r in declined if r["action_priority"] == "H"]

    if high_declined:
        st.markdown("**⚠️ %d High-priority candidate(s) were declined by the design "
                    "engineer:**" % len(high_declined))
        for r in high_declined:
            st.markdown("- %s (S=%d) — learned from %s" % (
                r["failure_mode"], r["severity"], r["learned_from"]))
    else:
        st.markdown("**✓ No High-priority candidates were declined.**")

    st.markdown("**Accepted rows (%d)**" % len(accepted))
    if accepted:
        adf = pd.DataFrame(accepted)[
            ["failure_mode", "severity", "occurrence", "detection",
             "action_priority", "evidence_ids"]]
        adf.columns = ["Failure Mode", "S", "O", "D", "AP", "8D Records"]
        st.dataframe(adf, use_container_width=True, hide_index=True)

    comments = st.text_area("Comments back to the design engineer",
                            value=draft.get("review_comments", ""),
                            key="qe_comments_" + draft["draft_id"])
    b1, b2 = st.columns(2)
    with b1:
        if st.button("↩️ Return with Comments", key="qe_return_" + draft["draft_id"],
                     use_container_width=True):
            queue_store.set_status(draft["draft_id"], queue_store.STATUS_RETURNED, comments)
            st.success("Returned to %s." % draft["submitted_by"])
            st.rerun()
    with b2:
        if st.button("✅ Approve", key="qe_approve_" + draft["draft_id"], type="primary",
                     use_container_width=True):
            queue_store.set_status(draft["draft_id"], queue_store.STATUS_APPROVED, comments)
            st.success("Approved.")
            st.rerun()


def _render_existing_part_audit(part_id: str) -> None:
    try:
        sev_all = cached_severity_drift()
        occ_all = cached_occurrence_findings()
        gaps = gap_detection.detect_gaps(part_id)
    except data_layer.DatasetError as exc:
        st.warning("Knowledge base not ready: %s" % exc)
        return

    sev_rows = sev_all[sev_all["part_id"] == part_id]
    occ_rows = occ_all[occ_all["part_id"] == part_id]

    if sev_rows.empty:
        st.success("✓ Severity matches the organization standard for every effect on this part.")
    else:
        for _, r in sev_rows.iterrows():
            st.error("⚠ **%s**: %s (scored S=%d, standard S=%d for %s)"
                     % (r["failure_mode"], r["finding"], r["severity"],
                        r["standard_severity"], r["effect_description"]))

    if occ_rows.empty:
        st.success("✓ Occurrence on file is consistent with the warranty record.")
    else:
        for _, r in occ_rows.iterrows():
            st.warning("~ **%s**: filed O=%d, %s to O=%d (%s, %s)"
                       % (r["failure_mode"], r["occurrence"], r["finding"].lower(),
                          r["derived_occurrence"], r["evidence_scope"], r["evidence_ids"]))

    if gaps.empty:
        st.success("✓ Coverage complete - every catalogued mode for this part's "
                   "type and family is analysed.")
    else:
        safety = int((gaps["standard_severity"] >= 9).sum())
        st.error("⚠ %d catalogued failure mode(s) not yet analysed, %d at severity 9+."
                 % (len(gaps), safety))
        with st.expander("Show unanalysed modes"):
            gdf = gaps[["failure_mode", "standard_severity", "priority",
                       "learned_from", "evidence_ids"]].rename(columns={
                "failure_mode": "Failure Mode", "standard_severity": "S",
                "priority": "Priority", "learned_from": "Learned From",
                "evidence_ids": "8D Records"})
            st.dataframe(gdf, use_container_width=True, hide_index=True)


def render_quality_engineer_tab() -> None:
    st.subheader("Review Queue")
    st.caption(
        "Audits, not drafting. Submitted drafts and existing parts on file, checked "
        "against the organization's failure-effect registry and the warranty record "
        "before sign-off - the same deterministic engines, read as an audit trail."
    )

    queue = queue_store.list_queue()

    left, right = st.columns([1, 2])
    with left:
        st.markdown("###### Submitted drafts")
        if not queue:
            st.caption("No drafts submitted yet - use the Design Engineer tab to send one.")
        selected_draft_id = st.session_state.get("qe_selected_draft")
        for draft in queue:
            label = "%s — %s\n%s · %d rows" % (
                draft["draft_id"], draft["part_name"],
                _STATUS_LABEL.get(draft["status"], draft["status"]),
                len(draft["accepted_rows"]))
            is_selected = draft["draft_id"] == selected_draft_id
            if st.button(label, key="qbtn_" + draft["draft_id"], use_container_width=True,
                        type="primary" if is_selected else "secondary"):
                st.session_state.qe_selected_draft = draft["draft_id"]
                st.rerun()

    with right:
        draft_id = st.session_state.get("qe_selected_draft")
        draft = queue_store.get_draft(draft_id) if draft_id else None
        if not draft:
            st.info("Select a submitted draft on the left, or audit an existing part below.")
        else:
            _render_draft_audit(draft)

    st.markdown("---")
    st.markdown("##### Audit an existing part")
    st.caption(
        "The same audit suite, run against a part already on file: severity "
        "consistency, occurrence vs. the warranty record, and coverage."
    )
    try:
        parts = _filtered(cached_parts())
    except data_layer.DatasetError as exc:
        st.warning("Knowledge base not ready: %s" % exc)
        return

    if parts.empty:
        st.caption("No parts match the current filter.")
    else:
        part_labels = ["%s — %s" % (r["part_id"], r["item_reference"])
                       for _, r in parts.iterrows()]
        chosen = st.selectbox("Part", part_labels, key="qe_part_select")
        _render_existing_part_audit(chosen.split(" — ")[0])

    st.markdown("---")
    with st.expander("📋 Coverage and rescoring across every part (bulk view)"):
        _render_bulk_gap_and_rescoring_view()


def _render_bulk_gap_and_rescoring_view() -> None:
    try:
        gap_metrics = cached_gap_metrics()
        gaps_all = cached_gaps()
        drift_all = cached_severity_drift()
        risk_metrics = cached_risk_metrics()
        occurrence_all = cached_occurrence_findings()
        ap_changes_all = cached_ap_changes()
        detection_all = cached_detection_findings()
    except data_layer.DatasetError as exc:
        st.warning("Knowledge base not ready: %s" % exc)
        return

    gaps_view = _filtered(gaps_all)
    drift_view = _filtered(drift_all)
    occurrence_view = _filtered(occurrence_all)
    ap_changes_view = _filtered(ap_changes_all)
    detection_view = _filtered(detection_all)

    st.markdown("###### Gap detection")
    if gaps_view.empty:
        st.success("No unanalysed failure modes for the current filter.")
    else:
        safety_gaps = int((gaps_view["standard_severity"] >= 9).sum())
        g1, g2, g3, g4 = st.columns(4)
        with g1:
            st.metric("Known Modes Not Analysed", len(gaps_view))
        with g2:
            st.metric("🔴 Safety / Regulatory (S≥9)", safety_gaps)
        with g3:
            st.metric("Parts Affected", int(gaps_view["part_id"].nunique()))
        with g4:
            st.metric("Mean DFMEA Coverage", "%s%%" % gap_metrics.get("mean_coverage_pct", 0))

        gap_display = gaps_view[[
            "part_id", "item_reference", "failure_mode", "standard_severity",
            "priority", "learned_from", "evidence_ids"]].rename(columns={
            "part_id": "Part ID", "item_reference": "Component",
            "failure_mode": "Unanalysed Failure Mode", "standard_severity": "S",
            "priority": "Priority", "learned_from": "Learned From",
            "evidence_ids": "8D Records"})
        st.dataframe(gap_display, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Export Gap Findings (CSV)",
            gap_display.to_csv(index=False).encode("utf-8"),
            "Mechnari_Gap_Findings.csv", "text/csv")

        if not drift_view.empty:
            st.markdown("###### Severity consistency")
            st.dataframe(
                drift_view[["part_id", "item_reference", "failure_mode",
                           "severity", "standard_severity", "finding"]].rename(columns={
                    "part_id": "Part ID", "item_reference": "Component",
                    "failure_mode": "Failure Mode", "severity": "Scored S",
                    "standard_severity": "Standard S", "finding": "Finding"}),
                use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("###### Occurrence vs. warranty record")
    if occurrence_view.empty:
        st.info("No occurrence disagreements for the current filter.")
    else:
        own_part = occurrence_view[occurrence_view["evidence_scope"] == "OWN_PART"]
        understated_own = int((own_part["occurrence_delta"] > 0).sum())
        r1, r2, r3 = st.columns(3)
        with r1:
            st.metric("Occurrence Understated (own part)", understated_own)
        with r2:
            st.metric("Action Priority: High",
                      risk_metrics.get("ap_high_evidence_based", 0),
                      delta="%+d vs as filed" % (
                          risk_metrics.get("ap_high_evidence_based", 0)
                          - risk_metrics.get("ap_high_as_filed", 0)))
        with r3:
            escalations = int((ap_changes_view["direction"] == "Escalates").sum()) \
                if not ap_changes_view.empty else 0
            st.metric("Rows Escalating on Evidence", escalations)

        if not risk_metrics.get("ap_table_verified", False):
            st.caption(
                "⚠️ Action Priority values are provisional - band structure and 8 "
                "cells are sourced, the rest still need checking against the DFMEA "
                "table in AIAG-VDA. RPN is retained as a legacy column."
            )

        occ_display = occurrence_view[[
            "part_id", "item_reference", "failure_mode", "occurrence",
            "derived_occurrence", "finding", "evidence_scope", "evidence_ids"]].rename(
            columns={"part_id": "Part ID", "item_reference": "Component",
                    "failure_mode": "Failure Mode", "occurrence": "O as Filed",
                    "derived_occurrence": "O from Claims", "finding": "Finding",
                    "evidence_scope": "Evidence", "evidence_ids": "8D Records"})
        st.dataframe(occ_display, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 Export Rescoring Findings (CSV)",
            occ_display.to_csv(index=False).encode("utf-8"),
            "Mechnari_Rescoring_Findings.csv", "text/csv")

        if not detection_view.empty:
            st.markdown("###### Detection not supported by the escape stage")
            st.dataframe(
                detection_view[["part_id", "failure_mode", "detection",
                               "detection_floor", "worst_escape_stage"]].rename(columns={
                    "part_id": "Part ID", "failure_mode": "Failure Mode",
                    "detection": "D as Filed", "detection_floor": "D Floor",
                    "worst_escape_stage": "Escaped To"}),
                use_container_width=True, hide_index=True)


# =====================================================================
# COMPANY & LEADERSHIP
# =====================================================================

def render_company_tab() -> None:
    st.subheader("Program Health")
    st.caption(
        "Rollup, not row detail. What the deterministic engines catch across the "
        "whole program, and the evidence that they'd have caught it without Mechnari."
    )

    try:
        gap_metrics = cached_gap_metrics()
        run = cached_backtest(backtest.DEFAULT_CUTOFF)
        cold = cached_cold_start()
    except data_layer.DatasetError as exc:
        st.warning("Knowledge base not ready: %s" % exc)
        return

    summary = run["summary"]

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.metric("Parts Covered", "%d/%d" % (gap_metrics["parts_analysed"],
                                               gap_metrics["parts_analysed"]))
    with k2:
        st.metric("Mean DFMEA Coverage", "%.0f%%" % gap_metrics["mean_coverage_pct"])
    with k3:
        st.metric("Open Safety Gaps (S≥9)", gap_metrics["safety_gaps"])
    with k4:
        st.metric("Backtest Lift vs. Manual",
                  "+%.0f pts" % ((summary["mechnari_recall"] - summary["dfmea_recall"]) * 100),
                  help="%.0f%% → %.0f%% recall" % (
                      summary["dfmea_recall"] * 100, summary["mechnari_recall"] * 100))
    with k5:
        st.metric("Claims Behind Newly-Caught", summary["newly_caught_claims"])

    cL, cR = st.columns([1.3, 1])
    with cL:
        st.markdown("##### Would this have caught what manual review missed?")
        sweep_frame = cached_backtest_sweep()
        chart_df = sweep_frame.set_index("cutoff")[["dfmea_recall", "mechnari_recall"]].copy()
        chart_df.columns = ["Manual DFMEA", "Mechnari"]
        st.line_chart(chart_df)
        st.caption(
            "A DFMEA for one 10-14 part assembly runs about a week as a "
            "cross-functional workshop; a tractor is 1,000+ parts - on the order of "
            "70-100 such workshops per program, run by different people at "
            "different times. That is the actual mechanism behind the gap above."
        )

    with cR:
        st.markdown("##### Open safety gaps by system package")
        gaps_all = cached_gaps()
        if gaps_all.empty:
            st.caption("No open gaps.")
        else:
            by_pkg = (gaps_all[gaps_all["standard_severity"] >= 9]
                     .groupby("system_package").size().sort_values(ascending=False))
            if by_pkg.empty:
                st.caption("No safety-severity gaps open.")
            else:
                max_n = float(by_pkg.max())
                for pkg, n in by_pkg.items():
                    bc1, bc2, bc3 = st.columns([2.2, 3.5, 0.6])
                    with bc1:
                        st.caption(pkg)
                    with bc2:
                        st.progress(float(n) / max_n if max_n else 0.0)
                    with bc3:
                        st.caption(str(int(n)))

    st.markdown("---")
    with st.expander("🧪 Full backtest detail (cutoff sweep, missed failures, cold start)"):
        _render_backtest_detail()

    st.markdown("---")
    with st.expander("📊 Full DFMEA reference matrix (export)"):
        try:
            parts = _filtered(cached_parts())
        except data_layer.DatasetError as exc:
            st.warning("Knowledge base not ready: %s" % exc)
        else:
            ref_display = parts[[
                "part_id", "system_package", "item_reference", "part_type_name",
                "material_type", "drawing_spec_ref"]].rename(columns={
                "part_id": "Part ID", "system_package": "System Package",
                "item_reference": "Component", "part_type_name": "Part Type",
                "material_type": "Material", "drawing_spec_ref": "Drawing Spec"})
            st.dataframe(ref_display, use_container_width=True, hide_index=True)
            st.download_button(
                "📥 Export DFMEA Reference Matrix (CSV)",
                ref_display.to_csv(index=False).encode("utf-8"),
                "Mechnari_DFMEA_Export.csv", "text/csv")


def _render_backtest_detail() -> None:
    st.caption(
        "The warranty history is cut at a date. The system is given only what was "
        "known before it, and asked what it would have flagged on the failures "
        "that came after."
    )

    cutoff = st.select_slider(
        "Knowledge cutoff", options=backtest.CUTOFF_SWEEP, value=backtest.DEFAULT_CUTOFF)

    try:
        run = cached_backtest(cutoff)
        sweep_frame = cached_backtest_sweep()
        cold = cached_cold_start()
    except data_layer.DatasetError as exc:
        st.warning("Knowledge base not ready: %s" % exc)
        return

    summary = run["summary"]
    detail = pd.DataFrame(run["detail"])

    st.caption(
        "%d records before the cutoff, %d after. %d incidents on active parts, "
        "%d unknowable (nothing had reported that mode yet, excluded from recall "
        "rather than counted as a miss)."
        % (run["train_records"], run["test_records"], summary["incidents"],
           summary["unknowable"]))

    b1, b2, b3, b4 = st.columns(4)
    with b1:
        st.metric("DFMEA on file caught", "%.0f%%" % (summary["dfmea_recall"] * 100))
    with b2:
        st.metric("Mechnari would have flagged", "%.0f%%" % (summary["mechnari_recall"] * 100),
                  delta="+%.0f pts" % ((summary["mechnari_recall"]
                                        - summary["dfmea_recall"]) * 100))
    with b3:
        st.metric("Failures newly caught", summary["newly_caught"])
    with b4:
        st.metric("Warranty claims behind them", summary["newly_caught_claims"])

    if not detail.empty and detail["newly_caught"].any():
        st.markdown("###### Failures the DFMEA on file would have missed")
        missed = detail[detail["newly_caught"]].sort_values(
            ["severity", "claims"], ascending=False)
        missed_display = missed[[
            "issue_id", "report_date", "part_id", "failure_mode", "severity",
            "claims"]].rename(columns={
            "issue_id": "8D Record", "report_date": "Reported", "part_id": "Part ID",
            "failure_mode": "Failure Mode That Occurred", "severity": "S",
            "claims": "Claims"})
        missed_display["Reported"] = pd.to_datetime(missed_display["Reported"]).dt.date.astype(str)
        st.dataframe(missed_display, use_container_width=True, hide_index=True)

    st.markdown("###### Does it hold at other cutoffs?")
    sweep_display = sweep_frame[[
        "cutoff", "incidents", "knowable", "dfmea_recall", "mechnari_recall",
        "newly_caught", "newly_caught_claims"]].rename(columns={
        "cutoff": "Cutoff", "incidents": "Incidents After", "knowable": "Knowable",
        "dfmea_recall": "DFMEA Caught", "mechnari_recall": "Mechnari Flagged",
        "newly_caught": "Newly Caught", "newly_caught_claims": "Claims"})
    st.dataframe(sweep_display, use_container_width=True, hide_index=True)
    st.caption(
        "Mechnari does not score 100%: some failures cross the taxonomy and those "
        "it cannot anticipate. A backtest that always scores perfectly is measuring "
        "its own construction, not the product."
    )

    st.markdown("###### Cold start: every part treated as never seen before")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Actual failure modes surfaced", "%.0f%%" % (cold["recall"] * 100),
                  help="%d of %d modes that really failed."
                       % (cold["modes_surfaced"], cold["failure_modes_evaluated"]))
    with c2:
        st.metric("Parts fully covered", cold["parts_fully_covered"])
    with c3:
        st.metric("Parts missed entirely", cold["parts_missed_entirely"])


# =====================================================================
# ROLE SWITCHER
# =====================================================================

tab_de, tab_qe, tab_co = st.tabs(
    ["🛠️ Design Engineer", "🔍 Quality Engineer", "📊 Company & Leadership"])

with tab_de:
    render_design_engineer_tab()

with tab_qe:
    render_quality_engineer_tab()

with tab_co:
    render_company_tab()
