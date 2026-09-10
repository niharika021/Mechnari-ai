"""
Mechnari.ai - failure records the engineer supplies
===================================================
A designer often knows something the warranty database does not: a
failure seen on a prototype, on a previous employer's equivalent part, in
a supplier's report, or in a test that never became an 8D. This turns
that knowledge into DFMEA rows without letting it bypass the engines.

The rule this module exists to hold
-----------------------------------
An engineer-supplied record is **evidence**, not a score. The engineer
says what happened; the engines still say what it is worth:

- **Severity** comes from the organisation's effect registry, chosen by
  `effect_id`. There is no field for the engineer to type a severity
  into, because the whole product rests on Severity being a property of
  the effect rather than of whoever is filling in the sheet. Supplying an
  effect that is not in the registry is an error, not a new effect.
- **Occurrence** is derived by `risk_engine.occurrence_from_claims` when
  a claim count and a fleet size are given - the same function, on the
  same scale, that the warranty path uses. Without both numbers there is
  no rate to derive from, so it stays at the floor and the row says so.
- **Detection** is `risk_engine.detection_floor` of the stage the
  engineer says the failure escaped to. A failure that reached a customer
  cannot honestly be scored as well-detected, and the floor is what
  enforces that.
- **Action Priority** is computed from those three by the same AP table
  as every other row.

So the engineer contributes observations and judgement about what
happened; the engines contribute every number. That is the same division
the agent operates under, applied to human input.

Provenance
----------
Rows carry `scope_level: "ENGINEER"` and name the source in
`learned_from`, so a Quality reviewer can tell at a glance which rows
rest on the warranty record, which on generic practice, and which on a
colleague's recollection. All three are legitimate; conflating them is
not.
"""

import re
from typing import Any, Dict, List

import pandas as pd

import data_layer
import risk_engine

# The stages risk_engine knows how to put a Detection floor under. Kept
# as an ordered list because it is also what the UI offers.
DETECTION_STAGES = [
    ("VALIDATION_TEST", "Caught in design validation testing"),
    ("END_OF_LINE_TEST", "Caught at end-of-line test"),
    ("DEALER_SERVICE", "Found at dealer / service"),
    ("FIELD_CUSTOMER", "Reached the customer in the field"),
]
VALID_STAGES = {stage for stage, _ in DETECTION_STAGES}


class OwnRecordError(ValueError):
    """The supplied record cannot be scored. The message says why."""


def _mode_id(failure_mode: str, index: int) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (failure_mode or "").lower()).strip("-")
    return "ENG-%02d-%s" % (index + 1, (slug[:28] or "mode"))


def build_rows(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Engineer-supplied records, scored, in the shape retrieval returns.

    Same columns as `retrieval.candidate_failure_modes` so `dfmea_sheet`
    builds a row from either without knowing which it has.
    """
    if not records:
        return pd.DataFrame()

    effects = data_layer.failure_effects()
    severity_by_effect = dict(zip(effects["effect_id"], effects["standard_severity"]))
    description_by_effect = dict(zip(effects["effect_id"], effects["effect_description"]))
    level_by_effect = dict(zip(effects["effect_id"], effects["system_level"]))

    rows = []
    for index, record in enumerate(records):
        failure_mode = (record.get("failure_mode") or "").strip()
        if not failure_mode:
            raise OwnRecordError("Every supplied record needs a failure mode.")

        effect_id = (record.get("effect_id") or "").strip()
        if effect_id not in severity_by_effect:
            raise OwnRecordError(
                "Unknown effect_id %r. Severity comes from the organisation's "
                "effect registry, so the effect has to be one already in it."
                % effect_id
            )

        stage = (record.get("detection_stage") or "").strip()
        if stage not in VALID_STAGES:
            raise OwnRecordError(
                "detection_stage must be one of %s - it is what puts a floor "
                "under Detection." % ", ".join(sorted(VALID_STAGES))
            )

        claims = record.get("claim_count")
        units = record.get("units_in_service")
        has_rate = bool(claims) and bool(units)
        if has_rate:
            occurrence = risk_engine.occurrence_from_claims(float(claims), float(units))
            rate = round(float(claims) / float(units) * 1000.0, 2)
            evidence = (record.get("reference") or "").strip() or "engineer-supplied record"
            evidence_ids = "%s (%s claims / %s units)" % (evidence, claims, units)
        else:
            # No rate to derive from. The floor, and it says so - rather
            # than a guess that would look identical to a measured one.
            occurrence = risk_engine.occurrence_from_rate(0)
            rate = 0.0
            evidence = (record.get("reference") or "").strip() or "engineer-supplied record"
            evidence_ids = "%s (no rate given)" % evidence

        severity = int(severity_by_effect[effect_id])
        detection = risk_engine.detection_floor(stage)

        rows.append({
            "mode_id": _mode_id(failure_mode, index),
            "scope_id": "ENGINEER",
            "scope_level": "ENGINEER",
            "failure_mode": failure_mode,
            "potential_cause": (record.get("potential_cause") or "").strip(),
            "effect_id": effect_id,
            "effect_description": description_by_effect[effect_id],
            "system_level": level_by_effect[effect_id],
            "typical_control": (record.get("control") or "").strip()
                               or "stated by the engineer, no control on file",
            "baseline_detection": detection,
            "recommended_action": (record.get("recommended_action") or "").strip(),
            "severity": severity,
            "occurrence": occurrence,
            "detection": detection,
            "action_priority": risk_engine.action_priority(severity, occurrence, detection),
            "rpn_legacy": risk_engine.rpn(severity, occurrence, detection),
            "field_reports": 1 if has_rate else 0,
            "field_claims": int(claims) if has_rate else 0,
            "claims_per_1000": rate,
            "evidence_ids": evidence_ids,
            "learned_from": "supplied by the design engineer",
            "worst_escape_stage": stage,
            "origin": "ENGINEER_SUPPLIED",
            "origin_part_id": "",
            "origin_part_name": "",
        })

    return pd.DataFrame(rows)
