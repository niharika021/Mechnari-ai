"""
Mechnari.ai - the design engineer's own reports
===============================================
A generated DFMEA that its author is still working: actions being
assigned, done and stamped. Distinct from the review queue, which is the
shared record Quality reads. A report becomes the queue's business only
when it is sent.

Ownership is by verified Google account (`owner_uid`), which is why this
could move off the browser at all. Before sign-in there was no answer to
"whose report is this", so localStorage - one workspace per browser - was
the honest option. Now there is an answer.

Signed-out use still works and deliberately does not write here. A report
made while signed out stays in that browser's localStorage, because
writing owner-less rows into a shared database would make them nobody's
and everybody's at once. The frontend says which of the two it is rather
than leaving the engineer to guess.

Same fallback contract as queue_store: Firestore when a project is
configured, otherwise a JSON file, so local development and the tests run
with no cloud access.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_HERE = os.path.dirname(os.path.abspath(__file__))
STORE_PATH = os.path.join(_HERE, ".mechnari_runtime", "reports.json")

COLLECTION = "reports"

# Forced off by the tests so they never touch a real database.
USE_FIRESTORE = True

_client = None
_client_failed = False


def _firestore():
    global _client, _client_failed
    if not USE_FIRESTORE or _client_failed:
        return None
    if _client is not None:
        return _client
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("FIRESTORE_PROJECT")
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
        return []


def _save_all(reports: List[Dict[str, Any]]) -> None:
    _ensure_store_dir()
    tmp_path = STORE_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(reports, f, indent=2, default=str)
    os.replace(tmp_path, STORE_PATH)


def _summary(report: Dict[str, Any]) -> Dict[str, Any]:
    """The list view. The full sheet is large - twenty-odd rows of forty-odd
    fields per part - so listing them whole would send megabytes to render
    a table of titles."""
    return {k: v for k, v in report.items() if k != "result"}


def create(
    owner_uid: str,
    owner_name: str,
    title: str,
    system_package: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    items = result.get("items") or []
    report = {
        "id": "RPT-" + uuid.uuid4().hex[:10].upper(),
        "owner_uid": owner_uid,
        "owner_name": owner_name,
        "title": title,
        "system_package": system_package,
        "part_count": len(items),
        "row_count": int(result.get("total_rows") or 0),
        "created_at": now,
        "updated_at": now,
        "submitted_at": None,
        "draft_ids": [],
        "result": result,
    }
    db = _firestore()
    if db is not None:
        db.collection(COLLECTION).document(report["id"]).set(report)
    else:
        _save_all(_load_all() + [report])
    return report


def list_for_owner(owner_uid: str) -> List[Dict[str, Any]]:
    """Summaries only, newest first. Filtered by owner in the query rather
    than after loading, so one engineer's list does not cost the price of
    reading everybody's."""
    db = _firestore()
    if db is not None:
        docs = (
            db.collection(COLLECTION)
            .where(filter=_owner_filter(owner_uid))
            .stream()
        )
        reports = [doc.to_dict() for doc in docs]
    else:
        reports = [r for r in _load_all() if r.get("owner_uid") == owner_uid]
    reports.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    return [_summary(r) for r in reports]


def _owner_filter(owner_uid: str):
    from google.cloud.firestore_v1.base_query import FieldFilter

    return FieldFilter("owner_uid", "==", owner_uid)


def get(report_id: str) -> Optional[Dict[str, Any]]:
    db = _firestore()
    if db is not None:
        doc = db.collection(COLLECTION).document(report_id).get()
        return doc.to_dict() if doc.exists else None
    for report in _load_all():
        if report["id"] == report_id:
            return report
    return None


def update(
    report_id: str,
    owner_uid: str,
    result: Optional[Dict[str, Any]] = None,
    submitted_at: Optional[str] = None,
    draft_ids: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Returns None when the report does not exist, and raises PermissionError
    when it exists but belongs to somebody else.

    The two are distinguished on purpose: "not found" and "not yours" are
    different facts, and collapsing them would let one engineer silently
    fail to edit a colleague's report with no idea why.
    """
    existing = get(report_id)
    if existing is None:
        return None
    if existing.get("owner_uid") != owner_uid:
        raise PermissionError(report_id)

    patch: Dict[str, Any] = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if result is not None:
        patch["result"] = result
        patch["row_count"] = int(result.get("total_rows") or 0)
    if submitted_at is not None:
        patch["submitted_at"] = submitted_at
    if draft_ids is not None:
        patch["draft_ids"] = draft_ids

    db = _firestore()
    if db is not None:
        db.collection(COLLECTION).document(report_id).update(patch)
        return get(report_id)

    reports = _load_all()
    for i, report in enumerate(reports):
        if report["id"] == report_id:
            reports[i] = {**report, **patch}
            _save_all(reports)
            return reports[i]
    return None


def delete(report_id: str, owner_uid: str) -> bool:
    existing = get(report_id)
    if existing is None:
        return False
    if existing.get("owner_uid") != owner_uid:
        raise PermissionError(report_id)

    db = _firestore()
    if db is not None:
        db.collection(COLLECTION).document(report_id).delete()
        return True
    _save_all([r for r in _load_all() if r["id"] != report_id])
    return True


def clear_all() -> None:
    """Tests and demo reset only."""
    db = _firestore()
    if db is not None:
        for doc in db.collection(COLLECTION).stream():
            doc.reference.delete()
        return
    _save_all([])
