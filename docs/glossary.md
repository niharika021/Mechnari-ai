# Glossary

For readers outside mechanical reliability engineering. Terms as this project
uses them.

## The document

**DFMEA — Design Failure Mode and Effects Analysis**
The mandatory document for catching how a part can fail before it is built.
One row per failure mode: what fails, why, what happens as a result, how bad
that is, how likely, whether design verification would catch it, and what will
be done. Produced in a cross-functional workshop — design, quality,
manufacturing in one room — typically a week per 10–14 part package.

**PFMEA**
The same instrument applied to the manufacturing *process* rather than the
design. Relevant here only because AIAG-VDA publishes a **different** Action
Priority table for it, and the two are not interchangeable.

**FMEA-MSR**
Monitoring and System Response — the third FMEA variant, with its own AP table
again.

**Form sheet**
The standard AIAG-VDA layout a DFMEA is filled in on. `dfmea_sheet.py` emits
rows in this shape so output lands in the format engineers already use.

## The scores

**Severity (S), 1–10**
How bad the effect is. In this system it is a property of the failure
**effect**, read from a registry (`failure_effects.csv`), not estimated per
analysis — which is what makes the same effect carry the same severity on
every program. Never reassessed downwards by an action: an action that does
not change the effect cannot change the severity.

**Occurrence (O), 1–10**
How likely the cause is over the design life. Normally a workshop opinion.
Here it is derived from the measured warranty rate — claims per 1000 units in
service — mapped onto the AIAG occurrence anchors.

**Detection (D), 1–10**
Whether design verification and validation would catch the cause before
release. Counter-intuitively, **higher is worse**: 1 means near-certain
detection, 10 means none. Sanity-checked here against where failures actually
escaped to — if a mode reached a customer, a Detection score of 3 is not
defensible.

**RPN — Risk Priority Number**
`S × O × D`. Dropped by AIAG-VDA in 2019 because multiplication misranks risk:
`S=9, O=2, D=2` scores 36 while `S=4, O=3, D=4` scores 48, which says the
safety-relevant failure matters less. Retained here as a legacy column only.

**AP — Action Priority**
The 2019 replacement for RPN: a lookup table read severity-first, then
occurrence, then detection, returning **High**, **Medium** or **Low**. More
auditable than a product because a lookup cannot be argued with.
[Provisional in this build.](evidence-and-limits.md#the-action-priority-table-is-provisional)

**AP lever**
The single change in Occurrence or Detection that would actually move a row's
AP band — computed by walking the table. It turns "recommended action" from a
hope into a stated consequence, and by omission tells you when no single change
works.

## The evidence

**8D — Eight Disciplines**
A structured problem-solving report filed against a field failure. The `8D`
number (`8D-2021-0001`) is the citation every Mechnari finding carries, and is
what makes a finding checkable rather than assertable.

**Warranty claim**
One customer-side failure paid for under warranty. `claim_count` over
`units_in_service` is the measured rate Occurrence is derived from.

**Units in service**
How many machines carrying the part are in the field — the denominator that
turns a raw claim count into a rate.

**Detection stage**
Where a failure was caught: design review, end-of-line test, dealer
pre-delivery, or the customer. The later it was caught, the worse the honest
Detection score.

**Claim-weighted recall**
Recall where each incident counts for the number of warranty claims behind it,
so one high-volume failure cannot hide behind a count of one.

## The model

**Part type**
The kind of part — *Fuel Hose / Flexible Fuel Line*, *Structural Bracket*.
17 of them in the shipped dataset.

**Family**
A group of types that share failure behaviour — *Flexible Fluid Routing*.
8 of them. A failure mode attaches at type or family level, whichever it
actually generalises to.

**Failure mode**
A specific way a part fails — *chafing wear-through*, *coking inside a PTFE
lumen*. Catalogued once, scoped to a type or a family, and inherited by parts
of that kind.

**Failure effect**
What the failure does at machine or subsystem level — *fuel or oil leak onto
hot surface, fire risk*. Carries the standard severity.

**System package**
A functional grouping of parts — *Fuel Routings*, a hydraulic package. The unit
a DFMEA workshop is run for. Deliberately **excluded** from the retrieval
corpus, because it groups parts by circuit and that fights grouping them by
kind.

**BOM — Bill of Materials**
The parts list for the machine.

**Applicable modes**
Every catalogued mode scoped to a part's type **or** its family — what the
company already knows could happen to this kind of part.

**Gap**
`applicable modes − analysed modes`. A failure mode the company has already
proven on this kind of part that this part's DFMEA never analysed. The product.

## The standards

**AIAG-VDA FMEA Handbook (2019)**
The harmonised American (AIAG) and German (VDA) automotive standard that
replaced both predecessors, introduced Action Priority and retired RPN.

**IATF 16949**
The automotive quality management standard. It expects a DFMEA, expects it to
be defensible, and expects consistency — which is why severity lives in a
registry and why the declined-row trail matters.

**Yellow print**
A pre-publication draft circulated for comment. The primary source behind this
build's AP table is an extract of one, explicitly marked non-binding — hence
the provisional label.

## The machinery

**TF-IDF cosine similarity**
Classical text retrieval: score words by how distinctive they are, compare
documents by the angle between their word vectors. No model, no embedding
service, fully deterministic.

**Head noun**
The noun that determines what a compound noun *is*. English is head-final: a
*Fuel Return Line Clamp* is a clamp. Weighted heavily in retrieval, and only
the last one counts.

**Temporal holdout / backtest**
Cutting history at a date, showing the system only what was known before it,
and scoring it on what came after.

**Unknowable**
A failure mode with no record anywhere before the cutoff. Excluded from both
sides of the backtest — nobody could have flagged it.

**Cold start**
The situation of a part that does not exist yet: no part number, no DFMEA, no
history of its own. Only a written description.

**Leave-one-out**
Evaluating by hiding one item at a time and asking the system to recover it
from the rest.

**Google ADK**
Agent Development Kit — the framework the copilot is built on. Agents expose a
`root_agent`, tools are plain typed Python functions, specialists compose under
a coordinator via `sub_agents`.

**AG-UI**
The streaming protocol between an agent backend and a chat frontend. Lets the
copilot stream token by token and carries the browser's client-side tools to
the agent.

**CopilotKit**
The React chat frontend. Its runtime here is a pure relay — that Next.js
process calls no model.

**Human-in-the-loop**
A tool that proposes rather than acts, requiring explicit approval. Used for
exactly one thing: declining a row.
