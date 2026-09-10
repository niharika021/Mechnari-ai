# Operations

## Prerequisites

- **Python 3.10+** (3.11 in the container, 3.13 tested locally)
- **Node.js 20+** — only for the Next.js frontend
- **Gemini access via Vertex AI** — only for the copilot's prose. Every score,
  gap, Action Priority and backtest figure works with no model access at all.

## Install

```bash
git clone https://github.com/niharika021/Mechnari-ai.git
cd Mechnari-ai
pip install -r requirements.txt
cp .env.example .env
```

Dependencies: `google-adk`, `google-genai`, `ag-ui-adk`, `google-cloud-firestore`,
`firebase-admin`, `google-cloud-bigquery`, `fastapi`, `uvicorn`,
`pandas`, `scikit-learn`, `python-dotenv`.

`fastapi` and `uvicorn` are listed explicitly even though they arrive
transitively via `google-adk` — depending on that is luck, not a contract.

## Model access

```bash
gcloud auth application-default login
gcloud services enable aiplatform.googleapis.com --project YOUR_PROJECT_ID
```

Then set `GOOGLE_CLOUD_PROJECT` in `.env`.

### Configuration — `.env`

| Variable | Meaning |
| --- | --- |
| `GOOGLE_GENAI_USE_VERTEXAI` | `true` for the Vertex path (recommended) |
| `GOOGLE_CLOUD_PROJECT` | The GCP project. Firestore picks this up too. |
| `GOOGLE_CLOUD_LOCATION` | e.g. `global` — availability is regional |
| `MECHNARI_MODEL` | Publisher model id. Defaults to `gemini-2.5-flash` on Vertex, `gemini-flash-latest` on AI Studio. |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Only for the legacy AI Studio `AIza` key path |
| `ALLOWED_ORIGINS` | Comma-separated extra CORS origins for the deployed frontend |
| `MECHNARI_DATA_SOURCE` | `bigquery` to read the knowledge base from BigQuery. Unset (or anything else) reads `data/*.csv` — what every test suite runs against. |
| `MECHNARI_BQ_PROJECT` | Project holding the dataset. Defaults to `GOOGLE_CLOUD_PROJECT`. |
| `MECHNARI_BQ_DATASET` | Defaults to `mechnari_engineering`. |

> **Use Vertex, not an AI Studio key.** As of September 2026 the keys AI Studio
> issues (the `AQ.` format that replaced `AIza`) return
> `401 ACCESS_TOKEN_TYPE_UNSUPPORTED` against the Generative Language API — a
> known Google-side issue with no published fix. Vertex avoids that path
> entirely and is the better fit for Cloud Run anyway: the service account
> supplies the credential, so there is no key to leak or rotate.
>
> Model names are **not** interchangeable between the two. Vertex serves
> versioned publisher models and 404s on AI Studio's floating aliases.

### Configuration — `web/.env.local`

| Variable | Meaning |
| --- | --- |
| `NEXT_PUBLIC_API_BASE` | Where the browser reaches FastAPI. **Read at build time** into the bundle. |
| `COPILOTKIT_TELEMETRY_DISABLED` | `true`. CopilotKit reports usage to its vendor by default; this product's premise is proprietary warranty data, so it is opted out rather than left on. |
| `NEXT_PUBLIC_FIREBASE_*` | Four values for optional Google sign-in. Public by design — they identify the project rather than authorising anything. Leave unset and sign-in simply does not appear. |
| `API_BASE_INTERNAL` | Server-side only. Lets the CopilotKit relay reach the API over a private origin. |

## Run

### Two processes

```bash
py -m uvicorn api:app --port 8000 --reload
```

```bash
cd web && cp .env.example .env.local && npm install && npm run dev
```

Open <http://localhost:3000>. API docs at <http://localhost:8000/docs>.

Both are also defined in [`.claude/launch.json`](../.claude/launch.json) as
`api` and `web`.

## Regenerate the dataset

```bash
py generate_csv_data.py
```

Seeded, so every figure in these docs reproduces exactly. `POST /api/reload`
picks up the new CSVs without a restart.

If BigQuery is the configured source, load the regenerated CSVs into it too:

```bash
py bq_load.py            # create the dataset if needed, load, verify
py bq_load.py --verify   # just compare what is loaded against the CSVs
```

Both steps are idempotent (`WRITE_TRUNCATE`) and read the schema from the
CSV rather than autodetecting it — autodetect once loaded an all-string
table with no way to tell its header from a data row, and silently produced
`string_field_0..5` instead of real column names.

## Tests

**167 tests across 10 suites, all passing** (verified 2026-09-10). Each file
runs standalone — no pytest required:

```bash
for f in test_*.py; do py "$f"; done
```

| Suite | Tests | Covers |
| --- | --- | --- |
| `test_api.py` | 39 | Route wiring, JSON-safety, 404-not-500, queue round trip |
| `test_risk_engine.py` | 23 | S/O/D derivation, AP band lookup, lever finding, monotonicity |
| `test_retrieval.py` | 17 | Describe/similarity, type inference, proposals |
| `test_mechnari_tools.py` | 13 | The ADK tool surface — including that no agent can write a score |
| `test_backtest.py` | 12 | Temporal holdout, unknowable exclusion, claim weighting |
| `test_gap_detection.py` | 12 | Type ∪ family applicability, severity consistency |
| `test_queue_store.py` | 11 | Draft queue atomicity, corruption recovery, Firestore degradation |
| `test_report_store.py` | 10 | Report ownership and update semantics |
| `test_data_source.py` | 10 | BigQuery vs CSV selection, and that an unreachable warehouse degrades to the CSVs rather than failing |
| `test_standards_and_own_records.py` | 20 | The standards floor, engineer-supplied records, and the separation between them |

Two of these are load-bearing beyond coverage:

- `test_mechnari_tools.py` asserts that no agent holds a tool that could write
  a score. That is the architectural guarantee, enforced rather than
  documented.
- `test_risk_engine.py::test_action_priority_never_decreases_as_risk_rises`
  enforces monotonicity across the AP table, which is what forces the
  `DERIVED` cells to the one value they can hold.

## Deployment

The build is live at <https://app.mechnari.in>. Full runbook: [`../DEPLOY.md`](../DEPLOY.md). The shape:

1. **Deploy the API first** — the frontend needs its URL baked in at build
   time.
2. **Build the frontend with `NEXT_PUBLIC_API_BASE` and the four
   `NEXT_PUBLIC_FIREBASE_*` values set**, then deploy. They are compiled into
   the bundle; passing them at run time does nothing. Omitting the Firebase
   ones is not an error — the app works, permanently signed out, with the
   sign-in button hidden, which is a confusing thing to debug later.
3. **Close the CORS loop** — add the frontend origin to `ALLOWED_ORIGINS` on
   the API service.
4. **Verify** — all three role views return 200 and the metrics match the
   local figures.

The [`Dockerfile`](../Dockerfile) copies `*.py` wholesale rather than a
hand-written module list. The list version went stale the moment new modules
appeared and failed the deploy with `ModuleNotFoundError: No module named
'auth'`. What must not ship is excluded in `.dockerignore` instead — one place
to look, and adding a module cannot break it.

`.gcloudignore` matters too: without it, gcloud falls back to the top-level
`.gitignore` only and does not read nested ones like `web/.gitignore`, which
uploaded `web/.next/` and `node_modules/` and killed the deploy on a running
dev server's lock file.

## Storage backends

| What | Firestore | Fallback |
| --- | --- | --- |
| Review queue | `draft_queue` | `.mechnari_runtime/draft_queue.json` |
| Saved reports | `reports` | `.mechnari_runtime/reports.json` |

Firestore needs enabling once per project, and the runtime service account
needs `roles/datastore.user`. `GOOGLE_CLOUD_PROJECT` is all the code reads.

**Always check which backend a deployment landed on:**

```bash
curl https://YOUR-API/api/health
# {"status":"ok","queue_backend":"firestore","data_source":"bigquery"}  <- what you want
# {"status":"ok","queue_backend":"file","data_source":"csv"}            <- degraded, but working
```

`data_source` is the equivalent check for the knowledge base — see
[Architecture § Knowledge base source](architecture.md#knowledge-base-source)
for what it reports and why it reads a table before answering rather than
reporting the configured intent. `GET /api/health/data` gives the per-table
breakdown.

On Cloud Run the file store is per-instance and resets on scale-to-zero, so a
silent fallback looks fine until the queue empties itself. That was real data
loss, not a theoretical limit.

Switching backends does not migrate anything: drafts written to the file
before the switch stay there and are simply not in the queue any more.

Signed-out reports remain in the browser's `localStorage` — per-browser, not
shared. Signing in is what moves them to Firestore and gives them an owner.

## Corporate networks

Behind a TLS-inspecting proxy, `gcloud` and the SDKs need the corporate root
CA. See the note in [`../DEPLOY.md`](../DEPLOY.md).
