"""
Mechnari.ai - the standards floor
=================================
Generic engineering failure modes, proposed when the company's own history
has nothing to say about a part.

Why this is a separate module and not rows in failure_mode_catalog
-------------------------------------------------------------------
A mode in `failure_mode_catalog` is institutional memory: this company
built a part like this, and this is how it failed. `gap_detection` reads
that table and calls an unanalysed mode a **gap** - "you already knew
about this and did not check it."

A generic mode carries no such claim. Nobody here learned it; it is
baseline engineering practice. Calling it a gap would be false, and
putting it in the catalog would silently change every headline figure in
the product: 127 gaps, 57.3% mean coverage and the whole backtest are
computed from `applicable_modes()`, which unions TYPE and FAMILY scopes
out of that one table.

So these live here, are never loaded by `data_layer`, never reach
`gap_detection`, and never enter the backtest. They are a *proposal
source of last resort* and nothing else.

What is still not invented
--------------------------
Severity. Every mode below maps to an `effect_id` in the organisation's
own registry (`failure_effects`), so Severity comes from the same single
source it always does. A standards row cannot introduce a severity the
organisation has not already standardised.

Occurrence is 1 - the floor - because there is by definition no measured
rate. Detection is the authored baseline below. Both are visibly marked:
`evidence_ids` reads "no field record - standards baseline", and
`scope_level` is `STANDARD` rather than TYPE or FAMILY, so a reviewer can
see at a glance which rows rest on evidence and which rest on practice.

Selection is deliberately coarse
--------------------------------
Modes are grouped into categories matched by keyword against the
engineer's description. This is not retrieval and does not pretend to be:
it is a keyword gate whose only job is to avoid proposing refrigerant
release for a mounting bracket. The universal set is always included.

An earlier version of this product's inheritance was too broad and
produced a finding telling an engineer to check a wire conduit for
park-brake binding. That is the failure this gate exists to prevent, and
it is why the categories are narrow and the universal set is short.
"""

from typing import Any, Dict, List

import pandas as pd

import data_layer
import risk_engine

# ---------------------------------------------------------------------
# NOT YET REVIEWED BY A DOMAIN ENGINEER.
#
# The modes below, their effect mappings and their baseline detection
# values were authored as a starting point, not taken from a published
# standard. They follow the same convention as risk_engine.AP_TABLE:
# the platform says so wherever it uses them, rather than presenting
# them as authoritative.
#
# To lift the label: review each mode against your own engineering
# practice, correct the effect mapping and baseline detection, and set
# this to True.
# ---------------------------------------------------------------------
STANDARDS_REVIEWED = False

# Below this retrieval similarity, the corpus does not really contain
# anything like the part being described, and the standards floor is
# added underneath whatever was retrieved.
#
# 0.25 is measured, not guessed. Against the shipped knowledge base:
#
#   paraphrased in-domain parts   0.313 - 0.489
#     ("diesel return hose", "coolant bypass tube", "brake line for
#      rear axle", "mounting bracket for fuel filter")
#   genuinely out-of-domain       0.100 - 0.161
#     ("operator seat cushion", "cab door glass", "rear view mirror arm")
#
# The gap between 0.161 and 0.313 is wide enough to sit a threshold in.
#
# Similarity rather than retrieval's own `confident` flag, which is the
# wrong signal for this: it is a measure of whether the neighbours AGREE
# on a type, not of whether any of them resemble the part. A rear view
# mirror arm comes back confident=True (the neighbours agree it is a
# bracket) while a correctly-identified hydraulic steering line comes
# back confident=False (its neighbours split across two hose types).
# Keyed on confidence, the floor would appear for the part that needs it
# least and be absent for the one that needs it most.
STANDARDS_SIMILARITY_FLOOR = 0.25

# Keywords are matched against the lowercased description + function +
# material. A part matches a category if any keyword appears.
CATEGORY_KEYWORDS = {
    "fluid": [
        "hose", "line", "tube", "pipe", "fitting", "coupling", "valve",
        "pump", "coolant", "fuel", "hydraulic", "oil", "pneumatic",
        "brake", "refrigerant", "fluid", "circuit",
    ],
    "electrical": [
        "wire", "harness", "connector", "sensor", "solenoid", "electrical",
        "conduit", "cable", "loom", "terminal", "signal",
    ],
    "sealing": [
        "seal", "boot", "grommet", "gasket", "o-ring", "cover", "housing",
        "enclosure",
    ],
    "structural": [
        "bracket", "mount", "plate", "frame", "support", "clamp", "bar",
        "arm", "housing", "casting",
    ],
}

# scope_id is cosmetic here - these attach to no type and no family.
STANDARD_MODES: List[Dict[str, Any]] = [
    # --- Universal: proposed for any part -----------------------------
    {
        "mode_id": "STD-FATIGUE",
        "category": "universal",
        "failure_mode": "Fatigue cracking under cyclic load",
        "potential_cause": "Cyclic stress over design life exceeding the endurance limit of the section",
        "effect_id": "EF-15",
        "typical_control": "Design review against duty cycle; durability sign-off",
        "baseline_detection": 6,
        "recommended_action": "Confirm the duty cycle and run a durability test to the intended service life.",
    },
    {
        "mode_id": "STD-CORROSION",
        "category": "universal",
        "failure_mode": "Corrosion or surface degradation from environmental exposure",
        "potential_cause": "Moisture, salt, agricultural chemicals or UV attacking the surface over time",
        "effect_id": "EF-15",
        "typical_control": "Material and coating selection review",
        "baseline_detection": 7,
        "recommended_action": "Confirm the coating or material suits the field environment; consider salt-spray validation.",
    },
    {
        "mode_id": "STD-WEAR",
        "category": "universal",
        "failure_mode": "Wear-through from relative motion or chafing against adjacent parts",
        "potential_cause": "Contact with a neighbouring component under vibration, with no protection at the contact point",
        "effect_id": "EF-15",
        "typical_control": "Packaging and clearance review",
        "baseline_detection": 6,
        "recommended_action": "Check clearance to neighbouring parts through the full motion envelope; add protection at any contact point.",
    },
    {
        "mode_id": "STD-FASTENER",
        "category": "universal",
        "failure_mode": "Loss of clamping force at the mounting under vibration",
        "potential_cause": "Joint relaxation or fastener loosening from machine vibration",
        "effect_id": "EF-15",
        "typical_control": "Torque specification and joint design review",
        "baseline_detection": 5,
        "recommended_action": "Confirm the torque specification and retention method against the vibration input.",
    },
    {
        "mode_id": "STD-MFG-VAR",
        "category": "universal",
        "failure_mode": "Dimensional or material variation outside drawing tolerance",
        "potential_cause": "Supplier process variation not held to the specified tolerance",
        "effect_id": "EF-15",
        "typical_control": "Drawing tolerance review; supplier PPAP",
        "baseline_detection": 4,
        "recommended_action": "Confirm the critical characteristics are identified on the drawing and covered by the supplier's control plan.",
    },

    # --- Fluid-carrying -----------------------------------------------
    {
        "mode_id": "STD-LEAK-EXT",
        "category": "fluid",
        "failure_mode": "External leak at a joint, seal or wall",
        "potential_cause": "Joint relaxation, seal degradation or wall permeation under pressure and temperature cycling",
        "effect_id": "EF-02",
        "typical_control": "Pressure and leak test",
        "baseline_detection": 4,
        "recommended_action": "Pressure-test to the maximum working pressure across the temperature range.",
    },
    {
        "mode_id": "STD-RESTRICT",
        "category": "fluid",
        "failure_mode": "Internal restriction or blockage reducing flow",
        "potential_cause": "Collapse, kinking, deposit build-up or debris at a restriction",
        "effect_id": "EF-05",
        "typical_control": "Flow test; routing bend-radius review",
        "baseline_detection": 4,
        "recommended_action": "Verify minimum bend radius on the routing and flow-test at the design condition.",
    },
    {
        "mode_id": "STD-CONTAM",
        "category": "fluid",
        "failure_mode": "Particulate contamination released into the circuit",
        "potential_cause": "Internal degradation, manufacturing debris or wear particles entering the fluid",
        "effect_id": "EF-08",
        "typical_control": "Cleanliness specification and validation",
        "baseline_detection": 6,
        "recommended_action": "Set a cleanliness specification for the part and confirm it on incoming parts.",
    },

    # --- Electrical ---------------------------------------------------
    {
        "mode_id": "STD-INSUL",
        "category": "electrical",
        "failure_mode": "Insulation breakdown or short to ground",
        "potential_cause": "Insulation damage from abrasion, heat or moisture ingress at a termination",
        "effect_id": "EF-09",
        "typical_control": "Dielectric test; routing and protection review",
        "baseline_detection": 5,
        "recommended_action": "Confirm insulation rating against the local thermal environment and protect the run where it passes hot or sharp features.",
    },
    {
        "mode_id": "STD-SIGNAL",
        "category": "electrical",
        "failure_mode": "Intermittent or degraded signal at the connector",
        "potential_cause": "Contact fretting, corrosion or partial seating at the connector interface",
        "effect_id": "EF-16",
        "typical_control": "Connector selection and retention review",
        "baseline_detection": 6,
        "recommended_action": "Confirm the connector is sealed and positively retained; include a vibration-with-signal-monitoring test.",
    },

    # --- Sealing / enclosure ------------------------------------------
    {
        "mode_id": "STD-INGRESS",
        "category": "sealing",
        "failure_mode": "Water or dust ingress past the seal",
        "potential_cause": "Seal compression set, installation damage or an inadequate sealing surface",
        "effect_id": "EF-13",
        "typical_control": "Ingress-protection test to the required rating",
        "baseline_detection": 4,
        "recommended_action": "Confirm the required IP rating and validate it after a thermal and vibration soak.",
    },

    # --- Structural ---------------------------------------------------
    {
        "mode_id": "STD-DEFLECT",
        "category": "structural",
        "failure_mode": "Excessive deflection or loss of position under load",
        "potential_cause": "Section stiffness insufficient for the applied load case",
        "effect_id": "EF-15",
        "typical_control": "Structural analysis against the load case",
        "baseline_detection": 3,
        "recommended_action": "Analyse against the worst-case load and confirm the deflection stays inside the functional limit.",
    },
]


def categories_for(description: str) -> List[str]:
    """The standards categories a free-text description matches.

    Always includes "universal". Matching is substring, lowercased, and
    intentionally simple - see the module docstring.
    """
    text = (description or "").lower()
    matched = ["universal"]
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            matched.append(category)
    return matched


def candidate_standard_modes(description: str) -> pd.DataFrame:
    """Standard modes for a description, in the shape retrieval returns.

    Same columns as `retrieval.candidate_failure_modes`, so `dfmea_sheet`
    builds a row from either without knowing which it has.
    """
    categories = set(categories_for(description))
    selected = [m for m in STANDARD_MODES if m["category"] in categories]
    if not selected:
        return pd.DataFrame()

    effects = data_layer.failure_effects()
    severity_by_effect = dict(
        zip(effects["effect_id"], effects["standard_severity"])
    )
    description_by_effect = dict(
        zip(effects["effect_id"], effects["effect_description"])
    )
    level_by_effect = dict(zip(effects["effect_id"], effects["system_level"]))

    rows = []
    for mode in selected:
        effect_id = mode["effect_id"]
        severity = int(severity_by_effect[effect_id])
        # No measured rate exists, by definition. occurrence_from_rate(0)
        # is the floor rather than a hardcoded 1, so the scale stays owned
        # by risk_engine.
        occurrence = risk_engine.occurrence_from_rate(0)
        detection = int(mode["baseline_detection"])
        rows.append({
            "mode_id": mode["mode_id"],
            "scope_id": "STANDARD",
            "scope_level": "STANDARD",
            "failure_mode": mode["failure_mode"],
            "potential_cause": mode["potential_cause"],
            "effect_id": effect_id,
            "effect_description": description_by_effect[effect_id],
            "system_level": level_by_effect[effect_id],
            "typical_control": mode["typical_control"],
            "baseline_detection": detection,
            "recommended_action": mode["recommended_action"],
            "severity": severity,
            "occurrence": occurrence,
            "detection": detection,
            "action_priority": risk_engine.action_priority(
                severity, occurrence, detection),
            "rpn_legacy": risk_engine.rpn(severity, occurrence, detection),
            "field_reports": 0,
            "field_claims": 0,
            "claims_per_1000": 0.0,
            "evidence_ids": "no field record - standards baseline",
            "learned_from": "generic engineering practice, not this company's history",
            "worst_escape_stage": "",
            "origin": "STANDARD",
            "origin_part_id": "",
            "origin_part_name": "",
        })

    frame = pd.DataFrame(rows)
    return frame.sort_values(
        by=["severity", "detection"], ascending=[False, False]
    ).reset_index(drop=True)
