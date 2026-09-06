"""
Invariants for the semantic retrieval agent.

Run with:  python test_retrieval.py     (or: pytest test_retrieval.py)

Two kinds of check here. Most are contract tests. The last group are
regression guards on measured retrieval quality: if a change to the corpus,
the weighting or the taxonomy quietly makes matching worse, these fail
rather than letting a weaker demo ship unnoticed.
"""

import sys

import pandas as pd

import data_layer
import retrieval

# Floors sit a little below the measured values so normal jitter does not
# fail the suite, but a real regression does.
MIN_MODE_RECALL = 0.70
MIN_TYPE_RECALL_AT_K = 0.65
MIN_FAMILY_ACCURACY = 0.60


def test_corpus_never_contains_the_label():
    """
    The whole evaluation is meaningless if the type name is a feature.
    """
    parts = retrieval._corpus()
    for _, row in parts.iterrows():
        text = row["_text"]
        assert row["part_type_name"].lower() not in text, row["part_id"]
        assert row["family_name"].lower() not in text, row["part_id"]
        assert row["system_package"].lower() not in text, row["part_id"]


def test_head_noun_is_the_last_one():
    """English compound nouns are head-final: a line clamp is a clamp."""
    assert retrieval._head_nouns("Constant-Tension Fuel Return Line Clamp") == ["clamp"]
    assert retrieval._head_nouns("High-Pressure Fuel Common Rail Feed Hose") == ["hose"]
    assert retrieval._head_nouns("Fuel Filter Cast Structural Bracket") == ["bracket"]
    assert retrieval._head_nouns("Something With No Component Noun") == []


def test_a_part_described_by_its_own_text_retrieves_itself_first():
    parts = data_layer.parts()
    for _, row in parts.head(10).iterrows():
        query = retrieval.describe(
            row["item_reference"], row["elementary_function"], row["material_type"])
        hits = retrieval.find_similar_parts(query, top_k=1)
        assert not hits.empty, row["part_id"]
        assert hits.iloc[0]["part_id"] == row["part_id"], row["part_id"]


def test_similarity_is_ordered_and_bounded():
    hits = retrieval.find_similar_parts(
        retrieval.describe("fuel hose", "carry diesel", "nitrile rubber"), top_k=8)
    assert not hits.empty
    scores = hits["similarity"].tolist()
    assert scores == sorted(scores, reverse=True)
    assert all(0 < s <= 1.0001 for s in scores)


def test_exclude_part_id_removes_that_part():
    parts = data_layer.parts()
    row = parts.iloc[0]
    query = retrieval.describe(
        row["item_reference"], row["elementary_function"], row["material_type"])
    hits = retrieval.find_similar_parts(query, top_k=5, exclude_part_id=row["part_id"])
    assert row["part_id"] not in set(hits["part_id"])


def test_empty_description_returns_nothing_rather_than_everything():
    for query in ["", "   "]:
        assert retrieval.find_similar_parts(query).empty
        inference = retrieval.infer_part_type(query)
        assert inference["part_type_id"] is None
        assert inference["confident"] is False


def test_nonsense_description_is_flagged_not_answered():
    inference = retrieval.infer_part_type("xyzzy qwertyuiop zzzz")
    assert inference["confident"] is False
    assert inference["reason"]


def test_cold_start_proposal_is_grounded_and_traceable():
    query = retrieval.describe(
        "New EPDM Fuel Return Line",
        "Return unburnt diesel from the injector rail to the tank",
        "EPDM rubber with textile braid")
    proposal = retrieval.propose_dfmea(query)

    assert proposal["status"] == "success"
    assert not proposal["neighbours"].empty
    assert not proposal["candidates"].empty

    issue_ids = set(data_layer.field_issues()["issue_id"])
    for _, row in proposal["candidates"].iterrows():
        assert row["learned_from"], "a proposed row with no provenance"
        assert 1 <= row["severity"] <= 10
        assert row["action_priority"] in ("H", "M", "L")
        if row["evidence_ids"] != "no field record":
            for issue_id in [i.strip() for i in row["evidence_ids"].split(",")]:
                assert issue_id in issue_ids


def test_cold_start_finds_the_fuel_hose_lessons():
    """
    The demo case: a flexible fuel line that does not exist yet should reach
    the fuel hose history, including the crimped-joint leak from a retired
    program that no current part would surface.
    """
    query = retrieval.describe(
        "New EPDM Fuel Return Line",
        "Return unburnt diesel from the injector rail to the tank",
        "EPDM rubber with textile braid")
    proposal = retrieval.propose_dfmea(query)
    assert proposal["part_type_name"] == "Fuel Hose / Flexible Fuel Line"

    modes = set(proposal["candidates"]["failure_mode"])
    assert "Fuel leakage at crimped ferrule joint" in modes
    assert proposal["safety_candidates"] > 0


def test_severity_on_a_proposal_comes_from_the_effect_registry():
    effects = data_layer.failure_effects().set_index("effect_id")["standard_severity"]
    proposal = retrieval.propose_dfmea(retrieval.describe("hydraulic hose", "", "rubber"))
    for _, row in proposal["candidates"].iterrows():
        assert row["severity"] == effects[row["effect_id"]]


def test_confirming_a_type_narrows_the_proposal():
    query = retrieval.describe("New EPDM Fuel Return Line", "", "EPDM rubber")
    unconfirmed = retrieval.propose_dfmea(query)
    confirmed = retrieval.propose_dfmea(query, part_type_id="PT-HOSE-FUEL")

    assert confirmed["confirmed"] is True
    assert unconfirmed["confirmed"] is False
    assert set(confirmed["scopes_used"]) == {"PT-HOSE-FUEL", "FAM-FLEX-ROUTING"}
    assert len(confirmed["candidates"]) <= len(unconfirmed["candidates"])


def test_unknown_confirmed_type_raises():
    try:
        retrieval.propose_dfmea(retrieval.describe("hose", "", ""),
                               part_type_id="PT-NOT-A-TYPE")
    except KeyError:
        return
    raise AssertionError("an unknown part_type_id should raise KeyError")


def test_retrieval_is_deterministic():
    query = retrieval.describe("steel mounting bracket", "support a pump", "steel")
    pd.testing.assert_frame_equal(
        retrieval.find_similar_parts(query), retrieval.find_similar_parts(query))


# --- measured quality, guarded against regression -----------------------

def test_mode_recall_holds():
    """The product metric: how much of what truly applies the proposal surfaces."""
    metrics = retrieval.evaluate_retrieval()
    assert metrics["mode_recall"] >= MIN_MODE_RECALL, (
        "mode recall fell to %.0f%%" % (metrics["mode_recall"] * 100))


def test_true_type_is_usually_among_the_neighbours():
    metrics = retrieval.evaluate_retrieval()
    assert metrics["type_recall_at_k"] >= MIN_TYPE_RECALL_AT_K, (
        "type recall@k fell to %.0f%%" % (metrics["type_recall_at_k"] * 100))


def test_family_inference_holds():
    metrics = retrieval.evaluate_retrieval()
    assert metrics["family_top1_accuracy"] >= MIN_FAMILY_ACCURACY, (
        "family accuracy fell to %.0f%%" % (metrics["family_top1_accuracy"] * 100))


def test_proposal_stays_reviewable():
    """
    Recall is easy if you propose everything. A proposal an engineer will not
    read is worth nothing, so the shortlist has to stay well short of the
    whole catalogue.
    """
    metrics = retrieval.evaluate_retrieval()
    assert metrics["mean_modes_proposed"] < metrics["catalog_size"] * 0.45, (
        "proposals average %.1f of %d modes - too many to review"
        % (metrics["mean_modes_proposed"], metrics["catalog_size"]))


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
