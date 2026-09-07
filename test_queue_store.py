"""
Invariants for the draft review queue.

Run with:  python test_queue_store.py     (or: pytest test_queue_store.py)

Every test redirects STORE_PATH to a scratch file first, so this suite never
touches (or is affected by) the real runtime queue.
"""

import os
import sys
import tempfile

import queue_store as qs

SAMPLE_ROWS = [
    {"failure_mode": "Fuel leakage at crimped ferrule joint", "severity": 9,
     "occurrence": 4, "detection": 4, "action_priority": "H",
     "evidence_ids": "8D-2023-0018"},
]


def _use_scratch_store():
    handle, path = tempfile.mkstemp(suffix=".json")
    os.close(handle)
    os.remove(path)  # submit_draft/_save_all must create it fresh
    qs.STORE_PATH = path
    return path


def test_empty_queue_before_anything_is_submitted():
    _use_scratch_store()
    assert qs.list_queue() == []


def test_submit_then_list_round_trips():
    _use_scratch_store()
    draft_id = qs.submit_draft(
        "EPDM Fuel Return Line", "Return diesel to tank",
        "EPDM rubber", "Fuel Routings", "Fuel Hose / Flexible Fuel Line",
        accepted_rows=SAMPLE_ROWS, declined_rows=[])
    assert draft_id.startswith("DR-")

    queue = qs.list_queue()
    assert len(queue) == 1
    assert queue[0]["draft_id"] == draft_id
    assert queue[0]["status"] == qs.STATUS_NEEDS_REVIEW
    assert queue[0]["accepted_rows"] == SAMPLE_ROWS


def test_get_draft_finds_it_and_returns_none_for_unknown_id():
    _use_scratch_store()
    draft_id = qs.submit_draft("X", "f", "m", "pkg", "type",
                               accepted_rows=[], declined_rows=[])
    assert qs.get_draft(draft_id)["draft_id"] == draft_id
    assert qs.get_draft("DR-NOTREAL") is None


def test_set_status_updates_and_reports_success():
    _use_scratch_store()
    draft_id = qs.submit_draft("X", "f", "m", "pkg", "type",
                               accepted_rows=[], declined_rows=[])
    ok = qs.set_status(draft_id, qs.STATUS_APPROVED, "looks good")
    assert ok is True

    draft = qs.get_draft(draft_id)
    assert draft["status"] == qs.STATUS_APPROVED
    assert draft["review_comments"] == "looks good"
    assert draft["reviewed_at"] is not None


def test_set_status_on_unknown_id_reports_failure_not_silence():
    _use_scratch_store()
    assert qs.set_status("DR-NOTREAL", qs.STATUS_APPROVED) is False


def test_set_status_rejects_an_unknown_status_value():
    _use_scratch_store()
    draft_id = qs.submit_draft("X", "f", "m", "pkg", "type",
                               accepted_rows=[], declined_rows=[])
    try:
        qs.set_status(draft_id, "vaguely_fine")
    except ValueError:
        return
    raise AssertionError("an unrecognised status should raise, not be stored silently")


def test_queue_survives_a_fresh_load_from_disk():
    """Not session_state - a real read from the file, as a second process would see it."""
    path = _use_scratch_store()
    qs.submit_draft("X", "f", "m", "pkg", "type", accepted_rows=[], declined_rows=[])

    reloaded = qs._load_all()
    assert len(reloaded) == 1
    with open(path, encoding="utf-8") as f:
        import json
        on_disk = json.load(f)
    assert on_disk == reloaded


def test_a_corrupt_store_file_reads_as_empty_not_a_crash():
    path = _use_scratch_store()
    with open(path, "w", encoding="utf-8") as f:
        f.write("{not valid json")
    assert qs.list_queue() == []


def test_newest_submission_is_listed_first():
    _use_scratch_store()
    first = qs.submit_draft("A", "f", "m", "pkg", "type", accepted_rows=[], declined_rows=[])
    second = qs.submit_draft("B", "f", "m", "pkg", "type", accepted_rows=[], declined_rows=[])
    queue = qs.list_queue()
    # submitted_at is an ISO timestamp with second resolution; two calls in
    # the same test can tie, so assert by id set and that a real order exists
    # rather than assuming distinguishable timestamps.
    ids = [d["draft_id"] for d in queue]
    assert set(ids) == {first, second}
    assert queue == sorted(queue, key=lambda d: d["submitted_at"], reverse=True)


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
