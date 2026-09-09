"""
Smoke tests for the HTTP API.

Run with:  python test_api.py     (or: pytest test_api.py)

api.py is deliberately thin - every route is a call into a module that has
its own suite. So these tests do not re-check the engines' arithmetic; they
check the wiring the other suites cannot see: that each route is reachable,
that its JSON is actually serialisable (pandas NaN is not valid JSON and has
to be nulled out), that the shapes the frontend indexes into are present, and
that unknown ids produce 404 rather than a 500.

The queue routes write to disk, so this suite redirects queue_store.STORE_PATH
to a scratch file before touching them - the real review queue is never read
or modified.
"""

import os
import sys
import tempfile

from fastapi.testclient import TestClient

import api
import queue_store

client = TestClient(api.app)

SAMPLE_PART = {
    "part_name": "New EPDM Fuel Return Line",
    "function": "Return unburnt diesel from the injector rail to the tank",
    "material": "EPDM rubber with textile braid",
}


def _use_scratch_store():
    handle, path = tempfile.mkstemp(suffix=".json")
    os.close(handle)
    os.remove(path)  # submit_draft must create it fresh
    queue_store.STORE_PATH = path
    return path


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}


def test_parts_are_json_safe_and_filterable():
    everything = client.get("/api/parts")
    assert everything.status_code == 200, everything.text
    parts = everything.json()  # would raise if NaN leaked into the body
    assert len(parts) > 0
    assert {"part_id", "item_reference", "system_package"} <= set(parts[0])

    package = parts[0]["system_package"]
    filtered = client.get("/api/parts", params={"system_package": package}).json()
    assert 0 < len(filtered) < len(parts)
    assert all(p["system_package"] == package for p in filtered)


def test_system_packages_match_the_parts_table():
    packages = client.get("/api/system-packages").json()
    from_parts = {p["system_package"] for p in client.get("/api/parts").json()}
    assert set(packages) == from_parts
    assert packages == sorted(packages)


def test_part_types_carry_their_family():
    types = client.get("/api/part-types").json()
    assert len(types) > 0
    assert {"part_type_id", "part_type_name", "family_name"} <= set(types[0])


def test_propose_dfmea_returns_scored_rows_with_levers():
    response = client.post("/api/propose-dfmea", json=SAMPLE_PART)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success", body
    assert body["part_type_id"]
    assert len(body["neighbours"]) > 0
    assert len(body["candidates"]) > 0

    for row in body["candidates"]:
        assert row["action_priority"] in {"H", "M", "L"}
        # The levers ride along with the row rather than being fetched per
        # row by the client; that regressed once into an infinite request
        # loop, so assert the field is actually there and consistent.
        assert "levers" in row, row["mode_id"]
        for lever in row["levers"]:
            assert lever["factor"] in {"occurrence", "detection"}
            assert lever["to"] < lever["from"]
            assert lever["resulting_ap"] != row["action_priority"]


def test_propose_dfmea_rejects_an_empty_description():
    response = client.post(
        "/api/propose-dfmea",
        json={"part_name": "", "function": "", "material": ""},
    )
    assert response.status_code == 400, response.text


def test_propose_dfmea_rejects_an_unknown_part_type():
    response = client.post(
        "/api/propose-dfmea", json=dict(SAMPLE_PART, part_type_id="PT-NOT-A-TYPE")
    )
    assert response.status_code == 400, response.text


def test_ap_levers_agrees_with_the_engine():
    import risk_engine

    body = client.post(
        "/api/ap-levers", json={"severity": 10, "occurrence": 6, "detection": 5}
    ).json()
    assert body == risk_engine.find_ap_levers(10, 6, 5)


def test_queue_round_trip():
    _use_scratch_store()
    proposal = client.post("/api/propose-dfmea", json=SAMPLE_PART).json()
    rows = proposal["candidates"]

    submitted = client.post(
        "/api/queue/submit",
        json={
            "part_name": SAMPLE_PART["part_name"],
            "function": SAMPLE_PART["function"],
            "material": SAMPLE_PART["material"],
            "system_package": "Fuel Routings",
            "part_type_name": proposal["part_type_name"],
            "accepted_rows": rows[:-1],
            "declined_rows": rows[-1:],
        },
    )
    assert submitted.status_code == 200, submitted.text
    draft_id = submitted.json()["draft_id"]

    listed = client.get("/api/queue").json()
    assert [d["draft_id"] for d in listed] == [draft_id]

    draft = client.get("/api/queue/%s" % draft_id).json()
    assert draft["status"] == "needs_review"
    assert len(draft["accepted_rows"]) == len(rows) - 1
    assert len(draft["declined_rows"]) == 1

    approved = client.post(
        "/api/queue/%s/status" % draft_id,
        json={"status": "approved", "comments": "Checked against the registry."},
    )
    assert approved.status_code == 200, approved.text
    after = client.get("/api/queue/%s" % draft_id).json()
    assert after["status"] == "approved"
    assert after["review_comments"] == "Checked against the registry."


def test_unknown_draft_is_404_not_500():
    _use_scratch_store()
    assert client.get("/api/queue/DR-NOPE").status_code == 404
    assert (
        client.post("/api/queue/DR-NOPE/status", json={"status": "approved"}).status_code
        == 404
    )


def test_rejected_draft_status_is_400():
    _use_scratch_store()
    draft_id = client.post(
        "/api/queue/submit",
        json={
            "part_name": "X", "function": "f", "material": "m",
            "system_package": "Fuel Routings", "part_type_name": "T",
            "accepted_rows": [], "declined_rows": [],
        },
    ).json()["draft_id"]
    response = client.post(
        "/api/queue/%s/status" % draft_id, json={"status": "not_a_status"}
    )
    assert response.status_code == 400, response.text


def test_audit_reports_every_section_for_a_real_part():
    part_id = client.get("/api/parts").json()[0]["part_id"]
    body = client.get("/api/audit/%s" % part_id).json()
    assert body["part"]["part_id"] == part_id
    for section in ("severity_findings", "occurrence_findings", "gaps"):
        assert isinstance(body[section], list)
        assert all(row["part_id"] == part_id for row in body[section])


def test_audit_of_an_unknown_part_is_404_not_500():
    assert client.get("/api/audit/TR-NOT-A-PART").status_code == 404


def test_dfmea_sheet_fills_the_form_sheet_columns():
    body = client.post("/api/dfmea-sheet", json={"items": [{
        "part_number": "EXAMPLE-0001",
        "description": SAMPLE_PART["part_name"],
        "function": SAMPLE_PART["function"],
        "material": SAMPLE_PART["material"],
        "system_package": "Fuel Routings",
    }]}).json()
    assert body["total_rows"] > 0
    block = body["items"][0]
    assert block["status"] == "success"
    assert block["part_number"] == "EXAMPLE-0001"

    for row in block["rows"]:
        # The columns an engineer reads off the sheet.
        for column in ("failure_mode", "potential_effect", "potential_cause",
                       "design_control_prevention", "detection_control",
                       "recommended_action", "drawing_spec"):
            assert row[column], (column, row["mode_id"])
        assert row["pes"] in {"Y", "N"}
        assert row["action_priority"] in {"H", "M", "L"}
        assert row["rpn_legacy"] == row["severity"] * row["occurrence"] * row["detection"]


def test_dfmea_sheet_leaves_commitment_columns_empty():
    """Responsibility, target date and action taken are commitments. The
    tool must not invent an owner or a date nobody agreed to."""
    body = client.post("/api/dfmea-sheet", json={"items": [{
        "description": SAMPLE_PART["part_name"],
        "function": SAMPLE_PART["function"],
    }]}).json()
    for row in body["items"][0]["rows"]:
        assert row["responsibility"] == ""
        assert row["target_completion_date"] == ""
        assert row["action_taken"] == ""
        assert row["completed_date"] == ""


def test_dfmea_sheet_reassessment_never_lowers_severity():
    """Severity is fixed by the failure effect. An action can cut how often
    a failure happens or how well it is caught, but if the effect still
    reaches the operator the severity is unchanged."""
    body = client.post("/api/dfmea-sheet", json={"items": [{
        "description": SAMPLE_PART["part_name"],
        "function": SAMPLE_PART["function"],
        "material": SAMPLE_PART["material"],
    }]}).json()
    rows = body["items"][0]["rows"]
    assert len(rows) > 0
    for row in rows:
        assert row["reassessed_severity"] == row["severity"]
        assert row["reassessed_occurrence"] <= row["occurrence"]
        assert row["reassessed_detection"] <= row["detection"]
        assert row["reassessment_basis"]


def test_dfmea_sheet_handles_a_package_of_parts():
    body = client.post("/api/dfmea-sheet", json={"items": [
        {"part_number": "A1", "description": "EPDM Fuel Return Line",
         "function": "Return diesel to the tank", "material": "EPDM rubber"},
        {"part_number": "B2", "description": "Fuel Filter Mounting Bracket",
         "function": "Support the filter head against vibration",
         "material": "Cast aluminium"},
    ]}).json()
    assert len(body["items"]) == 2
    assert [b["part_number"] for b in body["items"]] == ["A1", "B2"]
    # Different kinds of part must not be handed the same failure modes.
    types = {b["part_type_id"] for b in body["items"]}
    assert len(types) == 2, types
    assert body["total_rows"] == sum(len(b["rows"]) for b in body["items"])


def test_dfmea_sheet_rejects_empty_and_oversized_requests():
    assert client.post("/api/dfmea-sheet", json={"items": []}).status_code == 400
    too_many = [{"description": "x", "function": "y"} for _ in range(26)]
    assert client.post("/api/dfmea-sheet", json={"items": too_many}).status_code == 400


def test_dfmea_sheet_reports_an_undescribed_item_without_failing_the_batch():
    body = client.post("/api/dfmea-sheet", json={"items": [
        {"part_number": "GOOD", "description": SAMPLE_PART["part_name"],
         "function": SAMPLE_PART["function"]},
        {"part_number": "EMPTY"},
    ]}).json()
    statuses = {b["part_number"]: b["status"] for b in body["items"]}
    assert statuses["GOOD"] == "success"
    assert statuses["EMPTY"] == "insufficient_input"


def test_existing_dfmea_shows_filed_and_evidence_readings_side_by_side():
    part_id = client.get("/api/parts").json()[0]["part_id"]
    body = client.get("/api/dfmea-sheet/%s" % part_id).json()
    assert body["part_id"] == part_id
    assert body["rows_applicable"] >= body["rows_analysed"]
    assert 0 <= body["coverage_pct"] <= 100
    assert len(body["filed_rows"]) == body["rows_analysed"]

    for row in body["filed_rows"]:
        # Both readings are kept: the filed value is what somebody signed,
        # the evidence value is what the claims show. Replacing the first
        # with the second would destroy the finding.
        for column in ("severity", "occurrence", "detection", "action_priority",
                       "evidence_severity", "evidence_occurrence",
                       "evidence_detection", "evidence_action_priority"):
            assert row[column] is not None, column
        differs = (
            row["evidence_severity"] != row["severity"]
            or row["evidence_occurrence"] != row["occurrence"]
            or row["evidence_detection"] != row["detection"]
            or row["evidence_action_priority"] != row["action_priority"]
        )
        # A flagged row must explain itself, and an unflagged one must not
        # carry a phantom note.
        assert row["disagrees"] == bool(row["disagreement_notes"])
        if row["disagrees"]:
            assert differs, row["mode_id"]


def test_existing_dfmea_missing_rows_are_the_gaps_for_that_part():
    import gap_detection

    part_id = client.get("/api/parts").json()[0]["part_id"]
    body = client.get("/api/dfmea-sheet/%s" % part_id).json()
    expected = gap_detection.detect_gaps(part_id)
    assert len(body["missing_rows"]) == len(expected)
    assert all(row["evidence_ids"] for row in body["missing_rows"])


def test_existing_dfmea_of_an_unknown_part_is_404():
    assert client.get("/api/dfmea-sheet/TR-NOT-A-PART").status_code == 404


def test_rescore_keeps_the_ap_table_in_the_engine():
    """The review screen lets an engineer change Detection, which changes
    Action Priority. That recalculation must come back to risk_engine - a
    frontend doing its own band lookup would be a second, unversioned copy
    of the AP table."""
    import risk_engine

    triples = [(9, 4, 3), (9, 4, 8), (2, 2, 2), (10, 6, 5)]
    body = client.post("/api/rescore", json={
        "rows": [{"severity": s, "occurrence": o, "detection": d}
                 for s, o, d in triples],
    }).json()
    assert len(body) == len(triples)
    for (s, o, d), scored in zip(triples, body):
        assert scored["action_priority"] == risk_engine.action_priority(s, o, d)
        assert scored["rpn_legacy"] == risk_engine.rpn(s, o, d)
        assert scored["levers"] == risk_engine.find_ap_levers(s, o, d)["levers"]


def test_rescore_rejects_an_oversized_batch():
    rows = [{"severity": 5, "occurrence": 5, "detection": 5}] * 501
    assert client.post("/api/rescore", json={"rows": rows}).status_code == 400


def test_agui_endpoint_is_mounted():
    """The AG-UI streaming endpoint the CopilotKit frontend talks to. Only
    checks that it is registered and accepts POST - actually running it
    calls Gemini, which a test suite should not depend on."""
    paths = {r.path for r in api.app.routes if hasattr(r, "methods")}
    assert "/api/ag-ui" in paths
    route = next(r for r in api.app.routes
                 if getattr(r, "path", None) == "/api/ag-ui")
    assert "POST" in route.methods


def test_copilot_health_reports_whether_the_key_actually_works():
    body = client.get("/api/copilot/health").json()
    # Presence and validity are different questions, and the second is the
    # one the frontend needs - a key that is set but rejected looks
    # identical to a working one otherwise.
    assert set(body) >= {"api_key_present", "api_key_works", "reason", "agui_path"}
    assert isinstance(body["api_key_present"], bool)
    assert isinstance(body["api_key_works"], bool)
    assert body["agui_path"] == "/api/ag-ui"
    # A failing check must say why; a passing one has nothing to explain.
    if not body["api_key_works"]:
        assert body["reason"]


def test_issue_summary_covers_active_and_retired_parts():
    summary = client.get("/api/issues/summary").json()
    import data_layer

    all_issues = data_layer.field_issues()
    # Every part_id that has ever filed an issue, not just the 50 on the
    # current BOM - that is the whole point of this route.
    assert len(summary) == all_issues["part_id"].nunique()
    assert sum(row["issue_count"] for row in summary) == len(all_issues)
    assert all(row["issue_count"] >= 1 for row in summary)
    # Sorted worst-first, since that is what a leadership rollup wants to
    # see at the top without having to sort it themselves.
    counts = [row["issue_count"] for row in summary]
    assert counts == sorted(counts, reverse=True)


def test_issue_summary_labels_retired_parts_instead_of_dropping_them():
    summary = client.get("/api/issues/summary").json()
    active_ids = {p["part_id"] for p in client.get("/api/parts").json()}
    retired = [row for row in summary if row["part_id"] not in active_ids]
    assert len(retired) > 0
    assert all("retired" in row["item_reference"] for row in retired)


def test_issues_for_a_part_resolve_the_failure_mode_name():
    part_id = client.get("/api/issues/summary").json()[0]["part_id"]
    issues = client.get("/api/issues/%s" % part_id).json()
    assert len(issues) > 0
    assert all(row["part_id"] == part_id for row in issues)
    assert all(row["failure_mode"] for row in issues)
    # Newest first, matching what "history" implies.
    dates = [row["report_date"] for row in issues]
    assert dates == sorted(dates, reverse=True)


def test_issues_for_an_issue_free_part_is_an_empty_list_not_an_error():
    with_issues = {row["part_id"] for row in client.get("/api/issues/summary").json()}
    all_parts = {p["part_id"] for p in client.get("/api/parts").json()}
    quiet = all_parts - with_issues
    if not quiet:
        return  # every current part happens to have a filed issue - fine
    response = client.get("/api/issues/%s" % next(iter(quiet)))
    assert response.status_code == 200
    assert response.json() == []


def test_gaps_and_metrics_agree():
    gaps = client.get("/api/gaps").json()
    metrics = client.get("/api/gap-metrics").json()
    assert len(gaps) == metrics["total_gaps"]
    assert metrics["safety_gaps"] == sum(1 for g in gaps if g["standard_severity"] >= 9)
    assert 0 <= metrics["mean_coverage_pct"] <= 100


def test_backtest_summary_is_bounded_and_shows_the_lift():
    summary = client.get("/api/backtest").json()["summary"]
    for key in ("dfmea_recall", "mechnari_recall"):
        assert 0.0 <= summary[key] <= 1.0, (key, summary[key])
    assert summary["mechnari_recall"] >= summary["dfmea_recall"]
    assert summary["newly_caught_claims"] >= 0


def test_backtest_sweep_covers_the_offered_cutoffs():
    offered = client.get("/api/backtest/cutoffs").json()
    sweep = client.get("/api/backtest/sweep").json()
    assert offered["default"] in offered["cutoffs"]
    assert len(sweep) > 0
    assert {row["cutoff"] for row in sweep} <= set(offered["cutoffs"])
    for row in sweep:
        assert row["knowable"] + row["unknowable"] == row["incidents"]


def test_cold_start_reports_a_recall():
    body = client.get("/api/backtest/cold-start").json()
    assert 0.0 <= body["recall"] <= 1.0


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
