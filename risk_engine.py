"""
Mechnari.ai - Deterministic Risk Engine
========================================
Everything numeric in the platform lives here, and none of it touches a
model. Three jobs:

1. DERIVE OCCURRENCE FROM WARRANTY DATA, not from a workshop opinion.
   A DFMEA that scores Occurrence by asking the room what it remembers is
   the manual process with extra steps. Claims per 1000 units in service is
   a measured rate, and the AIAG occurrence anchors map that rate onto a
   1-10 score. Where the two disagree, the field data is the evidence and
   the workshop number is the claim.

2. SANITY-CHECK DETECTION AGAINST WHERE FAILURES ACTUALLY ESCAPED TO.
   If a mode reached a customer, the design control did not detect it, and
   a Detection score of 3 on that mode is not defensible.

3. RANK BY ACTION PRIORITY, NOT RPN.
   AIAG-VDA (2019) dropped RPN because multiplication misranks risk:
   S=9,O=2,D=2 gives 36 while S=4,O=3,D=4 gives 48, which says the
   safety-relevant failure matters less. AP is a lookup on the three scores
   in that order of importance. It is also more auditable than a product,
   because a lookup cannot be argued with.

   >>> READ BEFORE RELYING ON THE AP OUTPUT <<<
   AP_TABLE below reproduces the *structure* of the AIAG-VDA Action
   Priority table - the severity, occurrence and detection bands and the
   order they are read in. The individual cell values are a best-effort
   reconstruction and have NOT been verified against the handbook. Check
   them against your copy of AIAG-VDA FMEA (2019), Table AP, correct any
   cell that differs, and set AP_TABLE_VERIFIED = True. Until then the
   platform reports AP as provisional. RPN is retained alongside it as a
   legacy column so existing reviewers keep their familiar number.
"""

from typing import Optional

import pandas as pd

import data_layer

# =====================================================================
# OCCURRENCE: measured warranty rate -> 1-10 score
# =====================================================================
# AIAG occurrence anchors, expressed as incidents per 1000 units in
# service. Read as "a score of N means at least this rate". This is the one
# definition of the mapping - generate_csv_data.py imports it too, so the
# synthetic data and the engine can never drift apart.

OCCURRENCE_RATE_PER_1000 = {
    10: 120.0, 9: 55.0, 8: 22.0, 7: 11.0, 6: 5.0,
    5: 2.0, 4: 1.0, 3: 0.5, 2: 0.1, 1: 0.01,
}


def occurrence_from_rate(claims_per_1000: float) -> int:
    """Map a measured warranty rate onto the AIAG occurrence scale."""
    if claims_per_1000 is None or pd.isna(claims_per_1000) or claims_per_1000 <= 0:
        return 1
    for score in range(10, 0, -1):
        if claims_per_1000 >= OCCURRENCE_RATE_PER_1000[score]:
            return score
    return 1


def occurrence_from_claims(claims: float, units_in_service: float) -> int:
    if not units_in_service:
        return 1
    return occurrence_from_rate(claims / units_in_service * 1000.0)


# =====================================================================
# DETECTION: where the failure actually escaped to
# =====================================================================
# A design control that let a mode reach the customer did not detect it.
# The stage a failure was caught at puts a floor under a credible Detection
# score; anything below the floor is optimism, not evidence.

DETECTION_FLOOR_BY_STAGE = {
    "FIELD_CUSTOMER": 7,
    "DEALER_SERVICE": 5,
    "END_OF_LINE_TEST": 3,
    "VALIDATION_TEST": 2,
}


def detection_floor(stage: str) -> int:
    return DETECTION_FLOOR_BY_STAGE.get(stage, 1)


# =====================================================================
# ACTION PRIORITY (AIAG-VDA style)
# =====================================================================
# Bands are read severity first, then occurrence, then detection - the
# order that encodes "how badly it hurts" ahead of "how often" ahead of
# "would we catch it".

AP_TABLE_VERIFIED = False

SEVERITY_BANDS = [(9, "S9-10"), (7, "S7-8"), (4, "S4-6"), (2, "S2-3"), (1, "S1")]
OCCURRENCE_BANDS = [(8, "O8-10"), (6, "O6-7"), (4, "O4-5"), (2, "O2-3"), (1, "O1")]
DETECTION_BANDS = [(7, "D7-10"), (5, "D5-6"), (2, "D2-4"), (1, "D1")]

# (severity band, occurrence band) -> AP by detection band, in the order
# D7-10, D5-6, D2-4, D1.
AP_TABLE = {
    ("S9-10", "O8-10"): ("H", "H", "H", "H"),
    ("S9-10", "O6-7"):  ("H", "H", "H", "H"),
    ("S9-10", "O4-5"):  ("H", "H", "H", "M"),
    ("S9-10", "O2-3"):  ("H", "H", "M", "L"),
    ("S9-10", "O1"):    ("M", "M", "L", "L"),

    ("S7-8", "O8-10"):  ("H", "H", "H", "H"),
    ("S7-8", "O6-7"):   ("H", "H", "H", "M"),
    ("S7-8", "O4-5"):   ("H", "H", "M", "M"),
    ("S7-8", "O2-3"):   ("M", "M", "M", "L"),
    ("S7-8", "O1"):     ("L", "L", "L", "L"),

    ("S4-6", "O8-10"):  ("H", "H", "M", "M"),
    ("S4-6", "O6-7"):   ("M", "M", "M", "L"),
    ("S4-6", "O4-5"):   ("M", "M", "L", "L"),
    ("S4-6", "O2-3"):   ("L", "L", "L", "L"),
    ("S4-6", "O1"):     ("L", "L", "L", "L"),

    ("S2-3", "O8-10"):  ("M", "M", "L", "L"),
    ("S2-3", "O6-7"):   ("L", "L", "L", "L"),
    ("S2-3", "O4-5"):   ("L", "L", "L", "L"),
    ("S2-3", "O2-3"):   ("L", "L", "L", "L"),
    ("S2-3", "O1"):     ("L", "L", "L", "L"),
}

AP_LABELS = {"H": "H - High", "M": "M - Medium", "L": "L - Low"}


def _band(value: int, bands) -> str:
    for threshold, label in bands:
        if value >= threshold:
            return label
    return bands[-1][1]


def action_priority(severity: int, occurrence: int, detection: int) -> str:
    """
    AIAG-VDA style Action Priority: H, M or L.

    Severity 1 means no discernible effect, so it is always Low no matter
    what the other two scores say - that rule is the one part of the table
    that needs no lookup.
    """
    severity = max(1, min(10, int(severity)))
    occurrence = max(1, min(10, int(occurrence)))
    detection = max(1, min(10, int(detection)))

    if severity == 1:
        return "L"

    key = (_band(severity, SEVERITY_BANDS), _band(occurrence, OCCURRENCE_BANDS))
    detection_index = [label for _, label in DETECTION_BANDS].index(
        _band(detection, DETECTION_BANDS))
    return AP_TABLE[key][detection_index]


def rpn(severity: int, occurrence: int, detection: int) -> int:
    """Legacy RPN, kept for reviewers who still read it. Not used for ranking."""
    return int(severity) * int(occurrence) * int(detection)


# =====================================================================
# EVIDENCE AGGREGATION
# =====================================================================

def mode_evidence() -> pd.DataFrame:
    """Per failure mode: measured warranty rate and the escape stage."""
    issues = data_layer.field_issues()
    grouped = issues.groupby("mode_id")

    evidence = pd.DataFrame({
        "field_reports": grouped.size(),
        "field_claims": grouped["claim_count"].sum(),
        "field_units": grouped["units_in_service"].sum(),
        "latest_report": grouped["report_date"].max(),
        "worst_escape_stage": grouped["detection_stage"].apply(
            lambda stages: max(stages, key=detection_floor)),
        "evidence_ids": grouped["issue_id"].apply(lambda ids: ", ".join(sorted(ids)[:4])),
    }).reset_index()

    evidence["claims_per_1000"] = (
        evidence["field_claims"] / evidence["field_units"].replace(0, pd.NA) * 1000
    ).astype(float).round(2)
    evidence["derived_occurrence"] = evidence["claims_per_1000"].apply(occurrence_from_rate)
    evidence["detection_floor"] = evidence["worst_escape_stage"].apply(detection_floor)
    return evidence


def mode_evidence_parts() -> dict:
    """mode_id -> the parts that actually generated warranty records for it."""
    issues = data_layer.field_issues()
    return {
        mode_id: set(group["part_id"])
        for mode_id, group in issues.groupby("mode_id", sort=False)
    }


# =====================================================================
# SCORING THE DFMEA ON FILE
# =====================================================================

def scored_worksheet(part_id: Optional[str] = None) -> pd.DataFrame:
    """
    The DFMEA on file, rescored against evidence.

    Severity comes from the effect registry, Occurrence from warranty data
    where any exists, Detection from the worksheet with the escape-stage
    floor alongside it. AP is computed from the evidence-based scores; the
    as-filed AP is kept next to it so the change is visible.
    """
    worksheet = data_layer.dfmea_worksheet()
    catalog = data_layer.failure_mode_catalog()
    parts = data_layer.parts()[["part_id", "item_reference", "system_package",
                                "part_type_name"]]

    df = worksheet.merge(
        catalog[["mode_id", "failure_mode", "potential_cause", "effect_id",
                 "effect_description", "standard_severity", "recommended_action"]],
        on="mode_id", how="left", validate="many_to_one",
    ).merge(parts, on="part_id", how="left")

    if part_id is not None:
        if part_id not in set(df["part_id"]):
            raise KeyError("Unknown part_id: %s" % part_id)
        df = df[df["part_id"] == part_id].copy()

    df = df.merge(mode_evidence(), on="mode_id", how="left")
    df["field_reports"] = df["field_reports"].fillna(0).astype(int)
    df["field_claims"] = df["field_claims"].fillna(0).astype(int)
    df["claims_per_1000"] = df["claims_per_1000"].fillna(0.0)
    df["evidence_ids"] = df["evidence_ids"].fillna("no field record")
    df["worst_escape_stage"] = df["worst_escape_stage"].fillna("NO_RECORD")
    df["detection_floor"] = df["detection_floor"].fillna(1).astype(int)

    # Where there is no warranty record, the workshop estimate is all we
    # have and it stands. Evidence overrides opinion, absence does not.
    df["has_evidence"] = df["field_reports"] > 0

    # A rate measured on THIS part is direct evidence. A rate measured on
    # sibling parts of the same type is a prior, not a measurement, and
    # saying so is the difference between a finding an engineer trusts and
    # one they stop reading.
    parts_with_records = mode_evidence_parts()
    df["evidence_scope"] = [
        "OWN_PART" if pid in parts_with_records.get(mid, ()) else "TYPE_HISTORY"
        for pid, mid in zip(df["part_id"], df["mode_id"])
    ]
    df["derived_occurrence"] = df["derived_occurrence"].fillna(df["occurrence"]).astype(int)
    df["evidence_occurrence"] = df["derived_occurrence"].where(
        df["has_evidence"], df["occurrence"]).astype(int)

    df["severity_as_filed"] = df["severity"]
    df["severity_standard"] = df["standard_severity"].astype(int)

    df["ap_as_filed"] = [
        action_priority(s, o, d)
        for s, o, d in zip(df["severity_as_filed"], df["occurrence"], df["detection"])
    ]
    df["ap_evidence_based"] = [
        action_priority(s, o, d)
        for s, o, d in zip(df["severity_standard"], df["evidence_occurrence"], df["detection"])
    ]
    df["rpn_legacy"] = [
        rpn(s, o, d)
        for s, o, d in zip(df["severity_standard"], df["evidence_occurrence"], df["detection"])
    ]
    df["ap_changed"] = df["ap_as_filed"] != df["ap_evidence_based"]
    return df.reset_index(drop=True)


# =====================================================================
# FINDINGS
# =====================================================================

def occurrence_findings(min_delta: int = 1) -> pd.DataFrame:
    """
    Rows where the warranty record does not support the Occurrence on file.

    Understated is the finding that matters: the DFMEA says this rarely
    happens and the claims say otherwise.
    """
    df = scored_worksheet()
    df = df[df["has_evidence"]].copy()
    df["occurrence_delta"] = df["derived_occurrence"] - df["occurrence"]
    findings = df[df["occurrence_delta"].abs() >= min_delta].copy()
    findings["finding"] = findings["occurrence_delta"].apply(
        lambda d: "Understated by %d" % d if d > 0 else "Overstated by %d" % abs(d)
    )
    return findings[[
        "part_id", "item_reference", "system_package", "mode_id", "failure_mode",
        "occurrence", "derived_occurrence", "occurrence_delta", "finding",
        "evidence_scope", "field_reports", "field_claims", "field_units",
        "claims_per_1000", "evidence_ids", "ap_as_filed", "ap_evidence_based",
    ]].sort_values(
        by=["evidence_scope", "occurrence_delta", "claims_per_1000"],
        ascending=[True, False, False],
    ).reset_index(drop=True)


def detection_findings() -> pd.DataFrame:
    """Rows scoring Detection better than the escape stage can justify."""
    df = scored_worksheet()
    df = df[df["has_evidence"]].copy()
    findings = df[df["detection"] < df["detection_floor"]].copy()
    findings["detection_delta"] = findings["detection_floor"] - findings["detection"]
    findings["finding"] = findings.apply(
        lambda r: "Scored D=%d but escaped to %s" % (
            r["detection"], r["worst_escape_stage"].replace("_", " ").title()),
        axis=1,
    )
    return findings[[
        "part_id", "item_reference", "system_package", "mode_id", "failure_mode",
        "detection", "detection_floor", "detection_delta", "worst_escape_stage",
        "finding", "evidence_scope", "evidence_ids",
    ]].sort_values(
        by=["detection_delta", "part_id"], ascending=[False, True]
    ).reset_index(drop=True)


def ap_change_findings() -> pd.DataFrame:
    """Rows whose Action Priority moves once evidence replaces opinion."""
    df = scored_worksheet()
    changed = df[df["ap_changed"]].copy()
    rank = {"H": 3, "M": 2, "L": 1}
    changed["direction"] = changed.apply(
        lambda r: "Escalates" if rank[r["ap_evidence_based"]] > rank[r["ap_as_filed"]]
        else "De-escalates", axis=1)
    return changed[[
        "part_id", "item_reference", "system_package", "mode_id", "failure_mode",
        "severity_as_filed", "severity_standard", "occurrence", "derived_occurrence",
        "detection", "ap_as_filed", "ap_evidence_based", "direction",
        "rpn_legacy", "evidence_ids",
    ]].sort_values(by=["direction", "severity_standard"], ascending=[True, False]
                   ).reset_index(drop=True)


def headline_metrics() -> dict:
    df = scored_worksheet()
    occurrence = occurrence_findings()
    detection = detection_findings()
    own = occurrence[occurrence["evidence_scope"] == "OWN_PART"]
    return {
        "worksheet_rows": int(len(df)),
        "rows_measured_on_own_part": int((df["evidence_scope"] == "OWN_PART").sum()),
        "occurrence_understated": int((occurrence["occurrence_delta"] > 0).sum()),
        "occurrence_understated_own_part": int((own["occurrence_delta"] > 0).sum()),
        "occurrence_overstated": int((occurrence["occurrence_delta"] < 0).sum()),
        "detection_optimistic": int(len(detection)),
        "ap_high_as_filed": int((df["ap_as_filed"] == "H").sum()),
        "ap_high_evidence_based": int((df["ap_evidence_based"] == "H").sum()),
        "ap_escalations": int(len(df[df["ap_changed"]])),
        "ap_table_verified": AP_TABLE_VERIFIED,
    }


if __name__ == "__main__":
    metrics = headline_metrics()
    width = max(len(k) for k in metrics)
    for key, value in metrics.items():
        print("%-*s : %s" % (width, key, value))

    if not AP_TABLE_VERIFIED:
        print("\nNOTE: AP cell values are provisional - verify against AIAG-VDA "
              "FMEA (2019) Table AP, then set AP_TABLE_VERIFIED = True.")

    print("\nOccurrence understated, measured on the part itself (top 10)")
    print("-" * 100)
    findings = occurrence_findings()
    own = findings[(findings["evidence_scope"] == "OWN_PART")
                   & (findings["occurrence_delta"] > 0)]
    for _, row in own.head(10).iterrows():
        print("%-12s %-38.38s O filed=%d  O from claims=%d  (%.1f per 1000, %d claims)" % (
            row["part_id"], row["failure_mode"], row["occurrence"],
            row["derived_occurrence"], row["claims_per_1000"], row["field_claims"]))
