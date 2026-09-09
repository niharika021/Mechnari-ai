"""
Mechnari.ai - AIAG-VDA form sheet assembly
===========================================
Turns proposed failure modes into rows shaped like the DFMEA form sheet
engineers actually fill in, so the output lands in the format already in
use rather than asking anyone to adopt a new layout.

Two things this module does NOT do, deliberately:

- It computes no scores. Severity, Occurrence, Detection and Action
  Priority all arrive from risk_engine via retrieval; this only arranges
  them into columns.
- It leaves the execution columns empty. RESPONSIBILITY, TARGET
  COMPLETION DATE, ACTION TAKEN and COMPLETED DATE are the engineer's to
  fill. Inventing an owner or a date would be inventing a commitment.

The "Reassessment of Risk" block is the exception worth explaining. On a
manual sheet it is filled in by estimating what the recommended action
will achieve. Here it is read off risk_engine.find_ap_levers: the lever
says which single factor change actually moves the Action Priority band,
so the with-action row states the consequence of the action rather than a
hope about it. Severity is never reassessed downwards - it is fixed by
the failure effect, and an action that does not change the effect cannot
change it.
"""

from typing import Any, Dict, List, Optional

import pandas as pd

import data_layer
import retrieval
import risk_engine

# Part types that are a Programmable Electronic System, for the PES?
# column. Anything solenoid- or sensor-driven answers yes; plain
# mechanical routing does not.
PES_PART_TYPES = frozenset({"PT-VALVE-SOLENOID"})


def _drawing_spec(part_type_id: str, existing_part_id: Optional[str]) -> str:
    """The drawing/design specification reference for this row.

    A part already on file has one recorded. A part that does not exist
    yet has nothing to cite, and saying so is more useful than leaving a
    blank cell an auditor has to ask about.
    """
    if existing_part_id:
        parts = data_layer.parts()
        row = parts[parts["part_id"] == existing_part_id]
        if not row.empty:
            spec = row.iloc[0].get("drawing_spec_ref")
            if isinstance(spec, str) and spec.strip():
                return spec
    return "To be assigned (new part)"


def _reassessment(severity: int, occurrence: int, detection: int) -> Dict[str, Any]:
    """What the recommended action would achieve, from the AP levers.

    Returns the with-action S/O/D/AP, or the unchanged values plus a note
    when no single-factor change moves the band.
    """
    levers = risk_engine.find_ap_levers(severity, occurrence, detection)
    if not levers["levers"]:
        return {
            "reassessed_severity": severity,
            "reassessed_occurrence": occurrence,
            "reassessed_detection": detection,
            "reassessed_action_priority": levers["current_ap"],
            "reassessed_rpn": severity * occurrence * detection,
            "reassessment_basis": (
                "No single change in Occurrence or Detection moves this out of "
                "%s at Severity %d - Occurrence and Detection must improve "
                "together, or the effect itself has to change."
                % (levers["current_ap"], severity)
            ),
        }

    # Smallest effective step first: find_ap_levers already sorts by it.
    lever = levers["levers"][0]
    new_occurrence = lever["to"] if lever["factor"] == "occurrence" else occurrence
    new_detection = lever["to"] if lever["factor"] == "detection" else detection
    return {
        # Severity is set by the failure effect, not by the action.
        "reassessed_severity": severity,
        "reassessed_occurrence": new_occurrence,
        "reassessed_detection": new_detection,
        "reassessed_action_priority": lever["resulting_ap"],
        "reassessed_rpn": severity * new_occurrence * new_detection,
        "reassessment_basis": (
            "Taking the recommended action to bring %s from %d to %d moves "
            "this from %s to %s."
            % (lever["factor"], lever["from"], lever["to"],
               levers["current_ap"], lever["resulting_ap"])
        ),
    }


def _sheet_row(candidate: pd.Series, item: Dict[str, Any],
               part_type_id: str) -> Dict[str, Any]:
    severity = int(candidate["severity"])
    occurrence = int(candidate["occurrence"])
    detection = int(candidate["detection"])

    row: Dict[str, Any] = {
        # --- Correlation matrix interface -----------------------------
        "part_number": item.get("part_number") or "",
        "item_interface": item.get("description") or "",
        "elementary_function": item.get("function") or "",
        "material": item.get("material") or "",
        "system_package": item.get("system_package") or "",

        # --- Failure mode and effects ---------------------------------
        "failure_mode": candidate["failure_mode"],
        "potential_effect": candidate["effect_description"],
        "system_level": candidate["system_level"],
        "severity": severity,

        # --- Failure cause and prevention controls --------------------
        "potential_cause": candidate["potential_cause"],
        "drawing_spec": _drawing_spec(part_type_id, item.get("existing_part_id")),
        "pes": "Y" if part_type_id in PES_PART_TYPES else "N",
        "design_control_prevention": candidate["typical_control"],
        "occurrence": occurrence,

        # --- Detection controls ---------------------------------------
        # worst_escape_stage is where this mode has actually been caught
        # (or escaped to) in the warranty record - a real control point,
        # not a generic "design review".
        "detection_control": candidate.get("worst_escape_stage") or candidate["typical_control"],
        "test_reference": "",  # the engineer's test plan reference
        "detection": detection,

        # --- Priority -------------------------------------------------
        "action_priority": candidate["action_priority"],
        "rpn_legacy": int(candidate["rpn_legacy"]),

        # --- Action details -------------------------------------------
        "recommended_action": candidate["recommended_action"],
        "responsibility": "",
        "target_completion_date": "",
        "action_taken": "",
        "completed_date": "",

        # --- Evidence (not on the paper sheet, and the whole point) ----
        "evidence_ids": candidate.get("evidence_ids") or "",
        "learned_from": candidate.get("learned_from") or "",
        "field_reports": int(candidate.get("field_reports") or 0),
        "field_claims": int(candidate.get("field_claims") or 0),
        "claims_per_1000": (
            None if pd.isna(candidate.get("claims_per_1000"))
            else round(float(candidate["claims_per_1000"]), 2)
        ),
        "scope_level": candidate["scope_level"],
        "mode_id": candidate["mode_id"],
    }
    row.update(_reassessment(severity, occurrence, detection))
    return row


def build_for_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    One item in, one form-sheet block out.

    `item` carries what an engineer knows at design time: part_number,
    description, function, material, system_package, and optionally
    part_type_id to confirm the type or existing_part_id to run against a
    part already on file.
    """
    query = retrieval.describe(
        item.get("description") or "",
        item.get("function") or "",
        item.get("material") or "",
    )
    if not query.strip():
        return {
            "status": "insufficient_input",
            "reason": "Describe the part - a description, function or material.",
            "part_number": item.get("part_number") or "",
            "rows": [],
        }

    proposal = retrieval.propose_dfmea(
        query, part_type_id=item.get("part_type_id") or None
    )
    if proposal["status"] != "success":
        return {
            "status": proposal["status"],
            "reason": proposal["reason"],
            "part_number": item.get("part_number") or "",
            "rows": [],
        }

    part_type_id = proposal["part_type_id"]
    candidates = proposal["candidates"]
    rows = [
        _sheet_row(candidates.iloc[i], item, part_type_id)
        for i in range(len(candidates))
    ]

    # If this is a part already on file, its own warranty history is the
    # most direct evidence there is - more so than a sibling's.
    own_history: List[Dict[str, Any]] = []
    if item.get("existing_part_id"):
        history = data_layer.issue_history(item["existing_part_id"])
        own_history = history.astype(object).where(
            pd.notnull(history), None
        ).to_dict("records")

    neighbours = proposal["neighbours"]
    return {
        "status": "success",
        "part_number": item.get("part_number") or "",
        "item_interface": item.get("description") or "",
        "part_type_id": part_type_id,
        "part_type_name": proposal["part_type_name"],
        "family_name": proposal["family_name"],
        "confidence": proposal["confidence"],
        "confirmed": proposal["confirmed"],
        "confident": proposal["confident"],
        "type_reason": proposal["reason"],
        "safety_rows": int(proposal["safety_candidates"]),
        "similar_parts": neighbours.astype(object).where(
            pd.notnull(neighbours), None
        ).to_dict("records")[:5],
        "own_history": own_history,
        "rows": rows,
    }


def build(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """A whole package: one block per part, plus a package-level rollup."""
    blocks = [build_for_item(item) for item in items]
    all_rows = [row for block in blocks for row in block["rows"]]
    return {
        "items": blocks,
        "total_rows": len(all_rows),
        "high_rows": sum(1 for r in all_rows if r["action_priority"] == "H"),
        "safety_rows": sum(1 for r in all_rows if r["severity"] >= 9),
        "rows_with_evidence": sum(1 for r in all_rows if r["evidence_ids"]),
        "ap_table_verified": risk_engine.AP_TABLE_VERIFIED,
    }
