# API reference

FastAPI, defined in [`api.py`](../api.py). Base path `/api`. Interactive docs
at `/docs` when the server is running.

Every route calls a module that has its own test suite and shapes the return
value as JSON. **No route computes anything.**

```bash
py -m uvicorn api:app --port 8000 --reload
```

## Conventions

- All responses are JSON. `NaN` is emitted as `null`, never as the invalid
  JSON literal `NaN`.
- `503` — the dataset is missing or unreadable.
- `404` — unknown `part_id`, `draft_id` or `report_id`. Never a 500.
- `400` — malformed request (empty description, unknown `part_type_id`,
  oversized batch).
- `403` — writing a report owned by somebody else. *Reading* one returns
  `404` on purpose, so a stranger cannot learn that an id exists.
- Authentication is a bearer ID token from Google sign-in, and is optional on
  every route except the report writes.

---

## Health and identity

### `GET /api/health`

```json
{
  "status": "ok",
  "queue_backend": "firestore",
  "report_backend": "firestore",
  "auth_available": true
}
```

`queue_backend` is reported because a deployment that quietly fell back to the
file store is the failure this is meant to catch — on Cloud Run that file is
per-instance and resets on scale-to-zero, so the queue looks fine until it
empties itself. `firestore` is what you want; `file` means the queue will not
survive.

### `GET /api/me`

Who the backend thinks is calling — `{"signed_in": bool, "user": {...}|null}`.
The frontend shows the name it got from Google, but this is the one the server
verified. If they disagree, the server's answer is the real one.

---

## Reference data

| Route | Returns |
| --- | --- |
| `GET /api/parts` | Every part in the BOM, joined with material master. Optional `?system_package=` filter. |
| `GET /api/system-packages` | Sorted list of system package names. |
| `GET /api/part-types` | The 17 types with their families. |

---

## Drafting a DFMEA

### `POST /api/propose-dfmea`

The cold-start route: describe a part that need not exist.

```jsonc
// request
{ "part_name": "Fuel Return Line Clamp",
  "function": "Retain fuel return line against frame rail",
  "material": "Zinc-plated steel",
  "part_type_id": "" }        // optional — set it to confirm the type
```

```jsonc
// response
{ "status": "success",
  "reason": "...",
  "confident": true,           // did type inference clear MIN_TYPE_CONFIDENCE
  "confirmed": false,          // did the caller pin the type
  "part_type_id": "PT-CLAMP",
  "part_type_name": "...",
  "family_name": "...",
  "confidence": 0.61,
  "safety_candidates": 3,
  "neighbours": [ /* similar parts with similarity scores */ ],
  "candidates": [ /* proposed rows, each with severity, occurrence,
                     detection, action_priority, evidence ids, and levers */ ] }
```

`levers` ride along with each row rather than being fetched per row —
`find_ap_levers` is a pure table lookup, so computing twenty of them here
costs nothing and saves the client a request per High row.

`400` if the description is empty or `part_type_id` is unknown.

### `POST /api/dfmea-sheet`

Assembles proposed modes into AIAG-VDA form-sheet rows.

```jsonc
{ "items": [
    { "part_number": "", "description": "Fuel Return Line Clamp",
      "function": "...", "material": "...", "system_package": "Fuel Routings",
      "part_type_id": "", "existing_part_id": "" }
  ] }
```

One entry for a single part, several for a package — the shape is the same
either way, so the frontend does not need two request paths for one operation
repeated. **Maximum 25 items**; more is a `400`.

### `GET /api/dfmea-sheet/{part_id}`

The DFMEA already on file for a part, what the warranty record says about it
now, and which applicable modes it never covered. `404` on an unknown part.

---

## Scoring

### `POST /api/rescore`

```jsonc
{ "rows": [ { "severity": 9, "occurrence": 4, "detection": 6 } ] }
```

```jsonc
[ { "action_priority": "H", "rpn_legacy": 216, "levers": [ ... ] } ]
```

This route exists so the review screen never computes a priority itself. An
engineer editing Detection changes the Action Priority, and that
recalculation has to stay in `risk_engine` — a frontend doing its own band
lookup would be a second, unversioned copy of the AP table. **Maximum 500
rows.**

### `POST /api/ap-levers`

`{ "severity": 9, "occurrence": 4, "detection": 6 }` → the current AP plus
every single-factor change that would move the band.

---

## The review queue

### `POST /api/queue/submit`

```jsonc
{ "part_name": "...", "function": "...", "material": "...",
  "system_package": "...", "part_type_name": "...",
  "accepted_rows": [ /* DraftRow */ ],
  "declined_rows": [ /* DraftRow, each with the engineer's reason */ ],
  "submitted_by": "Design Engineer",
  "part_number": "", "package_ref": "" }
```

→ `{ "draft_id": "..." }`

`DraftRow` allows extra fields on purpose. A DFMEA row is a document that
keeps growing columns, and a strict model drops unknown ones *silently, with
the request still returning 200*. That has already cost two rounds of quiet
data loss — most recently seventeen fields including the failure effect
itself, so Quality was reviewing a document with an empty effect column and no
way to tell. The fields the API depends on stay declared and validated;
everything else is carried through untouched.

| Route | Does |
| --- | --- |
| `GET /api/queue` | Queue summaries, newest first |
| `GET /api/queue/{draft_id}` | One draft in full — `404` if unknown |
| `POST /api/queue/{draft_id}/status` | `{ "status": "needs_review" \| "returned" \| "approved", "comments": "" }` |

---

## Auditing what is already on file

### `GET /api/audit/{part_id}`

```jsonc
{ "part": { ... },
  "severity_findings":   [ /* rows scored below the organisation standard */ ],
  "occurrence_findings": [ /* claims measured on the part exceed its own estimate */ ],
  "gaps":                [ /* applicable modes the DFMEA never analysed */ ] }
```

| Route | Returns |
| --- | --- |
| `GET /api/gaps` | Every gap across the program. Optional `?system_package=`. |
| `GET /api/gap-metrics` | `parts_analysed`, `modes_in_catalog`, `total_gaps`, `safety_gaps`, `mean_coverage_pct`, `severity_drift_rows` |
| `GET /api/risk-metrics` | `ap_high_as_filed`, `ap_high_evidence_based`, `ap_escalations`, `occurrence_understated`, `ap_table_verified` |
| `GET /api/issues/summary` | Every part with a warranty issue on record — active or retired — and how many |
| `GET /api/issues/{part_id}` | The warranty history for one part |

`GET /api/issues/summary` is deliberately independent of what any one DFMEA
says: company-wide visibility into what has actually gone wrong.

---

## The backtest

| Route | Returns |
| --- | --- |
| `GET /api/backtest?cutoff=YYYY-MM-DD` | `summary`, `train_records`, `test_records`, and per-incident `detail`. Defaults to `2023-07-01`. |
| `GET /api/backtest/sweep` | The same summary at all five cutoffs |
| `GET /api/backtest/cold-start` | Recall from written descriptions alone, with each part hidden from the corpus |
| `GET /api/backtest/cutoffs` | `{ "cutoffs": [...], "default": "2023-07-01" }` |

`summary` carries `dfmea_recall`, `mechnari_recall`, both claim-weighted
variants, `newly_caught`, `newly_caught_claims`, `newly_caught_safety`,
`incidents_after_cutoff` and `unknowable_at_cutoff`.

---

## The copilot

### `POST /api/copilot/ask`

`{ "question": "...", "session_id": "web" }` — synchronous, one answer. The
dependency-light fallback path.

### `POST /api/ag-ui`

The AG-UI streaming endpoint over the same `root_agent`, mounted by
`agui_endpoint.py`. This is what the CopilotKit frontend talks to, and it is
what carries the browser's client-side tools to the agent.

### `GET /api/copilot/health`

```json
{ "api_key_present": true, "api_key_works": true,
  "reason": "", "agui_path": "/api/ag-ui" }
```

So the frontend can say something honest before opening an SSE stream that is
only going to fail on auth.

---

## Reports

Saved analyses, owned by the signed-in user. Reads work signed out and return
nothing rather than 401; writes require a verified token.

| Route | Auth | Does |
| --- | --- | --- |
| `GET /api/reports` | optional | The caller's own report summaries. Signed out → `[]`, and the frontend falls back to local storage. |
| `POST /api/reports` | **required** | `{ "title", "system_package", "result" }` |
| `GET /api/reports/{id}` | optional | The report — `404` unless the caller owns it |
| `PATCH /api/reports/{id}` | **required** | `{ "result"?, "submitted_at"?, "draft_ids"? }` |
| `DELETE /api/reports/{id}` | **required** | `{ "ok": true }` |

---

## Maintenance

### `POST /api/reload`

Re-reads the CSVs and clears the retrieval cache. `{ "ok": true }`.
