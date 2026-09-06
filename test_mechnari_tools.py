"""
Contract tests for the ADK function tools and the agent wiring.

Run with:  python test_mechnari_tools.py     (or: pytest test_mechnari_tools.py)

No API key and no network are needed: these check the tool contract and the
agent composition, not model output. The property that matters most is the
last one - that no agent holds a tool capable of writing a score.
"""

import inspect
import sys

from google.adk.tools import FunctionTool

import mechnari_tools as tools
from mechnari_agent import agent as mechnari_agent

SAMPLE_PART = "TR-FL-001"

TOOL_FUNCTIONS = [
    tools.list_parts,
    tools.get_part_profile,
    tools.find_unanalysed_failure_modes,
    tools.get_risk_scores,
    tools.get_occurrence_evidence,
    tools.check_severity_consistency,
    tools.analyse_new_part,
]


def test_every_tool_meets_the_adk_signature_contract():
    """ADK builds the tool schema from type hints and the docstring."""
    for fn in TOOL_FUNCTIONS:
        signature = inspect.signature(fn)
        assert fn.__doc__, "%s has no docstring for ADK to read" % fn.__name__
        assert signature.return_annotation is not inspect.Signature.empty, fn.__name__
        for name, param in signature.parameters.items():
            assert param.annotation is not inspect.Signature.empty, (
                "%s(%s) has no type hint" % (fn.__name__, name))
            assert param.kind not in (param.VAR_POSITIONAL, param.VAR_KEYWORD), (
                "%s uses *args/**kwargs, which ADK ignores" % fn.__name__)
        if signature.parameters:
            assert "Args:" in fn.__doc__, (
                "%s takes parameters but documents no Args section" % fn.__name__)


def test_adk_can_wrap_every_tool_and_build_its_declaration():
    """If ADK cannot generate a declaration, the agent silently loses the tool."""
    for fn in TOOL_FUNCTIONS:
        wrapped = FunctionTool(fn)
        assert wrapped.name == fn.__name__
        assert wrapped.description


def test_every_tool_returns_a_status_key():
    for fn in TOOL_FUNCTIONS:
        result = fn(SAMPLE_PART) if inspect.signature(fn).parameters else fn()
        assert isinstance(result, dict), fn.__name__
        assert result.get("status") in ("success", "error"), fn.__name__


def test_unknown_part_is_an_error_result_not_an_exception():
    """An agent must be able to read the failure, not crash on it."""
    for fn in [tools.get_part_profile, tools.find_unanalysed_failure_modes,
               tools.get_risk_scores]:
        result = fn("TR-NOT-A-PART")
        assert result["status"] == "error", fn.__name__
        assert "error_message" in result


def test_gap_tool_matches_the_engine_it_wraps():
    import gap_detection
    expected = gap_detection.detect_gaps(SAMPLE_PART)
    result = tools.find_unanalysed_failure_modes(SAMPLE_PART)
    assert result["status"] == "success"
    assert result["gap_count"] == len(expected)
    assert result["safety_gap_count"] == int((expected["standard_severity"] >= 9).sum())


def test_risk_tool_reports_whether_the_ap_table_is_verified():
    """A provisional Action Priority must never reach an agent unlabelled."""
    import risk_engine
    result = tools.get_risk_scores(SAMPLE_PART)
    assert result["action_priority_table_verified"] is risk_engine.AP_TABLE_VERIFIED


def test_findings_carry_their_warranty_evidence():
    result = tools.find_unanalysed_failure_modes(SAMPLE_PART)
    assert result["findings"], "no findings to check evidence on"
    for finding in result["findings"]:
        assert finding["warranty_evidence"]
        assert finding["learned_from"]


def test_occurrence_evidence_labels_its_scope():
    result = tools.get_occurrence_evidence(SAMPLE_PART)
    assert result["status"] == "success"
    for finding in result["findings"]:
        assert finding["evidence_scope"] in ("OWN_PART", "TYPE_HISTORY")


def test_root_agent_is_composed_for_adk_discovery():
    root = mechnari_agent.root_agent
    assert root.name and root.model
    assert [a.name for a in root.sub_agents] == [
        "gap_analyst", "risk_scorer", "mitigation_writer"]
    for sub in root.sub_agents:
        assert sub.description, "%s needs a description for delegation" % sub.name
        assert sub.instruction


def test_workflow_graph_starts_at_start_and_runs_the_review_in_order():
    edges = mechnari_agent.dfmea_review_workflow.edges
    assert len(edges) == 1
    chain = edges[0]
    assert chain[0] == "START"
    assert [node.name for node in chain[1:]] == [
        "gap_analyst", "risk_scorer", "mitigation_writer"]


def test_no_agent_can_write_a_score():
    """
    The audit-safety claim, enforced rather than asserted in a README: every
    tool any agent holds is a read-only lookup into the deterministic engines.
    """
    read_only = {fn.__name__ for fn in TOOL_FUNCTIONS}
    agents = [mechnari_agent.root_agent] + list(mechnari_agent.root_agent.sub_agents)
    for agent in agents:
        for tool in agent.tools:
            name = getattr(tool, "__name__", getattr(tool, "name", str(tool)))
            assert name in read_only, (
                "%s holds tool '%s', which is not a read-only engine lookup"
                % (agent.name, name))


def test_model_is_not_a_retired_snapshot():
    """The previous build pinned a retired model and failed silently into a fallback."""
    assert "1.5" not in mechnari_agent.MODEL


def test_copilot_reports_unavailable_instead_of_raising_without_a_key():
    import mechnari_agent.agent as module
    original = module._api_key_present
    module._api_key_present = lambda: False
    try:
        result = module.ask_copilot("Why is TR-FL-001 critical?")
        assert result["status"] == "unavailable"
        assert result["reason"]
    finally:
        module._api_key_present = original


def _main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS  %s" % name)
        except AssertionError as exc:
            failures += 1
            print("FAIL  %s\n      %s" % (name, exc))
        except Exception as exc:  # noqa: BLE001 - report, do not mask
            failures += 1
            print("ERROR %s\n      %s: %s" % (name, type(exc).__name__, exc))
    print("\n%d passed, %d failed" % (len(tests) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
