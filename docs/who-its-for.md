# Who it's for

## The three roles, and why they get different screens

Drafting a DFMEA, auditing one, and reporting on program risk are different
jobs and do not want the same screen. Each has its own route.

### Design / reliability engineer — `/design`

**The job:** produce a DFMEA for a part, often one that does not exist yet —
no part number, no history of its own.

**What Mechnari gives them:** describe the part in words, and get candidate
rows grounded in what the company has already learned, each with the field
records behind it. On every High row it also shows the single change in
Occurrence or Detection that would actually move the Action Priority band —
computed against the AP table, not suggested by a model.

**What changes for them:** the starting point stops being a blank page or a
copied previous sheet.

### Quality engineer — `/quality`

**The job:** defend these documents in an audit, and catch the ones that are
thin before they ship.

**What Mechnari gives them:** a review queue of submitted drafts, each
linkable by URL. Declined High rows show as *considered and declined* rather
than as missing. The same audit suite — severity consistency, Occurrence
against the warranty record, coverage — runs against parts already on file.

**What changes for them:** an engineer who leaves a High row out is recorded
as having *decided*, not as having missed it. That decision trail is the
artefact an auditor asks for.

### Company and leadership — `/company`

**The job:** know where program risk actually sits, and justify the spend.

**What Mechnari gives them:** coverage across the program, open safety gaps
by subsystem, warranty history, and the backtest curve — the evidence, not
row detail.

## The company profile this fits

Mechnari's entire value is the customer's own history. The fit criteria are
concrete:

| Needs | Why |
| --- | --- |
| **Years of warranty / 8D / field failure records** | These are the knowledge source. A company with no history gets very little. |
| **A product family with recurring part kinds** | Hoses, brackets, valves, clamps recurring across programs are what make a lesson transferable. |
| **DFMEA as a real obligation** | IATF 16949 or an equivalent regime — otherwise the audit trail is worth nothing to them. |
| **Enough parts that consistency is a scale problem** | At ten parts a year, memory works. At a thousand, it does not. |

Built against agricultural machinery (tractors), but nothing in the model is
crop-specific: the same shape holds for automotive, off-highway, industrial
equipment, and any manufacturer of durable physical products with a warranty
tail.

## Who should not adopt this yet

- **A new company with no failure history.** The retrieval has nothing to
  retrieve. Come back after a few programs of field data.
- **A team that wants the FMEA written for them.** Mechnari deliberately
  will not assert a part type, will not set a score, and will not close an
  action. If the goal is fewer human judgements, this is the wrong tool.
- **Anyone needing a certified AIAG-VDA Action Priority result today.** The
  AP table is [provisional](evidence-and-limits.md#the-action-priority-table-is-provisional)
  until every cell is checked against the published handbook.

## Who built it

**Niharika Yadav** — 10+ years mechanical design engineering in agriculture
(tractors). The scale figures above are from the job, not from a market
report: she has run these workshops.
