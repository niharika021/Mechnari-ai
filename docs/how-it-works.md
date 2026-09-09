# How it works

The whole system is one pipeline, run in two directions.

**Forward, for a part that does not exist yet:** words → similar parts →
failure modes those kinds of part are known for → scores from the warranty
record → a draft sheet an engineer edits.

**Backward, for a part already on file:** the DFMEA as filed → what the
warranty record says now → the difference.

Nothing in that pipeline calls a model. The copilot is a layer on top that
reads its output and writes English.

---

## 1. Describe the part

The engineer types a component name, its function, and its material. No part
number is required, and the part need not exist.

`retrieval.describe()` folds those three fields into one query document.

## 2. Find the closest historical parts

`retrieval.find_similar_parts()` — TF-IDF cosine similarity over a corpus
built from every part in the BOM.

Three design decisions here, each forced by measurement rather than taste
(`retrieval.evaluate_retrieval()` reproduces the numbers):

**The vectoriser never sees the label.** The corpus is descriptive text only
— component name, function, material — never part type or family names.
Otherwise type inference would read the answer off its own feature vector
and the accuracy figures would be fiction. System package is excluded too:
it groups parts by circuit, which actively fights grouping them by kind.
Dropping it moved type accuracy from 26% to 34%.

**The head noun is weighted, and it is the last one.** In a mechanical BOM
the head noun of a component name determines its type, but bag-of-words
drowns that one noun. English compound nouns are head-final: a *Fuel Return
Line Clamp* is a clamp, not a line, so only the last component noun counts.
Boosting every noun in the name instead scored a *Fuel Return Line* as a
clamp and cost 4 points of mode recall.

**The system proposes a type; it does not assert one.** Top-1 type
prediction plateaus near 50% on a 50-part corpus spread over 17 types, and
no tuning fixes it — after holding a part out, some types have a single
sibling left. So the analysis proposes modes for *every* kind of part among
the neighbours, states its confidence, and asks an engineer to confirm. That
choice is worth **19 points of mode recall** over winner-take-all.

## 3. Pull the failure modes those kinds of part are known for

`retrieval.candidate_failure_modes()` collects every catalogued mode scoped
to the neighbours' types **and** their families.

Why two levels: a mode attaches at the level it actually generalises to.
Chafing wear-through is real for any flexible line, so it sits at **family**
level. Coking inside a PTFE lumen is only real downstream of an air
compressor, so it sits at **type** level. The first build keyed everything
to part type and produced a finding telling an engineer to check a wire
conduit for park-brake binding. Inheritance has to be narrow enough to stay
true. See [Data model](data-model.md#the-two-level-taxonomy).

## 4. Score, without asking anyone's opinion

`risk_engine` owns every number. Three jobs:

### Severity comes from the effect registry

Severity is a property of the failure **effect** at a system level, not of an
individual analysis. Holding effects in one table means the same effect
carries the same severity on every program — a standard IATF / AIAG-VDA
audit expectation, and it is why `gap_detection.severity_consistency_findings()`
can flag rows scored below the organisation standard.

### Occurrence is counted, not remembered

Claims per 1000 units in service is a measured rate, and the AIAG occurrence
anchors map that rate onto the 1–10 score:

```
occurrence 10  >= 120.0 claims/1000      5  >= 2.0
            9  >=  55.0                  4  >= 1.0
            8  >=  22.0                  3  >= 0.5
            7  >=  11.0                  2  >= 0.1
            6  >=   5.0                  1  >= 0.01
```

Where the measured rate and the DFMEA disagree, the field data is the
evidence and the workshop number is the claim. That single definition lives
in `risk_engine.OCCURRENCE_RATE_PER_1000`, which `generate_csv_data.py`
imports too — so the data and the engine cannot drift apart.

### Detection is sanity-checked against where failures escaped to

If a mode reached a customer, the design control did not detect it, and a
Detection score of 3 on that mode is not defensible.
`risk_engine.DETECTION_FLOOR_BY_STAGE` maps the stage a failure escaped to
onto the best Detection score still arguable.

### Ranking is Action Priority, not RPN

AIAG-VDA dropped RPN in 2019 because multiplication misranks risk:

```
S=9, O=2, D=2  ->  RPN 36
S=4, O=3, D=4  ->  RPN 48    <- says the safety-relevant failure matters less
```

**Action Priority** is a band lookup read severity-first, then occurrence,
then detection — the order that encodes *how badly it hurts* ahead of *how
often* ahead of *would we catch it*. A lookup table is more auditable than a
product because it cannot be argued with. RPN is retained as a legacy column
so existing reviewers keep their familiar number.

The bands, from `risk_engine`:

```
SEVERITY_BANDS    S9-10 | S5-8  | S2-4 | S1
OCCURRENCE_BANDS  O6-10 | O4-5  | O2-3 | O1
DETECTION_BANDS   D7-10 | D5-6  | D1-4
```

> ⚠️ The AP table in this build is **provisional**. See
> [Evidence and limits](evidence-and-limits.md#the-action-priority-table-is-provisional).

### AP levers

`risk_engine.find_ap_levers()` answers the question a recommended action is
supposed to answer: *what single change would actually move this row's
band?* It walks the AP table and reports which one-factor change in
Occurrence or Detection lands the row in a lower band — and, by omission,
when nothing does. Severity is never reassessed downwards: it is fixed by
the failure effect, and an action that does not change the effect cannot
change it.

## 5. Detect what the DFMEA missed

`gap_detection.detect_gaps()` is a set difference, not a generation task:

```
gaps(part) = applicable_modes(part) - analysed_modes(part)
```

where `applicable_modes` spans the part's own type **and** its family.

Nothing here calls an LLM. Every finding is a row that either exists in the
knowledge base or does not, and every finding carries the field record
identifiers it came from — so an engineer can check it and an auditor can
trace it.

## 6. Assemble the form sheet

`dfmea_sheet.py` arranges the result into rows shaped like the AIAG-VDA form
sheet engineers already fill in, so the output lands in the format in use
rather than asking anyone to adopt a new layout.

Two things it deliberately does **not** do:

- **It computes no scores.** S/O/D and AP all arrive from `risk_engine`; this
  module only arranges them into columns.
- **It leaves the execution columns empty.** RESPONSIBILITY, TARGET
  COMPLETION DATE, ACTION TAKEN and COMPLETED DATE are the engineer's to
  fill. Inventing an owner or a date would be inventing a commitment.

The *Reassessment of Risk* block is the interesting exception. On a manual
sheet it is filled in by estimating what the recommended action will
achieve. Here it is read off `find_ap_levers`, so the with-action row states
the **consequence** of the action rather than a hope about it.

## 7. Submit, review, decide

The engineer accepts, edits or declines rows and submits the draft to the
review queue (`queue_store`). A Quality engineer opens it by URL, sees
accepted and declined rows separately, and sets a status: `needs_review`,
`returned`, or `approved`.

The declined-row trail is the point of the split. An engineer who leaves a
High row out is recorded as having considered and rejected it.

---

## How the claim is measured

### The temporal backtest — `backtest.temporal_backtest()`

Answering *would this have caught anything we missed?* with the whole
knowledge base loaded is cheating, because every mode in the catalogue was
written from a failure that has already happened. So the harness cuts the
history at a date:

```
train : every warranty record reported BEFORE the cutoff
test  : every warranty record reported ON OR AFTER it
```

For each incident after the cutoff it asks two questions about part *P* and
the mode *M* that failed:

- **Would Mechnari have flagged M for P?** — was M in P's applicable set, and
  had anything reported it before the cutoff?
- **Did the DFMEA on file cover M for P?** — the manual baseline.

Three honesty rules keep the answer meaningful:

1. **Unknowable modes are excluded from both sides.** A mode with no
   pre-cutoff record anywhere is counted `unknowable`, not scored as a miss
   and not as a success — nobody could have flagged it. At the reference
   cutoff that is 25 of 85 incidents. Including them would inflate the
   headline.
2. **The result is reported across five cutoffs**, not one flattering date.
3. **Claim-weighted recall is reported alongside incident recall**, so a
   single high-volume failure cannot hide behind a count of one.

### The cold-start backtest — `backtest.cold_start_backtest()`

Each part is hidden from the corpus entirely, and retrieval works from its
written description alone — the actual situation of a part that does not
exist yet.

### Retrieval evaluation — `retrieval.evaluate_retrieval()`

Leave-one-out over the corpus, reporting mode recall, whether the true type
appears among neighbours, family accuracy and top-1 type accuracy. The
weakest of those numbers is reported in full, because it is the reason the
system proposes rather than decides.

The results of all three are in [Evidence and limits](evidence-and-limits.md).

---

## Where the model actually is

Everything above runs with no model access at all. The copilot is a separate
layer that:

- reads the findings the engines produced, through read-only tools;
- writes the explanation in English, citing the record identifiers;
- drives the interface — filling the intake form, running the analysis,
  re-running it as a corrected part type, opening a filed DFMEA, switching
  view, or *proposing* that a row be declined for the engineer to approve.

It cannot write a number, complete an action or assign an owner, because no
such tool exists on either side of the wire. See
[Architecture](architecture.md#the-agent-layer).
