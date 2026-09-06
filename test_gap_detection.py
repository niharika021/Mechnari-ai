"""
Invariants for the knowledge base and the gap detection agent.

Run with:  python test_gap_detection.py     (or: pytest test_gap_detection.py)

These are the properties an auditor would ask about. If any of them break,
a finding on screen can no longer be trusted, so they are worth more than
line coverage.
"""

import sys

import pandas as pd

import data_layer
import gap_detection as gd
import taxonomy


def test_every_part_is_typed_and_families_resolve():
    parts = data_layer.parts()
    assert len(parts) == 50
    assert parts["part_type_id"].notna().all()
    assert parts["family_id"].notna().all(), "a part type with no family breaks inheritance"
    assert set(parts["part_type_id"]) <= set(taxonomy.PART_TYPES)


def test_gaps_partition_applicable_modes():
    """analysed + gaps == applicable, exactly. Nothing invented, nothing lost."""
    applicable = data_layer.applicable_modes()
    analysed = data_layer.analysed_modes()
    gaps = gd.detect_gaps()

    applicable_pairs = set(zip(applicable["part_id"], applicable["mode_id"]))
    gap_pairs = set(zip(gaps["part_id"], gaps["mode_id"]))
    analysed_pairs = {(pid, mid) for pid, modes in analysed.items() for mid in modes}

    assert gap_pairs <= applicable_pairs, "a gap was reported for an inapplicable mode"
    assert not (gap_pairs & analysed_pairs), "a mode already analysed was reported as a gap"
    assert gap_pairs | analysed_pairs == applicable_pairs
    assert len(applicable_pairs) == len(applicable), "duplicate (part, mode) pair"


def test_no_mode_travels_outside_its_scope():
    """A type-scoped lesson must not reach a part of another type."""
    applicable = data_layer.applicable_modes()
    for _, row in applicable.iterrows():
        if row["scope_level"] == "TYPE":
            assert row["scope_id"] == row["part_type_id"], row["mode_id"]
        else:
            assert row["scope_id"] == row["family_id"], row["mode_id"]


def test_severity_is_never_invented():
    """Every severity on a finding traces to the effect registry."""
    effects = data_layer.failure_effects().set_index("effect_id")["standard_severity"]
    gaps = gd.detect_gaps()
    for _, row in gaps.iterrows():
        assert row["standard_severity"] == effects[row["effect_id"]]
    assert gaps["standard_severity"].between(1, 10).all()


def test_every_evidenced_finding_cites_real_records():
    """A cited 8D number has to exist, or the audit trail is fiction."""
    issue_ids = set(data_layer.field_issues()["issue_id"])
    gaps = gd.detect_gaps()
    evidenced = gaps[gaps["reports"] > 0]
    assert len(evidenced), "no finding carries evidence - the evidence join is broken"
    for _, row in evidenced.iterrows():
        cited = [i.strip() for i in row["evidence_ids"].split(",")]
        assert cited, row["mode_id"]
        for issue_id in cited:
            assert issue_id in issue_ids, "%s cites unknown record %s" % (
                row["mode_id"], issue_id)


def test_priority_band_is_a_pure_function_of_severity():
    assert gd.priority_band(10) == gd.priority_band(9)
    assert gd.priority_band(9) != gd.priority_band(8)
    assert gd.priority_band(8) == gd.priority_band(7)
    assert gd.priority_band(6) != gd.priority_band(7)
    assert gd.priority_band(1) == "P4 - Nuisance"


def test_detection_is_deterministic():
    """Same knowledge base in, byte-identical findings out - twice."""
    first, second = gd.detect_gaps(), gd.detect_gaps()
    pd.testing.assert_frame_equal(first, second)


def test_single_part_query_matches_the_bom_wide_result():
    everything = gd.detect_gaps()
    part_id = everything["part_id"].iloc[0]
    one = gd.detect_gaps(part_id).reset_index(drop=True)
    expected = everything[everything["part_id"] == part_id].reset_index(drop=True)
    pd.testing.assert_frame_equal(one, expected)


def test_unknown_part_raises():
    try:
        gd.detect_gaps("TR-NOT-A-PART")
    except KeyError:
        return
    raise AssertionError("unknown part_id should raise KeyError")


def test_severity_consistency_finds_the_seeded_drift():
    findings = gd.severity_consistency_findings()
    assert len(findings) == 6, "expected the 6 seeded drift rows, got %d" % len(findings)
    assert (findings["severity_delta"] != 0).all()
    # Every drift row must name both scores so the engineer can act on it.
    assert findings["standard_severity"].notna().all()
    assert findings["severity"].notna().all()


def test_coverage_is_incomplete_everywhere():
    """
    A baseline DFMEA with nothing missing is not a realistic demo, and it
    would mean the gap agent has nothing to prove.
    """
    coverage = data_layer.coverage_summary()
    assert (coverage["modes_not_analysed"] > 0).all()
    assert coverage["coverage_pct"].between(0, 100).all()


def test_headline_metrics_agree_with_the_frames():
    metrics = gd.headline_metrics()
    gaps = gd.detect_gaps()
    assert metrics["total_gaps"] == len(gaps)
    assert metrics["safety_gaps"] == int((gaps["standard_severity"] >= 9).sum())
    assert metrics["parts_with_gaps"] == gaps["part_id"].nunique()


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
