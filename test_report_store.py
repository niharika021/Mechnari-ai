"""
Ownership rules for the design engineer's reports.

Run with:  python test_report_store.py     (or: pytest test_report_store.py)

These are the tests worth having on this module. A report is one
engineer's working copy, so the interesting behaviour is not that it round
trips - it is that somebody else cannot touch it, and that "not found" and
"not yours" stay distinguishable. Every test forces the file backend, so
the suite never reads or writes a real database.
"""

import os
import sys
import tempfile

import report_store as rs

SAMPLE_RESULT = {
    "items": [{
        "status": "success",
        "part_number": "EXAMPLE-0001",
        "item_interface": "EPDM Fuel Return Line",
        "rows": [{"mode_id": "FM-A", "failure_mode": "Tube kink",
                  "severity": 10, "occurrence": 6, "detection": 5,
                  "action_priority": "H"}],
    }],
    "total_rows": 1,
}

ALICE = ("uid-alice", "A. Engineer")
BOB = ("uid-bob", "B. Engineer")


def _use_scratch_store():
    """File backend, throwaway path.

    USE_FIRESTORE is switched off explicitly rather than assumed:
    GOOGLE_CLOUD_PROJECT is in .env for Vertex, so the module would
    otherwise prefer the real database - which is how the API suite once
    ended up writing to the live review queue.
    """
    rs.USE_FIRESTORE = False
    rs._client = None
    rs._client_failed = False
    handle, path = tempfile.mkstemp(suffix=".json")
    os.close(handle)
    os.remove(path)
    rs.STORE_PATH = path
    return path


def _create(owner=ALICE, title="Report"):
    return rs.create(owner[0], owner[1], title, "Fuel Routings", SAMPLE_RESULT)


def test_create_then_get_round_trips_the_whole_result():
    _use_scratch_store()
    created = _create()
    fetched = rs.get(created["id"])
    assert fetched is not None
    assert fetched["owner_uid"] == ALICE[0]
    assert fetched["owner_name"] == ALICE[1]
    assert fetched["row_count"] == 1
    # The sheet itself has to survive, not a summary of it.
    assert fetched["result"]["items"][0]["rows"][0]["failure_mode"] == "Tube kink"


def test_list_returns_only_the_callers_reports():
    _use_scratch_store()
    _create(ALICE, "Alice's")
    _create(BOB, "Bob's")
    titles = [r["title"] for r in rs.list_for_owner(ALICE[0])]
    assert titles == ["Alice's"]


def test_list_omits_the_result_payload():
    """Listing whole reports would send megabytes to render a table of
    titles - twenty-odd rows of forty-odd fields per part."""
    _use_scratch_store()
    _create()
    summaries = rs.list_for_owner(ALICE[0])
    assert summaries and "result" not in summaries[0]
    assert summaries[0]["row_count"] == 1


def test_newest_first():
    _use_scratch_store()
    first = _create(ALICE, "older")
    second = _create(ALICE, "newer")
    # updated_at is set on create, so ordering is by that.
    rs.update(second["id"], ALICE[0], result=SAMPLE_RESULT)
    ids = [r["id"] for r in rs.list_for_owner(ALICE[0])]
    assert ids[0] == second["id"]
    assert first["id"] in ids


def test_another_engineer_cannot_update_your_report():
    _use_scratch_store()
    created = _create(ALICE)
    try:
        rs.update(created["id"], BOB[0], result={"items": [], "total_rows": 0})
    except PermissionError:
        pass
    else:
        raise AssertionError("Bob was allowed to edit Alice's report")
    # And the report is untouched.
    assert rs.get(created["id"])["row_count"] == 1


def test_another_engineer_cannot_delete_your_report():
    _use_scratch_store()
    created = _create(ALICE)
    try:
        rs.delete(created["id"], BOB[0])
    except PermissionError:
        pass
    else:
        raise AssertionError("Bob was allowed to delete Alice's report")
    assert rs.get(created["id"]) is not None


def test_missing_and_not_yours_are_different_answers():
    """Collapsing them would let an engineer silently fail to edit a
    colleague's report with no idea why."""
    _use_scratch_store()
    created = _create(ALICE)
    assert rs.update("RPT-NOPE", ALICE[0], result=SAMPLE_RESULT) is None
    assert rs.delete("RPT-NOPE", ALICE[0]) is False
    try:
        rs.update(created["id"], BOB[0], result=SAMPLE_RESULT)
        raise AssertionError("expected PermissionError")
    except PermissionError:
        pass


def test_update_records_submission_without_disturbing_the_sheet():
    _use_scratch_store()
    created = _create(ALICE)
    rs.update(created["id"], ALICE[0],
              submitted_at="2026-09-09T12:00:00Z", draft_ids=["DR-ABC"])
    after = rs.get(created["id"])
    assert after["submitted_at"] == "2026-09-09T12:00:00Z"
    assert after["draft_ids"] == ["DR-ABC"]
    assert after["result"]["items"][0]["rows"][0]["failure_mode"] == "Tube kink"


def test_owner_can_delete_their_own():
    _use_scratch_store()
    created = _create(ALICE)
    assert rs.delete(created["id"], ALICE[0]) is True
    assert rs.get(created["id"]) is None


def test_backend_is_the_file_when_no_project_is_configured():
    _use_scratch_store()
    rs.USE_FIRESTORE = True
    rs._client = None
    rs._client_failed = False
    saved = {k: os.environ.pop(k, None)
             for k in ("GOOGLE_CLOUD_PROJECT", "FIRESTORE_PROJECT")}
    try:
        assert rs.backend() == "file"
        created = _create()
        assert rs.get(created["id"]) is not None
    finally:
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v
        rs.USE_FIRESTORE = False
        rs._client = None
        rs._client_failed = False


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
