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
