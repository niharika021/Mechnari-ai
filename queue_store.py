"""
Mechnari.ai - Draft Review Queue
=================================
The record that makes the three role views a real workflow instead of three
independent screens: when a design engineer sends a draft DFMEA for review,
it has to still be there when the quality engineer's tab loads.

Two backends, one interface.

Firestore is used when a project is configured (GOOGLE_CLOUD_PROJECT, plus
ADC locally or the service account on Cloud Run). That is not a nice-to-have:
the JSON file below lives on the container's own disk, and Cloud Run's
filesystem is per-instance and resets on scale-to-zero. On the deployed app
that meant a draft could be submitted, the service could idle, and the
Quality queue would come back empty - real data loss, not a theoretical
limit. Firestore also makes the draft one record two roles read, rather than
two stores with a copy between them.

The JSON file remains as the fallback when no project is configured, so local
development and the test suite work with no cloud access at all. Both paths
are exercised by test_queue_store.py, which is what makes the swap
verifiable rather than hopeful.

What is still missing is auth. The queue is shared by design - every reviewer
sees every draft - which is correct for this record and is why it could move
to Firestore without first deciding what "mine" means. The design engineer's
own working reports are a different question and deliberately stay in the
browser until there is an identity to attach them to.

A draft holds only what the review actually checks: the rows the design
engineer accepted, each with the same severity, occurrence, detection and
evidence a Quality Engineer would find scored a part already in the system,
plus the provenance of the engineer's decisions. Rejected rows are not
silently dropped - they are kept as "declined" candidates with the reason, so
review can tell a considered rejection from an oversight.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
STORE_PATH = os.path.join(_HERE, ".mechnari_runtime", "draft_queue.json")

STATUS_NEEDS_REVIEW = "needs_review"
STATUS_RETURNED = "returned"
STATUS_APPROVED = "approved"

COLLECTION = "draft_queue"

# Set to False to force the file backend even with a project configured -
# what the tests use, so they never touch a real database.
USE_FIRESTORE = True

_client = None
_client_failed = False


def _project() -> Optional[str]:
    return os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("FIRESTORE_PROJECT")


def _firestore():
    """The Firestore client, or None to fall back to the file.

    A failure here is deliberately not fatal. The queue is a workflow
    convenience; if the database is unreachable the app should degrade to
    local storage rather than refuse to serve a DFMEA. The failure is
    remembered so every call does not retry a broken connection.
    """
    global _client, _client_failed
    if not USE_FIRESTORE or _client_failed:
        return None
    if _client is not None:
        return _client
    project = _project()
    if not project:
        return None
    try:
        from google.cloud import firestore

        _client = firestore.Client(project=project)
        return _client
    except Exception:  # noqa: BLE001 - degrade, do not crash
        _client_failed = True
        return None


def backend() -> str:
    """Which store is actually in use - surfaced so the UI and the deploy
    checks can state it rather than assume it."""
    return "firestore" if _firestore() is not None else "file"


def _ensure_store_dir() -> None:
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)


def _load_all() -> List[Dict[str, Any]]:
    if not os.path.exists(STORE_PATH):
        return []
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # A half-written file from a killed process should not crash the
        # app - it should look like an empty queue, which is recoverable.
        return []


def _save_all(drafts: List[Dict[str, Any]]) -> None:
    _ensure_store_dir()
    tmp_path = STORE_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(drafts, f, indent=2, default=str)
    os.replace(tmp_path, STORE_PATH)  # atomic on both POSIX and Windows


def submit_draft(
    part_name: str,
    function: str,
    material: str,
    system_package: str,
    part_type_name: str,
    accepted_rows: List[Dict[str, Any]],
    declined_rows: List[Dict[str, Any]],
    submitted_by: str = "Design Engineer",
    part_number: str = "",
    package_ref: str = "",
) -> str:
    """
    Record a new draft and return its id.

    part_number and package_ref default to empty so drafts written before
    they existed still load. package_ref groups the drafts that came from
    one package submission - each part is reviewed on its own merits, but
    Quality can still see they arrived together.
    """
    draft_id = "DR-" + uuid.uuid4().hex[:8].upper()
    draft = {
        "draft_id": draft_id,
        "part_number": part_number,
        "package_ref": package_ref,
        "part_name": part_name,
        "function": function,
        "material": material,
        "system_package": system_package,
        "part_type_name": part_type_name,
        "accepted_rows": accepted_rows,
        "declined_rows": declined_rows,
        "submitted_by": submitted_by,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "status": STATUS_NEEDS_REVIEW,
        "review_comments": "",
        "reviewed_at": None,
    }
    db = _firestore()
    if db is not None:
        # The draft_id is the document id, so get_draft is a direct read
        # rather than a scan - and two submits cannot collide on it.
        db.collection(COLLECTION).document(draft_id).set(draft)
        return draft_id

    drafts = _load_all()
    drafts.append(draft)
    _save_all(drafts)
    return draft_id


def list_queue() -> List[Dict[str, Any]]:
    """Newest first - what a reviewer opens the queue expecting to see."""
    db = _firestore()
    if db is not None:
        # Sorted in Python rather than with order_by: submitted_at is an
        # ISO string, so lexical and chronological order agree, and this
        # needs no composite index to deploy.
        drafts = [doc.to_dict() for doc in db.collection(COLLECTION).stream()]
    else:
        drafts = _load_all()
    return sorted(drafts, key=lambda d: d.get("submitted_at") or "", reverse=True)


def get_draft(draft_id: str) -> Optional[Dict[str, Any]]:
    db = _firestore()
    if db is not None:
        doc = db.collection(COLLECTION).document(draft_id).get()
        return doc.to_dict() if doc.exists else None

    for draft in _load_all():
        if draft["draft_id"] == draft_id:
            return draft
    return None


def set_status(draft_id: str, status: str, comments: str = "") -> bool:
    """Returns False if the draft_id does not exist, so a stale UI state is
    reported rather than silently doing nothing."""
    if status not in (STATUS_NEEDS_REVIEW, STATUS_RETURNED, STATUS_APPROVED):
        raise ValueError("Unknown status: %s" % status)

    reviewed_at = datetime.now(timezone.utc).isoformat()

    db = _firestore()
    if db is not None:
        ref = db.collection(COLLECTION).document(draft_id)
        if not ref.get().exists:
            return False
        # update, not set: this touches the review fields only and cannot
        # clobber the rows a concurrent writer may have changed.
        ref.update({
            "status": status,
            "review_comments": comments,
            "reviewed_at": reviewed_at,
        })
        return True

    drafts = _load_all()
    found = False
    for draft in drafts:
        if draft["draft_id"] == draft_id:
            draft["status"] = status
            draft["review_comments"] = comments
            draft["reviewed_at"] = reviewed_at
            found = True
            break
    if found:
        _save_all(drafts)
    return found


def clear_all() -> None:
    """Used by tests and by a demo reset - never called from the app UI."""
    db = _firestore()
    if db is not None:
        for doc in db.collection(COLLECTION).stream():
            doc.reference.delete()
        return
    _save_all([])
