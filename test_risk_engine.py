"""
Invariants for the deterministic risk engine.

Run with:  python test_risk_engine.py     (or: pytest test_risk_engine.py)

The engine produces the numbers an engineer signs their name against, so
these check the properties that make a score defensible: it round-trips
against the anchors it claims to use, it never falls below the evidence,
and it ranks a safety failure above a nuisance one.
"""

import itertools
import sys

import pandas as pd

import data_layer
import risk_engine as re


def test_occurrence_round_trips_against_its_own_anchors():
    for score, rate in re.OCCURRENCE_RATE_PER_1000.items():
        assert re.occurrence_from_rate(rate) == score, (
            "rate %s should map back to O=%s" % (rate, score))


def test_occurrence_is_monotonic_in_the_claim_rate():
    scores = [re.occurrence_from_rate(r) for r in
              [0, 0.001, 0.05, 0.2, 0.7, 1.5, 3, 12, 30, 60, 200]]
    assert scores == sorted(scores)
    assert re.occurrence_from_rate(0) == 1
    assert re.occurrence_from_rate(10_000) == 10


def test_occurrence_from_claims_handles_zero_fleet():
    assert re.occurrence_from_claims(5, 0) == 1
    assert re.occurrence_from_claims(0, 5000) == 1


def test_action_priority_is_defined_for_every_score_triple():
    for s, o, d in itertools.product(range(1, 11), repeat=3):
        assert re.action_priority(s, o, d) in ("H", "M", "L")


def test_ap_table_is_structurally_complete():
    severity_bands = [label for _, label in re.SEVERITY_BANDS if label != "S1"]
    occurrence_bands = [label for _, label in re.OCCURRENCE_BANDS]
    for key in itertools.product(severity_bands, occurrence_bands):
        assert key in re.AP_TABLE, "AP table missing %s" % (key,)
        row = re.AP_TABLE[key]
        assert len(row) == len(re.DETECTION_BANDS)
        assert set(row) <= {"H", "M", "L"}


def test_action_priority_never_decreases_as_risk_rises():
    """Raising any one score must never lower the priority."""
    rank = {"L": 1, "M": 2, "H": 3}
    for s, o, d in itertools.product(range(1, 11), repeat=3):
        here = rank[re.action_priority(s, o, d)]
        if s < 10:
            assert rank[re.action_priority(s + 1, o, d)] >= here, (s, o, d)
        if o < 10:
            assert rank[re.action_priority(s, o + 1, d)] >= here, (s, o, d)
        if d < 10:
            assert rank[re.action_priority(s, o, d + 1)] >= here, (s, o, d)


def test_verified_ap_cells_match_the_primary_source():
    """
    Pins every AP cell confirmed against the cited source (Pfeufer, VDA QMC,
    "Design FMEA Action Priority (AP) (Extract)", SMMT AQMS Nov 2018 - see
    the citation in risk_engine.py above AP_TABLE). If this fails, a table
    edit silently drifted from what is actually sourced, not just from an
    internal best-effort choice.
    """
    verified = [
        # (severity, occurrence, detection) -> AP, each an example inside
        # the cited band combination.
        ((10, 8, 5), "H"),   # S9-10,O6-10: whole row H regardless of D
        ((9, 6, 1), "H"),
        ((10, 5, 8), "H"),   # S9-10,O4-5,D7-10
        ((7, 5, 6), "H"),    # S5-8,O4-5,D5-6
        ((7, 5, 3), "M"),    # S5-8,O4-5,D1-4
        ((3, 5, 6), "M"),    # S2-4,O4-5,D5-6
        ((3, 5, 2), "L"),    # S2-4,O4-5,D1-4
        ((1, 10, 10), "L"),  # S1: any O, any D
    ]
    for (s, o, d), expected in verified:
        assert re.action_priority(s, o, d) == expected, (s, o, d, expected)


def test_severity_one_is_always_low():
    for o, d in itertools.product(range(1, 11), repeat=2):
        assert re.action_priority(1, o, d) == "L"


def test_ap_fixes_the_rpn_misranking_that_motivates_it():
    """
    The reason AIAG-VDA dropped RPN: a safety failure that is rare and hard
    to detect scores lower than a nuisance that is common. AP must not.
    """
    safety = (9, 2, 2)      # RPN 36
    nuisance = (4, 3, 4)    # RPN 48
    assert re.rpn(*safety) < re.rpn(*nuisance), "the RPN premise changed"

    rank = {"L": 1, "M": 2, "H": 3}
    assert rank[re.action_priority(*safety)] > rank[re.action_priority(*nuisance)]


def test_detection_floor_reflects_where_the_failure_escaped_to():
    assert re.detection_floor("FIELD_CUSTOMER") > re.detection_floor("DEALER_SERVICE")
    assert re.detection_floor("DEALER_SERVICE") > re.detection_floor("END_OF_LINE_TEST")
    assert re.detection_floor("END_OF_LINE_TEST") > re.detection_floor("VALIDATION_TEST")
    assert re.detection_floor("NO_RECORD") == 1


def test_scored_worksheet_covers_every_row_without_holes():
    df = re.scored_worksheet()
    worksheet = data_layer.dfmea_worksheet()
    assert len(df) == len(worksheet), "scoring dropped or duplicated rows"
    for column in ["severity_standard", "evidence_occurrence", "detection",
                   "ap_as_filed", "ap_evidence_based", "evidence_scope"]:
        assert df[column].notna().all(), "%s has holes" % column
    assert set(df["evidence_scope"]) <= {"OWN_PART", "TYPE_HISTORY"}


def test_severity_used_for_scoring_comes_from_the_effect_registry():
    effects = data_layer.failure_effects().set_index("effect_id")["standard_severity"]
    df = re.scored_worksheet()
    for _, row in df.iterrows():
        assert row["severity_standard"] == effects[row["effect_id"]]


def test_evidence_never_lowers_occurrence_below_the_workshop_when_absent():
    """With no warranty record, the workshop estimate stands unchanged."""
    df = re.scored_worksheet()
    no_evidence = df[~df["has_evidence"]]
    assert (no_evidence["evidence_occurrence"] == no_evidence["occurrence"]).all()


def test_occurrence_findings_are_evidence_backed_and_material():
    findings = re.occurrence_findings()
    assert len(findings), "no occurrence findings - the evidence join is broken"
    assert (findings["field_reports"] > 0).all()
    assert (findings["occurrence_delta"].abs() >= 1).all()
    issue_ids = set(data_layer.field_issues()["issue_id"])
    for cited in findings["evidence_ids"]:
        for issue_id in [i.strip() for i in cited.split(",")]:
            assert issue_id in issue_ids


def test_own_part_findings_exist_and_are_labelled():
    """
    A rate measured on sibling parts is a prior, not a measurement. The
    engine has to say which it is, and the credible findings - measured on
    the part itself - must not be empty.
    """
    findings = re.occurrence_findings()
    own = findings[findings["evidence_scope"] == "OWN_PART"]
    assert len(own), "no findings measured on the part itself"
    assert (own["occurrence_delta"] > 0).any(), "no understated occurrence to report"


def test_scoring_is_deterministic():
    pd.testing.assert_frame_equal(re.scored_worksheet(), re.scored_worksheet())


def test_unknown_part_raises():
    try:
        re.scored_worksheet("TR-NOT-A-PART")
    except KeyError:
        return
    raise AssertionError("unknown part_id should raise KeyError")


def test_headline_metrics_agree_with_the_frames():
    metrics = re.headline_metrics()
    df = re.scored_worksheet()
    assert metrics["worksheet_rows"] == len(df)
    assert metrics["ap_high_evidence_based"] == int((df["ap_evidence_based"] == "H").sum())
    assert metrics["ap_escalations"] == int(df["ap_changed"].sum())
    assert metrics["ap_table_verified"] is re.AP_TABLE_VERIFIED


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
