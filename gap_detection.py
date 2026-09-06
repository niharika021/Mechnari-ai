"""
Mechnari.ai - Gap Detection Agent
==================================
The question this module answers is the product:

    "Which failure modes has this company already proven on this kind of
     part, that the DFMEA on file for THIS part never analysed?"

It is a set difference, not a generation task:

    gaps(part) = applicable_modes(part) - analysed_modes(part)

where applicable_modes spans the part's own type and its family, so a
lesson only travels as far as it stays true.

Nothing here calls an LLM. Every finding is a row that either exists in the
knowledge base or does not, and every finding carries the 8D / warranty
record ids it came from, so an engineer can check it and an auditor can
trace it.

Severity is never invented either - it is read from the failure effect
registry, which is what lets the same effect carry the same severity on
every program.
"""

from typing import Optional

import pandas as pd

import data_layer

# Priority bands follow AIAG-VDA severity intent. Kept as a pure function of
# severity so a finding's priority can never drift between two runs.
PRIORITY_BANDS = [
    (9, "P1 - Safety / regulatory"),
    (7, "P2 - Loss of primary function"),
    (5, "P3 - Degraded function"),
    (0, "P4 - Nuisance"),
]


def priority_band(severity: int) -> str:
    for threshold, label in PRIORITY_BANDS:
        if severity >= threshold:
            return label
    return PRIORITY_BANDS[-1][1]


def _evidence_index() -> pd.DataFrame:
    """Per failure mode: the warranty record trail that proves it is real."""
    issues = data_layer.field_issues()
    grouped = issues.groupby("mode_id")
    evidence = pd.DataFrame({
        "reports": grouped.size(),
        "total_claims": grouped["claim_count"].sum(),
        "total_units": grouped["units_in_service"].sum(),
        "latest_report": grouped["report_date"].max(),
        "source_parts": grouped["part_id"].nunique(),
    })
    evidence["claims_per_1000"] = (
        evidence["total_claims"] / evidence["total_units"].replace(0, pd.NA) * 1000
    ).round(2)
    evidence["evidence_ids"] = grouped["issue_id"].apply(
        lambda ids: ", ".join(sorted(ids)[:4])
    )
    evidence["evidence_parts"] = grouped["part_id"].apply(
        lambda pids: ", ".join(sorted(set(pids)))
    )
    return evidence.reset_index()


def detect_gaps(part_id: Optional[str] = None) -> pd.DataFrame:
    """
    Failure modes known for a part's type that its DFMEA has not analysed.

    Pass a part_id for one part, or leave it out for the whole BOM.
    Returns an empty (but correctly shaped) frame when nothing is missing.
    """
    candidates = data_layer.applicable_modes()
    if part_id is not None:
        if part_id not in set(candidates["part_id"]):
            raise KeyError("Unknown part_id: %s" % part_id)
        candidates = candidates[candidates["part_id"] == part_id]

    analysed = data_layer.analysed_modes()
    evidence = _evidence_index()

    # ...minus the pairs the DFMEA on file already covers.
    covered = [
        mode_id in analysed.get(pid, ())
        for pid, mode_id in zip(candidates["part_id"], candidates["mode_id"])
    ]
    gaps = candidates[~pd.Series(covered, index=candidates.index)].copy()

    gaps = gaps.merge(evidence, on="mode_id", how="left")
    # A mode whose only evidence is this very part is not an outside lesson.
    gaps["reports"] = gaps["reports"].fillna(0).astype(int)
    gaps["total_claims"] = gaps["total_claims"].fillna(0).astype(int)
    gaps["source_parts"] = gaps["source_parts"].fillna(0).astype(int)
    gaps["claims_per_1000"] = gaps["claims_per_1000"].fillna(0.0)
    gaps["evidence_ids"] = gaps["evidence_ids"].fillna("no field record")
    gaps["evidence_parts"] = gaps["evidence_parts"].fillna("")

    gaps["priority"] = gaps["standard_severity"].apply(priority_band)
    gaps["learned_from"] = gaps.apply(
        lambda r: "%s (%s)" % (r["origin_part_name"], r["origin_part_id"]), axis=1
    )
    gaps["evidence_summary"] = gaps.apply(
        lambda r: (
            "%d warranty report(s), %d claims across %d part(s) - %s"
            % (r["reports"], r["total_claims"], r["source_parts"], r["evidence_ids"])
            if r["reports"] else "catalogued mode, no warranty record yet"
        ),
        axis=1,
    )

    columns = [
        "part_id", "item_reference", "system_package", "part_type_id", "part_type_name",
        "family_name", "scope_level",
        "mode_id", "failure_mode", "potential_cause",
        "effect_id", "effect_description", "standard_severity", "priority",
        "origin", "learned_from", "reports", "total_claims", "source_parts",
        "claims_per_1000", "latest_report", "evidence_ids", "evidence_parts",
        "evidence_summary", "typical_control", "recommended_action",
    ]
    gaps = gaps[columns].sort_values(
        by=["standard_severity", "total_claims", "part_id"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    return gaps


def gap_summary() -> pd.DataFrame:
    """One row per part: coverage and the worst thing it is missing."""
    coverage = data_layer.coverage_summary()
    gaps = detect_gaps()

    if gaps.empty:
        coverage["top_gap_severity"] = 0
        coverage["top_gap"] = ""
        return coverage

    worst = (
        gaps.sort_values("standard_severity", ascending=False)
        .groupby("part_id", as_index=False)
        .first()[["part_id", "standard_severity", "failure_mode"]]
        .rename(columns={
            "standard_severity": "top_gap_severity",
            "failure_mode": "top_gap",
        })
    )
    df = coverage.merge(worst, on="part_id", how="left")
    df["top_gap_severity"] = df["top_gap_severity"].fillna(0).astype(int)
    df["top_gap"] = df["top_gap"].fillna("")
    return df.sort_values(
        by=["top_gap_severity", "modes_not_analysed"], ascending=[False, False]
    ).reset_index(drop=True)


def severity_consistency_findings() -> pd.DataFrame:
    """
    Rows where the DFMEA on file scores an effect differently from the
    organization standard for that same effect.

    Severity is a property of the effect at a system level, so the same
    effect must carry the same severity on every program. Divergence is a
    standard audit finding and it is detectable with a join.
    """
    worksheet = data_layer.dfmea_worksheet()
    catalog = data_layer.failure_mode_catalog()
    parts = data_layer.parts()[["part_id", "item_reference", "system_package"]]

    df = worksheet.merge(
        catalog[["mode_id", "failure_mode", "effect_id", "effect_description",
                 "standard_severity"]],
        on="mode_id", how="left", validate="many_to_one",
    ).merge(parts, on="part_id", how="left")

    df["severity_delta"] = df["severity"] - df["standard_severity"]
    findings = df[df["severity_delta"] != 0].copy()
    findings["finding"] = findings["severity_delta"].apply(
        lambda d: "Under-scored by %d" % abs(d) if d < 0 else "Over-scored by %d" % d
    )
    return findings[[
        "part_id", "item_reference", "system_package", "mode_id", "failure_mode",
        "effect_id", "effect_description", "severity", "standard_severity",
        "severity_delta", "finding", "analyzed_by", "analysis_date",
    ]].sort_values(
        by=["severity_delta", "standard_severity"], ascending=[True, False]
    ).reset_index(drop=True)


def headline_metrics() -> dict:
    """Numbers for the dashboard, computed once."""
    gaps = detect_gaps()
    coverage = data_layer.coverage_summary()
    drift = severity_consistency_findings()
    return {
        "parts_analysed": int(len(coverage)),
        "modes_in_catalog": int(len(data_layer.failure_mode_catalog())),
        "total_gaps": int(len(gaps)),
        "parts_with_gaps": int(gaps["part_id"].nunique()) if not gaps.empty else 0,
        "safety_gaps": int((gaps["standard_severity"] >= 9).sum()) if not gaps.empty else 0,
        "gaps_with_evidence": int((gaps["reports"] > 0).sum()) if not gaps.empty else 0,
        "mean_coverage_pct": float(coverage["coverage_pct"].mean().round(1)),
        "severity_drift_rows": int(len(drift)),
    }


if __name__ == "__main__":
    metrics = headline_metrics()
    width = max(len(k) for k in metrics)
    for key, value in metrics.items():
        print("%-*s : %s" % (width, key, value))

    print("\nTop 10 unanalysed failure modes across the BOM")
    print("-" * 96)
    top = detect_gaps().head(10)
    for _, row in top.iterrows():
        print("%-12s %-34.34s S=%-2d %s" % (
            row["part_id"], row["failure_mode"], row["standard_severity"], row["priority"]))
        print("%-12s   learned from: %s" % ("", row["learned_from"]))
        print("%-12s   evidence: %s" % ("", row["evidence_summary"]))
