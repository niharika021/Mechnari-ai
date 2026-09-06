"""
Mechnari.ai - ADK Function Tools
=================================
The deterministic engines exposed to Google ADK agents as function tools.

Written to the ADK Python tool contract: plain functions with type hints on
every parameter and an Args section in the docstring, which the framework
inspects to build the tool schema and wraps as a FunctionTool automatically.
Each returns a dict carrying a "status" key, as the ADK docs recommend, so a
failure is something the agent can read rather than an exception it cannot.

The important property: every number an agent can see comes from
gap_detection or risk_engine. The model may summarise, prioritise and
explain these results, but it has no path to compute or alter a severity,
an occurrence, a detection score or an Action Priority. That is what keeps
the output defensible in an audit, and it is enforced here by simply not
giving the model a tool that would let it.
"""

from typing import Any, Dict

import data_layer
import gap_detection
import risk_engine

# Row caps keep tool results small enough to stay useful in a prompt. The
# full frames remain available to the dashboard.
MAX_ROWS = 12


def _error(message: str) -> Dict[str, Any]:
    return {"status": "error", "error_message": message}


def list_parts(system_package: str = "") -> Dict[str, Any]:
    """Lists the parts in the active BOM, optionally filtered to one system package.

    Use this to find a part_id when the user names a component in words rather
    than by its identifier.

    Args:
        system_package (str): Optional system package to filter by, for example
            'Fuel Routings'. Pass an empty string to list every part.
    """
    try:
        parts = data_layer.parts()
    except data_layer.DatasetError as exc:
        return _error(str(exc))

    if system_package:
        parts = parts[parts["system_package"] == system_package]
        if parts.empty:
            return _error("No parts in system package '%s'." % system_package)

    return {
        "status": "success",
        "part_count": int(len(parts)),
        "parts": [
            {
                "part_id": row["part_id"],
                "component": row["item_reference"],
                "system_package": row["system_package"],
                "part_type": row["part_type_name"],
            }
            for _, row in parts.head(MAX_ROWS * 5).iterrows()
        ],
    }


def get_part_profile(part_id: str) -> Dict[str, Any]:
    """Returns the engineering profile of one part.

    Covers the component name, its system package, the part type and family it
    inherits failure history from, its material and the drawing specification.

    Args:
        part_id (str): The part identifier, for example 'TR-FL-001'.
    """
    try:
        parts = data_layer.parts()
    except data_layer.DatasetError as exc:
        return _error(str(exc))

    match = parts[parts["part_id"] == part_id]
    if match.empty:
        return _error("Unknown part_id '%s'." % part_id)

    row = match.iloc[0]
    return {
        "status": "success",
        "part_id": row["part_id"],
        "component": row["item_reference"],
        "system_package": row["system_package"],
        "elementary_function": row["elementary_function"],
        "part_type": row["part_type_name"],
        "part_family": row["family_name"],
        "material": row["material_type"],
        "yield_strength_mpa": float(row["yield_strength_mpa"]),
        "max_temp_limit_c": float(row["max_temp_limit_c"]),
        "drawing_spec_ref": row["drawing_spec_ref"],
    }


def find_unanalysed_failure_modes(part_id: str) -> Dict[str, Any]:
    """Finds failure modes proven on this kind of part that this part's DFMEA never analysed.

    This is a deterministic set difference between the failure modes known for
    the part's type and family and the modes its DFMEA on file actually covers.
    Every result carries the 8D warranty records behind it. Results are ordered
    by severity, highest first.

    Args:
        part_id (str): The part identifier, for example 'TR-FL-001'.
    """
    try:
        gaps = gap_detection.detect_gaps(part_id)
    except KeyError:
        return _error("Unknown part_id '%s'." % part_id)
    except data_layer.DatasetError as exc:
        return _error(str(exc))

    if gaps.empty:
        return {
            "status": "success",
            "part_id": part_id,
            "gap_count": 0,
            "findings": [],
            "note": "This DFMEA covers every failure mode known for its part type and family.",
        }

    return {
        "status": "success",
        "part_id": part_id,
        "gap_count": int(len(gaps)),
        "safety_gap_count": int((gaps["standard_severity"] >= 9).sum()),
        "findings": [
            {
                "failure_mode": row["failure_mode"],
                "potential_cause": row["potential_cause"],
                "effect": row["effect_description"],
                "severity": int(row["standard_severity"]),
                "priority": row["priority"],
                "learned_from": row["learned_from"],
                "inherited_at": row["scope_level"],
                "warranty_evidence": row["evidence_summary"],
                "existing_control": row["typical_control"],
                "recommended_action": row["recommended_action"],
            }
            for _, row in gaps.head(MAX_ROWS).iterrows()
        ],
    }


def get_risk_scores(part_id: str) -> Dict[str, Any]:
    """Returns the DFMEA rows on file for a part, rescored against field evidence.

    Severity comes from the organization's failure effect registry, Occurrence
    from measured warranty claims per 1000 units in service where any record
    exists, and Action Priority from the AIAG-VDA band lookup. The Action
    Priority as originally filed is returned alongside so any change is visible.
    Legacy RPN is included for reviewers who still read it.

    Args:
        part_id (str): The part identifier, for example 'TR-FL-001'.
    """
    try:
        scored = risk_engine.scored_worksheet(part_id)
    except KeyError:
        return _error("Unknown part_id '%s'." % part_id)
    except data_layer.DatasetError as exc:
        return _error(str(exc))

    return {
        "status": "success",
        "part_id": part_id,
        "action_priority_table_verified": risk_engine.AP_TABLE_VERIFIED,
        "rows": [
            {
                "failure_mode": row["failure_mode"],
                "effect": row["effect_description"],
                "severity": int(row["severity_standard"]),
                "occurrence_as_filed": int(row["occurrence"]),
                "occurrence_from_evidence": int(row["evidence_occurrence"]),
                "detection": int(row["detection"]),
                "action_priority_as_filed": row["ap_as_filed"],
                "action_priority_on_evidence": row["ap_evidence_based"],
                "rpn_legacy": int(row["rpn_legacy"]),
                "evidence_scope": row["evidence_scope"],
                "warranty_records": row["evidence_ids"],
            }
            for _, row in scored.head(MAX_ROWS).iterrows()
        ],
    }


def get_occurrence_evidence(part_id: str) -> Dict[str, Any]:
    """Returns where the DFMEA's Occurrence scores disagree with the warranty record.

    Occurrence measured on the part itself is direct evidence and is labelled
    OWN_PART. A rate measured on sibling parts of the same type is a prior
    rather than a measurement and is labelled TYPE_HISTORY; say which one you
    are relying on when you explain a finding.

    Args:
        part_id (str): The part identifier, for example 'TR-FL-001'.
    """
    try:
        findings = risk_engine.occurrence_findings()
    except data_layer.DatasetError as exc:
        return _error(str(exc))

    findings = findings[findings["part_id"] == part_id]
    if findings.empty:
        return {
            "status": "success",
            "part_id": part_id,
            "finding_count": 0,
            "findings": [],
            "note": "Occurrence scores on file are consistent with the warranty record.",
        }

    return {
        "status": "success",
        "part_id": part_id,
        "finding_count": int(len(findings)),
        "findings": [
            {
                "failure_mode": row["failure_mode"],
                "occurrence_as_filed": int(row["occurrence"]),
                "occurrence_from_claims": int(row["derived_occurrence"]),
                "finding": row["finding"],
                "evidence_scope": row["evidence_scope"],
                "claims_per_1000_units": float(row["claims_per_1000"]),
                "total_claims": int(row["field_claims"]),
                "warranty_records": row["evidence_ids"],
            }
            for _, row in findings.head(MAX_ROWS).iterrows()
        ],
    }


def check_severity_consistency(part_id: str) -> Dict[str, Any]:
    """Checks whether a part's DFMEA scores a failure effect against the org standard.

    Severity is a property of the failure effect at a system level, so the same
    effect must carry the same severity on every program. Divergence is a
    standard audit finding.

    Args:
        part_id (str): The part identifier, for example 'TR-FL-001'.
    """
    try:
        findings = gap_detection.severity_consistency_findings()
    except data_layer.DatasetError as exc:
        return _error(str(exc))

    findings = findings[findings["part_id"] == part_id]
    if findings.empty:
        return {
            "status": "success",
            "part_id": part_id,
            "finding_count": 0,
            "findings": [],
            "note": "Severity scores match the organization standard for every effect.",
        }

    return {
        "status": "success",
        "part_id": part_id,
        "finding_count": int(len(findings)),
        "findings": [
            {
                "failure_mode": row["failure_mode"],
                "effect": row["effect_description"],
                "severity_as_filed": int(row["severity"]),
                "severity_org_standard": int(row["standard_severity"]),
                "finding": row["finding"],
                "analysed_by": row["analyzed_by"],
            }
            for _, row in findings.head(MAX_ROWS).iterrows()
        ],
    }


# The toolsets each agent is given. Keeping them here means the agent module
# declares intent and this module owns the contract.
KNOWLEDGE_BASE_TOOLS = [list_parts, get_part_profile]
GAP_TOOLS = [get_part_profile, find_unanalysed_failure_modes]
RISK_TOOLS = [get_risk_scores, get_occurrence_evidence, check_severity_consistency]
ALL_TOOLS = KNOWLEDGE_BASE_TOOLS + [
    find_unanalysed_failure_modes,
    get_risk_scores,
    get_occurrence_evidence,
    check_severity_consistency,
]
