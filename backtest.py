"""
Mechnari.ai - Backtest Harness
===============================
The question a pilot customer actually asks: would this have caught anything
we missed?

Answering it with the whole knowledge base loaded is cheating, because every
mode in the catalogue was written from a failure that has already happened.
So the harness cuts the history at a date and only lets the system know what
was known then:

    train : every warranty record reported BEFORE the cutoff
    test  : every warranty record reported ON OR AFTER it

For each incident in the test window it asks two questions about part P and
the mode M that failed:

    would Mechnari have flagged M for P?   - was M in P's applicable set,
                                             and had anything reported it
                                             before the cutoff?
    did the DFMEA on file cover M for P?   - the manual baseline

The gap between those two is the product's claim, stated as a number rather
than a promise.

Three honesty rules the harness follows:

1. A mode with no pre-cutoff record anywhere is counted as UNKNOWABLE, not
   as a miss the system should be blamed for and not as a success. Nobody
   could have flagged it. Reporting this separately is what stops the
   headline number being quietly inflated.

2. Incidents where the mode was only ever seen on P itself are reported
   apart from those learned on a DIFFERENT part. Only the second kind
   supports the institutional-memory claim; flagging a mode a part is
   already famous for proves nothing.

3. Results are reported claim-weighted as well as incident-weighted. One 8D
   covering 187 claims is not the same size of miss as one covering 3, and
   the warranty ledger is what a plant manager is actually looking at.

The cold-start backtest answers the other half: for a part treated as brand
new - hidden from the corpus, no DFMEA, no history of its own - would
retrieval from its description alone have surfaced the mode that really
failed on it?
"""

from typing import Any, Dict, List, Optional

import pandas as pd

import data_layer
import retrieval

DEFAULT_CUTOFF = "2023-07-01"
CUTOFF_SWEEP = ["2022-07-01", "2023-01-01", "2023-07-01", "2024-01-01", "2024-07-01"]


def _applicable_by_part() -> Dict[str, set]:
    applicable = data_layer.applicable_modes()
    return {
        part_id: set(group["mode_id"])
        for part_id, group in applicable.groupby("part_id", sort=False)
    }


def temporal_backtest(cutoff: str = DEFAULT_CUTOFF) -> Dict[str, Any]:
    """
    Hold out everything reported on or after `cutoff` and ask what the system
    would have flagged beforehand.
    """
    cutoff_ts = pd.Timestamp(cutoff)
    issues = data_layer.field_issues()

    train = issues[issues["report_date"] < cutoff_ts]
    test = issues[issues["report_date"] >= cutoff_ts]

    # What the company had actually seen by the cutoff, and where.
    known_modes = set(train["mode_id"])
    parts_seen_per_mode: Dict[str, set] = {
        mode_id: set(group["part_id"])
        for mode_id, group in train.groupby("mode_id", sort=False)
    }

    applicable = _applicable_by_part()
    analysed = data_layer.analysed_modes()
    catalog = data_layer.failure_mode_catalog().set_index("mode_id")

    rows: List[Dict[str, Any]] = []
    for _, incident in test.iterrows():
        part_id = incident["part_id"]
        mode_id = incident["mode_id"]

        # Retired parts are not in the active BOM and have no DFMEA to judge.
        if part_id not in applicable:
            continue

        knowable = mode_id in known_modes
        seen_on = parts_seen_per_mode.get(mode_id, set())
        learned_elsewhere = bool(seen_on - {part_id})

        flagged = knowable and mode_id in applicable[part_id]
        covered = mode_id in analysed.get(part_id, set())

        rows.append({
            "issue_id": incident["issue_id"],
            "report_date": incident["report_date"],
            "part_id": part_id,
            "mode_id": mode_id,
            "failure_mode": catalog.loc[mode_id, "failure_mode"]
            if mode_id in catalog.index else mode_id,
            "severity": int(incident["observed_severity"]),
            "claims": int(incident["claim_count"]),
            "knowable_at_cutoff": knowable,
            "learned_on_another_part": learned_elsewhere,
            "mechnari_would_flag": flagged,
            "dfmea_on_file_covered": covered,
            "newly_caught": bool(flagged and not covered),
        })

    detail = pd.DataFrame(rows)
    summary = _summarise(detail, cutoff)
    return {"cutoff": cutoff, "summary": summary, "detail": detail,
            "train_records": int(len(train)), "test_records": int(len(test))}


def _summarise(detail: pd.DataFrame, cutoff: str) -> Dict[str, Any]:
    if detail.empty:
        return {
            "cutoff": cutoff, "incidents": 0, "claims": 0,
            "knowable": 0, "unknowable": 0,
            "dfmea_recall": 0.0, "mechnari_recall": 0.0,
            "dfmea_recall_claim_weighted": 0.0,
            "mechnari_recall_claim_weighted": 0.0,
            "newly_caught": 0, "newly_caught_claims": 0,
            "newly_caught_cross_part": 0, "newly_caught_safety": 0,
        }

    total = len(detail)
    claims = int(detail["claims"].sum())
    knowable = detail[detail["knowable_at_cutoff"]]
    newly = detail[detail["newly_caught"]]

    def share(mask_sum, denominator):
        return round(float(mask_sum) / denominator, 3) if denominator else 0.0

    return {
        "cutoff": cutoff,
        "incidents": total,
        "claims": claims,
        # Knowable incidents are the fair denominator for a recall claim: a
        # mode nothing had reported yet was not there to be found.
        "knowable": int(len(knowable)),
        "unknowable": int(total - len(knowable)),
        # Numerator and denominator both restricted to knowable incidents.
        "dfmea_recall": share(knowable["dfmea_on_file_covered"].sum(), len(knowable)),
        "mechnari_recall": share(knowable["mechnari_would_flag"].sum(), len(knowable)),
        "dfmea_recall_claim_weighted": share(
            knowable.loc[knowable["dfmea_on_file_covered"], "claims"].sum(),
            knowable["claims"].sum()),
        "mechnari_recall_claim_weighted": share(
            knowable.loc[knowable["mechnari_would_flag"], "claims"].sum(),
            knowable["claims"].sum()),
        "newly_caught": int(len(newly)),
        "newly_caught_claims": int(newly["claims"].sum()),
        "newly_caught_cross_part": int(newly["learned_on_another_part"].sum()),
        "newly_caught_safety": int((newly["severity"] >= 9).sum()),
    }


def sweep(cutoffs: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Run the backtest at several cutoffs.

    One cutoff is a data point; a curve is evidence. If the result only holds
    at one date, it is an artefact of that date.
    """
    rows = [temporal_backtest(cutoff)["summary"] for cutoff in (cutoffs or CUTOFF_SWEEP)]
    return pd.DataFrame(rows)


def cold_start_backtest(top_k: int = retrieval.DEFAULT_TOP_K) -> Dict[str, Any]:
    """
    Treat each part as brand new and see whether retrieval alone would have
    surfaced the mode that actually failed on it.

    The part is hidden from the corpus, so the proposal is built purely from
    its description and the other 49 parts - no DFMEA, no history of its own.
    This is the "never seen this part before" claim, measured.
    """
    parts = data_layer.parts()
    issues = data_layer.field_issues()
    catalog = data_layer.failure_mode_catalog()

    modes_by_scope: Dict[str, set] = {}
    for _, row in catalog.iterrows():
        modes_by_scope.setdefault(row["scope_id"], set()).add(row["mode_id"])

    failed_modes: Dict[str, set] = {
        part_id: set(group["mode_id"])
        for part_id, group in issues.groupby("part_id", sort=False)
    }

    rows: List[Dict[str, Any]] = []
    for _, part in parts.iterrows():
        actual = failed_modes.get(part["part_id"], set())
        if not actual:
            continue

        query = retrieval.describe(
            part["item_reference"], part["elementary_function"], part["material_type"])
        inference = retrieval.infer_part_type(
            query, top_k=top_k, exclude_part_id=part["part_id"])

        proposed: set = set()
        for candidate in inference["candidate_types"]:
            proposed |= modes_by_scope.get(candidate["part_type_id"], set())
            proposed |= modes_by_scope.get(candidate["family_id"], set())

        hits = actual & proposed
        rows.append({
            "part_id": part["part_id"],
            "component": part["item_reference"],
            "true_type": part["part_type_name"],
            "suggested_type": inference["part_type_name"],
            "modes_that_failed": len(actual),
            "modes_surfaced": len(hits),
            "recall": round(len(hits) / len(actual), 3),
            "proposed_count": len(proposed),
        })

    detail = pd.DataFrame(rows)
    total_actual = int(detail["modes_that_failed"].sum())
    total_hits = int(detail["modes_surfaced"].sum())
    return {
        "parts_evaluated": int(len(detail)),
        "failure_modes_evaluated": total_actual,
        "modes_surfaced": total_hits,
        "recall": round(total_hits / total_actual, 3) if total_actual else 0.0,
        "parts_fully_covered": int((detail["recall"] == 1.0).sum()),
        "parts_missed_entirely": int((detail["recall"] == 0.0).sum()),
        "mean_proposed": round(float(detail["proposed_count"].mean()), 1),
        "detail": detail,
    }


def headline() -> Dict[str, Any]:
    """The two numbers to quote, plus the caveats that keep them honest."""
    temporal = temporal_backtest()
    cold = cold_start_backtest()
    summary = temporal["summary"]
    return {
        "cutoff": summary["cutoff"],
        "incidents_after_cutoff": summary["incidents"],
        "unknowable_at_cutoff": summary["unknowable"],
        "dfmea_recall": summary["dfmea_recall"],
        "mechnari_recall": summary["mechnari_recall"],
        "dfmea_recall_claim_weighted": summary["dfmea_recall_claim_weighted"],
        "mechnari_recall_claim_weighted": summary["mechnari_recall_claim_weighted"],
        "newly_caught": summary["newly_caught"],
        "newly_caught_claims": summary["newly_caught_claims"],
        "newly_caught_safety": summary["newly_caught_safety"],
        "cold_start_recall": cold["recall"],
        "cold_start_modes": cold["failure_modes_evaluated"],
    }


if __name__ == "__main__":
    result = temporal_backtest()
    s = result["summary"]

    print("Temporal backtest - knowledge cut at %s" % s["cutoff"])
    print("  %d warranty records before the cutoff, %d after"
          % (result["train_records"], result["test_records"]))
    print("  %d incidents on active parts in the test window (%d claims)"
          % (s["incidents"], s["claims"]))
    print("  %d of those were unknowable - nothing had reported that mode yet"
          % s["unknowable"])
    print()
    print("  Of the %d knowable incidents:" % s["knowable"])
    print("    DFMEA on file covered the mode : %5.0f%%   (claim-weighted %.0f%%)"
          % (s["dfmea_recall"] * 100, s["dfmea_recall_claim_weighted"] * 100))
    print("    Mechnari would have flagged it : %5.0f%%   (claim-weighted %.0f%%)"
          % (s["mechnari_recall"] * 100, s["mechnari_recall_claim_weighted"] * 100))
    print()
    print("  Newly caught: %d incidents the DFMEA missed and Mechnari flags"
          % s["newly_caught"])
    print("    covering %d warranty claims" % s["newly_caught_claims"])
    print("    %d of them learned on a different part" % s["newly_caught_cross_part"])
    print("    %d of them at severity 9 or above" % s["newly_caught_safety"])

    print("\nCutoff sweep - one date is a data point, a curve is evidence")
    print("-" * 78)
    print("%-12s %9s %9s %11s %11s %8s" % (
        "cutoff", "incidents", "knowable", "DFMEA", "Mechnari", "newly"))
    for _, row in sweep().iterrows():
        print("%-12s %9d %9d %10.0f%% %10.0f%% %8d" % (
            row["cutoff"], row["incidents"], row["knowable"],
            row["dfmea_recall"] * 100, row["mechnari_recall"] * 100,
            row["newly_caught"]))

    cold = cold_start_backtest()
    print("\nCold-start backtest - every part treated as never seen before")
    print("-" * 78)
    print("  %d parts, %d modes that actually failed" % (
        cold["parts_evaluated"], cold["failure_modes_evaluated"]))
    print("  surfaced from the description alone : %.0f%% (%d of %d)" % (
        cold["recall"] * 100, cold["modes_surfaced"], cold["failure_modes_evaluated"]))
    print("  parts where every failed mode was surfaced : %d" % cold["parts_fully_covered"])
    print("  parts where none was                       : %d" % cold["parts_missed_entirely"])
