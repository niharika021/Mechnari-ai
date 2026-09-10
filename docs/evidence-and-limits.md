# Evidence and limits

Every figure on this page is reproduced by a committed harness, not asserted.
All of them were regenerated against the current code on **2026-09-09**.

```bash
py backtest.py     # the temporal and cold-start harnesses
py retrieval.py    # leave-one-out retrieval evaluation
```

---

## The temporal backtest

The warranty history is cut at a date. The system sees only what was known
before it, and is asked what it would have flagged on the failures that came
after. Reference cutoff `2023-07-01`:

| Metric | Result |
| --- | --- |
| DFMEA on file caught | **71.7%** of failures it could have anticipated |
| Mechnari would flag | **98.3%** — *+27 points* |
| Failures newly caught | **16**, every one learned on a *different* part; **3** at severity 9+ |
| Warranty claims behind them | **228** (claim-weighted recall: 72.3% → 99.1%) |
| Incidents after the cutoff | 85, of which **25 were unknowable** and excluded from both sides |

### It holds across all five cutoffs

| Cutoff | Incidents | Knowable | Unknowable | DFMEA | Mechnari | Lift | Newly caught | Claims | At S≥9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2022-07-01 | 127 | 64 | 63 | 73.4% | 96.9% | +23.5 | 15 | 189 | 3 |
| 2023-01-01 | 101 | 67 | 34 | 71.6% | 97.0% | +25.4 | 17 | 234 | 4 |
| **2023-07-01** | 85 | 60 | 25 | 71.7% | 98.3% | **+26.6** | 16 | 228 | 3 |
| 2024-01-01 | 71 | 56 | 15 | 78.6% | 98.2% | +19.6 | 11 | 178 | 1 |
| 2024-07-01 | 49 | 43 | 6 | 72.1% | 97.7% | +25.6 | 11 | 176 | 1 |

Reporting the sweep rather than one date is the point: a single flattering
cutoff would prove nothing.

### The honesty rules behind those numbers

1. **Unknowable modes are excluded from both sides.** A mode with no
   pre-cutoff record anywhere is nobody's miss — 25 of 85 incidents at the
   reference cutoff. Scoring them as misses against the manual baseline would
   inflate the headline. They are reported separately instead.
2. **Every newly caught failure was learned on a different part.**
   `newly_caught_cross_part` equals `newly_caught` at every cutoff — the lift
   is transfer of a lesson between parts, not the system recognising a part's
   own history.
3. **Claim-weighted recall is reported alongside incident recall**, so one
   high-volume failure cannot hide behind a count of one.
4. **Mechnari does not score 100%.** Some failures cross the taxonomy, and a
   backtest that always scores perfectly is measuring its own construction.

---

## Cold start — a part that does not exist yet

Each part is hidden from the corpus entirely; retrieval works from its written
description alone.

| Metric | Result |
| --- | --- |
| Failure modes surfaced | **82 of 112 — 73.2%** |
| Parts fully covered | 32 of 50 |
| Parts missed entirely | 14 |
| Mean shortlist | **18.9 candidates** out of 71 catalogued modes |

---

## Retrieval quality, reported in full

Leave-one-out over 50 parts, 17 types, 71 catalogued modes:

| Metric | Result | Reading |
| --- | --- | --- |
| Mode recall | **75.6%** | The product metric — applicable modes the proposal surfaces |
| True type among neighbours (`type_recall_at_k`) | 72% | The correct type appears in the shortlist |
| Leading family correct | 66% | Family-scoped modes are the general lessons |
| Leading type exactly right | **46%** | Weak — and the reason the system proposes rather than decides |
| Low-confidence rate | 50% | How often it declines to be sure |

**The weakest number is the load-bearing one.** Top-1 type prediction plateaus
near 50% on this corpus and no tuning fixes it — after holding a part out,
some types have a single sibling left. So the system does not assert a type:
it proposes modes for every kind of part among the neighbours, states its
confidence, and asks an engineer to confirm.

That choice is worth **19 points of mode recall** over winner-take-all. A
system that decided would be more confident and less useful.

---

## What the engines find in the current knowledge base

| Engine | Finding | Detail |
| --- | --- | --- |
| Gap detection | **127 gaps** | Across 50 parts, **15 at severity 9+**, every one evidence-backed. Mean DFMEA coverage **57.3%**. |
| Occurrence from warranty | **40 understated** | Claims measured on the part itself exceed the DFMEA's own estimate (90 understated in total, including modes measured on sibling parts; 23 overstated) |
| Action Priority | **35 → 64 High** | **70 rows change priority** once evidence replaces workshop opinion |
| Severity consistency | **6 rows** | The same failure effect scored below the organisation standard |

Every gap carries the field record identifiers it came from
(`gaps_with_evidence` equals `total_gaps`), so each one is checkable against
an 8D number.

---

## The Action Priority table is provisional

`risk_engine.AP_TABLE_VERIFIED` is `False`, and the platform reports AP as
provisional until it is `True`.

**Why.** AIAG-VDA publishes **three** separate Action Priority tables — DFMEA,
PFMEA and FMEA-MSR — because Occurrence and Detection mean different things in
each. In DFMEA, Occurrence is the likelihood of the cause over the design life
and Detection is whether design verification catches it; in PFMEA both are
about the manufacturing process instead. The band boundaries and some H/M/L
outcomes differ between them, so they are not interchangeable. Mechnari is a
DFMEA tool and reproduces the DFMEA table.

**What is verified.** The band structure and 7 cells are confirmed against a
primary source: Jochen Pfeufer (VDA QMC project lead for the AIAG-VDA
alignment), *"New global FMEA standard — FMEA Alignment AIAG and VDA"*, SMMT
AQMS Conference, November 2018, slide *"Design FMEA Action Priority (AP)
(Extract)"*.

That source caught a real structural error. Severity does **not** split into 5
bands (9-10 / 7-8 / 4-6 / 2-3 / 1) — the real table uses **4** (9-10 / 5-8 /
2-4 / 1). Detection does **not** split into 4 bands — the real table merges the
bottom two into one, 1-4. A wrong band boundary is worse than an unverified
cell, because it puts entire ranges of scores in the wrong bucket. Both were
fixed.

**What is not verified.** The deck itself states it reflects the
pre-publication "yellow print" status and is *"not fixed and non-binding"*, so
the published 2019 handbook may differ in cells it does not confirm. Every
cell in `risk_engine.AP_TABLE` is therefore individually tagged:

| Tag | Meaning |
| --- | --- |
| `VERIFIED` | Taken directly from that slide |
| `DERIVED` | The one value forced by a VERIFIED neighbour plus the monotonic rule (`test_action_priority_never_decreases_as_risk_rises`) |
| `unconfirmed` | Best-effort completion, consistent with monotonicity and with severity dominating occurrence dominating detection — **not authoritative** |

**To lift the label:** check the unconfirmed cells against your copy of the
AIAG-VDA FMEA Handbook (2019), the **DFMEA** Action Priority table
specifically, correct any that differ, and set `AP_TABLE_VERIFIED = True`.
RPN is retained alongside as a legacy column so existing reviewers keep their
familiar number.

---

## Known limitations

Stated here rather than discovered in review.

- **The data is synthetic.** Domain-correlated and internally consistent — a
  bracket only ever draws bracket-type failure modes, never a hose's — but the
  backtest measures the system against generated warranty history. The harness
  runs unchanged against a pilot company's anonymised data; that substitution
  is the next real validation, not a rewrite.
- **The AP table is provisional.** See above.
- **TF-IDF is a floor, not a ceiling.** At 50 parts it is the honest choice.
  Moving to Vertex AI embeddings replaces two functions and nothing
  downstream.
- **Effects are inherited with their origin.** A mode carried to a new part
  keeps the effect it had on the part that taught it, so a coolant drain valve
  can inherit an AC valve's cab-climate effect. Re-evaluating effect per target
  part is the known fix.
- **Type inference is right 46% of the time at top-1.** This is designed
  around rather than hidden — the system proposes and an engineer confirms —
  but it means the shortlist is wider than a confident system's would be.
- **Signed-out reports live in one browser.** They move to Firestore only when
  the user signs in.

## Roadmap

1. Verify the Action Priority cells against the AIAG-VDA handbook and lift the
   provisional label.
2. Replace synthetic data with a pilot company's anonymised warranty set and
   re-run the backtest unchanged.
3. Push aggregation down into BigQuery once the data is large enough to earn
   it — millions of claims rather than hundreds is the point where reading
   the tables whole into memory stops being the faster choice.
4. Close the loop: when a new claim arrives, flag which shipped DFMEAs
   predicted low risk for that mode.
5. Migrate reports made while signed out into an account on first sign-in.

Shipped since the first version of this page: the AIAG-VDA form sheet as the
actual output (`dfmea_sheet.py`), the human-in-the-loop review between
findings and report, the Quality action-closure handoff, Firestore
persistence, optional Google sign-in, and BigQuery as the source of record —
see [Architecture § Knowledge base source](architecture.md#knowledge-base-source).
