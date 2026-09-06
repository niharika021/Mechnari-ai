"""
Invariants for the backtest harness.

Run with:  python test_backtest.py     (or: pytest test_backtest.py)

A backtest is the one component whose bugs flatter you, so these check the
arithmetic that could inflate a headline number: that no future information
leaks across the cutoff, that recall shares stay in range, that the fair
denominator is used, and that the measurement is still capable of failing.
"""

import sys

import pandas as pd

import backtest
import data_layer


def test_the_cutoff_actually_splits_the_history():
    result = backtest.temporal_backtest("2023-07-01")
    issues = data_layer.field_issues()
    cutoff = pd.Timestamp("2023-07-01")
    assert result["train_records"] == int((issues["report_date"] < cutoff).sum())
    assert result["test_records"] == int((issues["report_date"] >= cutoff).sum())
    assert result["train_records"] and result["test_records"]


def test_no_incident_in_the_test_window_predates_the_cutoff():
    """A leak here would let the system 'predict' what it had already read."""
    result = backtest.temporal_backtest("2023-07-01")
    detail = result["detail"]
    assert (detail["report_date"] >= pd.Timestamp("2023-07-01")).all()


def test_a_mode_is_only_flagged_if_something_reported_it_first():
    """The core no-lookahead rule: unknowable modes are never counted as flagged."""
    result = backtest.temporal_backtest("2023-07-01")
    detail = result["detail"]
    unknowable = detail[~detail["knowable_at_cutoff"]]
    assert not unknowable["mechnari_would_flag"].any()


def test_recall_uses_the_knowable_denominator():
    result = backtest.temporal_backtest("2023-07-01")
    detail, summary = result["detail"], result["summary"]
    knowable = detail[detail["knowable_at_cutoff"]]
    expected = knowable["dfmea_on_file_covered"].sum() / len(knowable)
    assert abs(summary["dfmea_recall"] - expected) < 0.002


def test_every_share_is_a_share():
    """The bug this catches produced a DFMEA recall of 185%."""
    for cutoff in backtest.CUTOFF_SWEEP:
        summary = backtest.temporal_backtest(cutoff)["summary"]
        for key in ["dfmea_recall", "mechnari_recall",
                    "dfmea_recall_claim_weighted", "mechnari_recall_claim_weighted"]:
            assert 0.0 <= summary[key] <= 1.0, "%s = %s at %s" % (
                key, summary[key], cutoff)


def test_counts_reconcile():
    result = backtest.temporal_backtest("2023-07-01")
    detail, summary = result["detail"], result["summary"]
    assert summary["incidents"] == len(detail)
    assert summary["knowable"] + summary["unknowable"] == summary["incidents"]
    assert summary["newly_caught"] == int(
        (detail["mechnari_would_flag"] & ~detail["dfmea_on_file_covered"]).sum())


def test_newly_caught_is_a_strict_subset_of_what_was_flagged():
    detail = backtest.temporal_backtest("2023-07-01")["detail"]
    newly = detail[detail["newly_caught"]]
    assert newly["mechnari_would_flag"].all()
    assert not newly["dfmea_on_file_covered"].any()


def test_the_measurement_is_capable_of_failing():
    """
    If the system scores a perfect 100% at every cutoff, the harness is
    measuring its own construction rather than the product. Real warranty
    data contains failures that cross the taxonomy, and so must this.
    """
    recalls = [backtest.temporal_backtest(c)["summary"]["mechnari_recall"]
               for c in backtest.CUTOFF_SWEEP]
    assert any(r < 1.0 for r in recalls), (
        "Mechnari scored 100% at every cutoff - the backtest cannot fail, "
        "so it is not measuring anything")


def test_the_result_holds_across_cutoffs_not_just_one():
    """One date is a data point. A claim needs the curve."""
    frame = backtest.sweep()
    assert len(frame) == len(backtest.CUTOFF_SWEEP)
    assert (frame["mechnari_recall"] > frame["dfmea_recall"]).all(), (
        "the advantage does not hold at every cutoff")
    assert (frame["knowable"] > 0).all()


def test_cold_start_hides_the_part_from_its_own_evaluation():
    """
    The whole claim is about a part with no history. If the part being
    evaluated is still in the corpus, it matches itself and the number is
    meaningless.
    """
    result = backtest.cold_start_backtest()
    assert result["parts_evaluated"] > 0
    assert 0.0 <= result["recall"] <= 1.0
    # Self-matching would drive this to essentially 100%.
    assert result["recall"] < 0.95, (
        "cold-start recall of %.0f%% suggests parts are matching themselves"
        % (result["recall"] * 100))
    assert result["parts_missed_entirely"] > 0, (
        "no part missed entirely - suspiciously perfect")


def test_headline_agrees_with_the_underlying_runs():
    headline = backtest.headline()
    summary = backtest.temporal_backtest(backtest.DEFAULT_CUTOFF)["summary"]
    cold = backtest.cold_start_backtest()
    assert headline["dfmea_recall"] == summary["dfmea_recall"]
    assert headline["mechnari_recall"] == summary["mechnari_recall"]
    assert headline["newly_caught"] == summary["newly_caught"]
    assert headline["cold_start_recall"] == cold["recall"]


def test_backtest_is_deterministic():
    first = backtest.temporal_backtest("2023-07-01")["summary"]
    second = backtest.temporal_backtest("2023-07-01")["summary"]
    assert first == second


def _main():
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print("PASS  %s" % name)
        except AssertionError as exc:
            failures += 1
            print("FAIL  %s\n      %s" % (name, exc))
        except Exception as exc:  # noqa: BLE001 - report, do not mask
            failures += 1
            print("ERROR %s\n      %s: %s" % (name, type(exc).__name__, exc))
    print("\n%d passed, %d failed" % (len(tests) - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_main())
