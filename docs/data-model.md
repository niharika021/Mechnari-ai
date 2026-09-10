# Data model

Eight normalised tables. **BigQuery is the source of record; the CSVs under
`data/` are the fallback**, and what every test suite runs against. Seven of
the tables are the runtime knowledge base; `historical_field_issues.csv` is
a legacy denormalised extract kept for reference and is not in BigQuery.

[`data_layer.py`](../data_layer.py) loads and joins them, reading from
BigQuery when `MECHNARI_DATA_SOURCE=bigquery` and falling back to CSV on any
failure — see [Architecture § Knowledge base source](architecture.md#knowledge-base-source).

Authoring happens in [`taxonomy.py`](../taxonomy.py) — part types, failure
effects and the cross-program mode catalogue — which
[`generate_csv_data.py`](../generate_csv_data.py) bakes into the CSVs. The
generator is seeded, so every figure in these docs reproduces exactly.

## The tables

| Table | Rows | Grain |
| --- | --- | --- |
| `part_types.csv` | 17 | One part type, and the family it belongs to |
| `failure_effects.csv` | 16 | One system-level effect, with the organisation's standard severity |
| `bom_package_hierarchy.csv` | 50 | One part in the active BOM |
| `material_master.csv` | 50 | Material properties per part |
| `failure_mode_catalog.csv` | 71 | One failure mode, scoped to a type or a family |
| `field_issues.csv` | 227 | One warranty / 8D incident |
| `dfmea_worksheet.csv` | 172 | One analysed row of a DFMEA on file |
| `historical_field_issues.csv` | — | Legacy flat extract, not read at runtime |

Row counts are the shipped synthetic dataset: 50 parts across 5 system
packages, 17 types in 8 families.

### `part_types.csv`

```
part_type_id, part_type_name, family_id, family_name, member_part_count
PT-HOSE-FUEL, Fuel Hose / Flexible Fuel Line, FAM-FLEX-ROUTING, Flexible Fluid Routing, 3
```

### `failure_effects.csv` — the severity registry

```
effect_id, effect_description, system_level, standard_severity
EF-01, Fuel or oil leak onto hot surface - fire risk, Machine, 9
```

This table is why Severity is never invented. Severity is a property of the
**effect**, not of an individual analysis, so the same effect carries the same
severity on every program — which is a standard IATF / AIAG-VDA audit
expectation, and what lets `gap_detection.severity_consistency_findings()`
flag a row scored below the organisation standard.

### `bom_package_hierarchy.csv` — the parts

```
part_id, system_package, item_reference, elementary_function, material_type, part_type_id
TR-FL-001, Fuel Routings, Hose 3: Fuel Cooler Supply Line,
  Transport bio-diesel fuel to cooler circuit without thermal leaks,
  Nitrile Rubber NBR with Aramid Braid, PT-HOSE-FUEL
```

`elementary_function` and `material_type` are the descriptive text the
retrieval corpus is built from. `part_type_id` is the label — and it is
deliberately **excluded** from that corpus, so type inference cannot read the
answer off its own feature vector.

### `failure_mode_catalog.csv` — the institutional memory

```
mode_id, scope_id, scope_level, failure_mode, potential_cause, effect_id,
typical_control, baseline_detection, recommended_action,
origin, origin_part_id, origin_part_name
```

`scope_level` is `TYPE` (65 modes) or `FAMILY` (6 modes) — see below.

`origin` is `CURRENT_PROGRAM` (50) or `PRIOR_PROGRAM` (21). The prior-program
modes are failure modes learned on earlier programs whose parts are no longer
in the active BOM. **These are the institutional memory a manual workshop
forgets, and they are where most gap-detection findings come from.**

`origin_part_id` / `origin_part_name` keep the provenance, so a proposed row
can say which part taught this lesson.

### `field_issues.csv` — the warranty record

```
issue_id, part_id, scope_id, mode_id, report_date, units_in_service,
claim_count, median_machine_hours, detection_stage, observed_effect_id,
observed_severity, description
```

`issue_id` is the 8D number (`8D-2021-0001`) — the citation every finding
carries. `claim_count` over `units_in_service` is the measured rate Occurrence
is derived from. `report_date` is what the temporal backtest cuts on.
`detection_stage` is where the failure escaped to, which sets the Detection
floor.

### `dfmea_worksheet.csv` — the DFMEA on file

```
part_id, mode_id, severity, occurrence, detection,
current_design_control, analyzed_by, analysis_date, revision
```

This is the manual baseline: what the workshop actually wrote. Everything the
product claims is a comparison against this table.

---

## The two-level taxonomy

Every part belongs to a **type**; every type belongs to a **family**. A
failure mode attaches at the level it actually generalises to:

| Level | Example mode | Why that level |
| --- | --- | --- |
| **Family** | Chafing wear-through | Real for any flexible line, whatever it carries |
| **Type** | Coking inside a PTFE lumen | Only real downstream of an air compressor |

So applicability is a union:

```
applicable_modes(part) = modes scoped to part's type  ∪  modes scoped to part's family
```

The first build keyed everything to part type, and the second attempt keyed
everything broadly. The broad version produced a finding telling an engineer
to check a wire conduit for park-brake binding. **Inheritance has to be narrow
enough to stay true**, and one level cannot be both — which is why there are
two.

## What is deliberately not in these tables

`standards.py` holds generic engineering failure modes and `own_records.py`
scores failures the engineer supplies. Neither is loaded by `data_layer`, and
neither appears in `failure_mode_catalog` — on purpose.

A mode in that catalog is a claim: *this company built a part like this and
this is how it failed*, which is what lets `gap_detection` call an unanalysed
one a **gap**. Generic practice supports no such claim, and nor does a
colleague's recollection. Beyond correctness, putting them in the table would
silently move every headline figure in the product, because gaps, coverage
and the backtest are all computed from `applicable_modes()` over it.

## Multi-tenancy

The tables are `organization_id`-ready: the shape assumes a tenant column and
nothing in the joins would need restructuring to add one.
[`schema.sql`](../schema.sql) holds the BigQuery DDL — generated from the
CSVs by [`bq_load.py`](../bq_load.py) rather than hand-maintained, so the
declared types cannot drift from what the engines actually receive the way a
hand-written DDL did once (it named two tables that matched no CSV and was
missing six others).

The shape is ready; real per-tenant access control on top of it is not
implemented — `organization_id`-ready describes the schema, not an auth
system.

## Loading and reloading

```bash
py bq_load.py            # create the dataset, load data/*.csv, verify it
py bq_load.py --verify   # only compare BigQuery against the CSVs
```

Loads are idempotent (`WRITE_TRUNCATE`), so running it twice leaves the same
rows rather than doubling them. `--verify` is the check that matters — it
reads every table back through the same code path the app uses and compares
row counts and column names against the CSV, which is how a schema mistake
(autodetect once loaded an all-string table as `string_field_0..5`, silently
losing every column name) gets caught here instead of surfacing as a wrong
number on a DFMEA row.

`POST /api/reload` re-reads whichever source is configured — BigQuery or
CSV — and clears the retrieval vectoriser cache (`data_layer.reload()` +
`retrieval.reload()`), so a regenerated dataset takes effect without a
restart.
