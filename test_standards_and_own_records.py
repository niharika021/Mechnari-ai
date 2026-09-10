"""
Mechnari.ai - the standards floor and engineer-supplied records
===============================================================
Run with:  python test_standards_and_own_records.py   (or pytest)

Two additions covered here, and one guarantee that spans both: neither
of them may introduce a number the engines did not produce. An engineer
supplying a failure record contributes an observation; Severity still
comes from the effect registry, Occurrence still comes from
risk_engine's scale, Detection still comes from the escape-stage floor.
A standards row is the same, with Occurrence at the floor because there
is no measured rate to derive one from.

The other thing asserted here is that the standards modes stay OUT of
the knowledge base. They are generic practice, not this company's
history, so calling an unanalysed one a "gap" would be a false claim -
and putting them in failure_mode_catalog would silently move every
headline figure in the product.
"""

import sys

import data_layer
import dfmea_sheet
import gap_detection
import own_records
import risk_engine
import standards

# A part the corpus genuinely knows about, and one it does not.
IN_DOMAIN = {
    "part_number": "T-1",
    "description": "Diesel return hose",
    "function": "Carry unburnt fuel back to the tank",
    "material": "Rubber hose with braid",
}
OUT_OF_DOMAIN = {
    "part_number": "T-2",
    "description": "Operator seat cushion",
    "function": "Support the operator",
    "material": "Polyurethane foam",
}


def _levels(result):
    seen = {}
    for row in result["rows"]:
        seen[row["scope_level"]] = seen.get(row["scope_level"], 0) + 1
    return seen


# =====================================================================
# THE STANDARDS FLOOR
# =====================================================================

def test_standards_do_not_appear_for_a_part_the_corpus_knows():
    """Otherwise every well-evidenced sheet gains a dozen generic rows."""
    result = dfmea_sheet.build_for_item(dict(IN_DOMAIN))
    assert result["standards_rows"] == 0, _levels(result)
    assert "STANDARD" not in _levels(result)


def test_standards_appear_for_a_part_the_corpus_does_not_know():
    result = dfmea_sheet.build_for_item(dict(OUT_OF_DOMAIN))
    assert result["standards_rows"] > 0, _levels(result)
    assert _levels(result).get("STANDARD", 0) > 0


def test_the_floor_is_keyed_on_similarity_not_on_the_confident_flag():
    """`confident` measures whether neighbours agree on a type, not
    whether any of them resemble the part - it fires on the wrong parts
    in both directions, which is why the threshold is a similarity."""
    import retrieval

    query = retrieval.describe(
        OUT_OF_DOMAIN["description"], OUT_OF_DOMAIN["function"],
        OUT_OF_DOMAIN["material"])
    inference = retrieval.infer_part_type(query)
    assert inference["best_similarity"] < standards.STANDARDS_SIMILARITY_FLOOR


def test_standard_rows_take_severity_from_the_registry():
    """A standards row cannot introduce a severity the organisation has
    not already standardised for that effect."""
    effects = data_layer.failure_effects()
    standard_by_effect = dict(
        zip(effects["effect_id"], effects["standard_severity"]))
    frame = standards.candidate_standard_modes("hydraulic hose assembly line")
    assert not frame.empty
    for _, row in frame.iterrows():
        assert row["effect_id"] in standard_by_effect
        assert int(row["severity"]) == int(standard_by_effect[row["effect_id"]])


def test_standard_rows_sit_at_the_occurrence_floor_and_say_so():
    """No measured rate exists, so Occurrence must not look measured."""
    frame = standards.candidate_standard_modes("fuel hose")
    for _, row in frame.iterrows():
        assert int(row["occurrence"]) == risk_engine.occurrence_from_rate(0)
        assert int(row["field_claims"]) == 0
        assert "no field record" in row["evidence_ids"]


def test_standards_never_enter_the_knowledge_base():
    """The load-bearing separation. A generic mode is not institutional
    memory, so an unanalysed one is not a gap - and if these were in
    failure_mode_catalog, every gap and coverage figure would move."""
    catalog_ids = set(data_layer.failure_mode_catalog()["mode_id"])
    standard_ids = {m["mode_id"] for m in standards.STANDARD_MODES}
    assert not (catalog_ids & standard_ids), catalog_ids & standard_ids

    gap_ids = set(gap_detection.detect_gaps()["mode_id"])
    assert not (gap_ids & standard_ids), gap_ids & standard_ids


def test_headline_metrics_are_untouched_by_the_standards_tier():
    """The figures the README quotes must not move because this shipped."""
    metrics = gap_detection.headline_metrics()
    assert metrics["parts_analysed"] == 50, metrics
    assert metrics["total_gaps"] == 127, metrics
    assert metrics["safety_gaps"] == 15, metrics


def test_the_keyword_gate_keeps_categories_apart():
    """The gate exists so a bracket is not offered refrigerant release."""
    fluid = standards.categories_for("hydraulic hose assembly")
    electrical = standards.categories_for("wiring harness connector")
    assert "fluid" in fluid and "electrical" not in fluid
    assert "electrical" in electrical and "fluid" not in electrical
    # Universal applies to everything, including text matching nothing.
    assert standards.categories_for("zzz nothing here") == ["universal"]


def test_standards_are_flagged_as_unreviewed():
    """Same convention as risk_engine.AP_TABLE_VERIFIED: the platform
    says so rather than presenting authored content as authoritative."""
    assert standards.STANDARDS_REVIEWED is False
    result = dfmea_sheet.build_for_item(dict(OUT_OF_DOMAIN))
    assert result["standards_reviewed"] is False


# =====================================================================
# ENGINEER-SUPPLIED RECORDS
# =====================================================================

def test_a_supplied_record_becomes_a_row():
    result = dfmea_sheet.build_for_item(dict(
        IN_DOMAIN,
        own_records=[{
            "failure_mode": "Collar cracks after cold-soak cycling",
            "effect_id": "EF-01",
            "detection_stage": "FIELD_CUSTOMER",
        }],
    ))
    assert result["engineer_rows"] == 1
    engineer = [r for r in result["rows"] if r["scope_level"] == "ENGINEER"]
    assert len(engineer) == 1
    assert engineer[0]["failure_mode"].startswith("Collar cracks")


def test_severity_comes_from_the_registry_not_the_engineer():
    """There is deliberately no severity field to supply."""
    effects = data_layer.failure_effects()
    expected = int(
        effects[effects["effect_id"] == "EF-04"]["standard_severity"].iloc[0])
    frame = own_records.build_rows([{
        "failure_mode": "Anything at all",
        "effect_id": "EF-04",
        "detection_stage": "VALIDATION_TEST",
    }])
    assert int(frame.iloc[0]["severity"]) == expected


def test_occurrence_is_derived_from_the_rate_by_the_same_engine():
    claims, units = 34, 1200
    frame = own_records.build_rows([{
        "failure_mode": "Cracks in the cold",
        "effect_id": "EF-01",
        "detection_stage": "FIELD_CUSTOMER",
        "claim_count": claims,
        "units_in_service": units,
    }])
    assert int(frame.iloc[0]["occurrence"]) == risk_engine.occurrence_from_claims(
        claims, units)


def test_without_a_rate_occurrence_stays_at_the_floor_and_says_so():
    """A guess must not end up looking identical to a measurement."""
    frame = own_records.build_rows([{
        "failure_mode": "Something seen once on a prototype",
        "effect_id": "EF-02",
        "detection_stage": "DEALER_SERVICE",
    }])
    row = frame.iloc[0]
    assert int(row["occurrence"]) == risk_engine.occurrence_from_rate(0)
    assert "no rate given" in row["evidence_ids"]


def test_detection_is_the_escape_stage_floor():
    """A failure that reached a customer cannot be scored well-detected."""
    for stage, _ in own_records.DETECTION_STAGES:
        frame = own_records.build_rows([{
            "failure_mode": "m", "effect_id": "EF-02", "detection_stage": stage,
        }])
        assert int(frame.iloc[0]["detection"]) == risk_engine.detection_floor(stage)


def test_an_effect_outside_the_registry_is_refused():
    """Accepting it would let an engineer introduce a severity by
    inventing an effect - the one thing the registry exists to stop."""
    try:
        own_records.build_rows([{
            "failure_mode": "m", "effect_id": "EF-DOES-NOT-EXIST",
            "detection_stage": "DEALER_SERVICE",
        }])
    except own_records.OwnRecordError:
        return
    raise AssertionError("expected OwnRecordError for an unregistered effect")


def test_an_unknown_detection_stage_is_refused():
    try:
        own_records.build_rows([{
            "failure_mode": "m", "effect_id": "EF-02",
            "detection_stage": "SOMEONE_MENTIONED_IT",
        }])
    except own_records.OwnRecordError:
        return
    raise AssertionError("expected OwnRecordError for an unknown stage")


def test_a_record_with_no_failure_mode_is_refused():
    try:
        own_records.build_rows([{
            "failure_mode": "   ", "effect_id": "EF-02",
            "detection_stage": "DEALER_SERVICE",
        }])
    except own_records.OwnRecordError:
        return
    raise AssertionError("expected OwnRecordError for a blank failure mode")


def test_supplied_rows_are_marked_as_the_engineers_own():
    """Quality has to be able to tell a colleague's recollection from
    the warranty record. Both are legitimate; conflating them is not."""
    frame = own_records.build_rows([{
        "failure_mode": "m", "effect_id": "EF-02",
        "detection_stage": "DEALER_SERVICE",
    }])
    row = frame.iloc[0]
    assert row["scope_level"] == "ENGINEER"
    assert row["origin"] == "ENGINEER_SUPPLIED"
    assert "engineer" in row["learned_from"].lower()


def test_supplied_records_survive_when_the_part_matches_nothing():
    """The case where a colleague's own observation is the only evidence
    there is - it must not be dropped along with the empty proposal."""
    result = dfmea_sheet.build_for_item(dict(
        OUT_OF_DOMAIN,
        own_records=[{
            "failure_mode": "Foam compresses permanently after a season",
            "effect_id": "EF-15",
            "detection_stage": "DEALER_SERVICE",
        }],
    ))
    engineer = [r for r in result["rows"] if r["scope_level"] == "ENGINEER"]
    assert len(engineer) == 1, _levels(result)


def test_action_priority_on_supplied_rows_uses_the_same_ap_table():
    frame = own_records.build_rows([{
        "failure_mode": "m", "effect_id": "EF-01",
        "detection_stage": "FIELD_CUSTOMER",
        "claim_count": 34, "units_in_service": 1200,
    }])
    row = frame.iloc[0]
    assert row["action_priority"] == risk_engine.action_priority(
        int(row["severity"]), int(row["occurrence"]), int(row["detection"]))


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
