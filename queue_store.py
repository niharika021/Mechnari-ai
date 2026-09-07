"""
Mechnari.ai - Draft Review Queue
=================================
The record that makes the three role views a real workflow instead of three
independent screens: when a design engineer sends a draft DFMEA for review,
it has to still be there when the quality engineer's tab loads.

This is deliberately a plain JSON file, not a database. It is demo-scale
persistence for a single local instance, not a multi-user store - concurrent
writers can race, and there is no auth. That is an explicit, stated limit,
not an oversight: the target architecture's data layer (Postgres, per part
of Mechnari's own roadmap) replaces this module wholesale, and nothing that
calls it needs to change when that happens - the shape here (draft_id in,
draft_id out, status in between) is the contract that carries over.

A draft holds only what the review actually checks: the rows the design
engineer accepted from the proposal, each with the same severity, occurrence,
detection and evidence a Quality Engineer would find scored a part already
in the system. Rejected rows are not silently dropped - they are kept as
"declined" candidates so review can ask whether a high-severity mode was
declined for a good reason.
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
) -> str:
    """Record a new draft and return its id."""
    draft_id = "DR-" + uuid.uuid4().hex[:8].upper()
    draft = {
        "draft_id": draft_id,
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
    drafts = _load_all()
    drafts.append(draft)
    _save_all(drafts)
    return draft_id


def list_queue() -> List[Dict[str, Any]]:
    """Newest first - what a reviewer opens the queue expecting to see."""
    drafts = _load_all()
    return sorted(drafts, key=lambda d: d["submitted_at"], reverse=True)


def get_draft(draft_id: str) -> Optional[Dict[str, Any]]:
    for draft in _load_all():
        if draft["draft_id"] == draft_id:
            return draft
    return None


def set_status(draft_id: str, status: str, comments: str = "") -> bool:
    """Returns False if the draft_id does not exist, so a stale UI state is
    reported rather than silently doing nothing."""
    if status not in (STATUS_NEEDS_REVIEW, STATUS_RETURNED, STATUS_APPROVED):
        raise ValueError("Unknown status: %s" % status)

    drafts = _load_all()
    found = False
    for draft in drafts:
        if draft["draft_id"] == draft_id:
            draft["status"] = status
            draft["review_comments"] = comments
            draft["reviewed_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break
    if found:
        _save_all(drafts)
    return found


def clear_all() -> None:
    """Used by tests and by a demo reset - never called from the app UI."""
    _save_all([])
