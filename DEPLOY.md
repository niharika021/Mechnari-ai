# Deploying Mechnari.ai to Cloud Run

Two services, deployed in order — the API first, because the frontend needs
its URL baked in at build time.

**Currently deployed:**

| Service | URL |
| --- | --- |
| Frontend | <https://mechnari-web-1041795730182.us-central1.run.app> |
| API | <https://mechnari-api-1041795730182.us-central1.run.app> |

Every step below was run against project `project-b5c60fe1-dbb8-4eb8-84b`
and verified live: all three role views return 200, the metrics match the
local figures exactly (50/50 parts, 57% coverage, 15 safety gaps, +27 pts),
and the copilot answers citing real 8D records with no API key anywhere —
Vertex authenticates as the Cloud Run service account.

## Prerequisites

- A Google Cloud project with billing enabled
- `gcloud` CLI, authenticated: `gcloud auth login`
- The APIs this needs, enabled once per project:

  ```bash
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
  ```

- **On a fresh project, grant the build service account its roles.** Cloud
  Run source deploys upload to a staging bucket and build as the compute
  service account; without these the deploy fails with
  `does not have storage.objects.get access to the Google Cloud Storage
  object`:

  ```bash
  PROJECT_ID=project-b5c60fe1-dbb8-4eb8-84b
  PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
  SA=${PROJECT_NUMBER}-compute@developer.gserviceaccount.com
  for ROLE in roles/cloudbuild.builds.builder roles/storage.objectViewer \
              roles/artifactregistry.writer roles/logging.logWriter; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
      --member="serviceAccount:$SA" --role="$ROLE"
  done
  ```

### What gets uploaded

`.gcloudignore` (root, and one in `web/`) controls this, and it matters:
without it gcloud falls back to the **top-level** `.gitignore` only — it
does not read nested ones like `web/.gitignore`. That meant `web/.next/`
and `node_modules/` were uploaded, and the deploy died on the running dev
server's lock file (`PermissionError: web\.next\dev\lock`).

### Model access: use Vertex AI, not an AI Studio key

The copilot reaches Gemini through **Vertex AI**, authenticated by the
service account Cloud Run already runs as. There is no API key to set,
leak or rotate.

This is not only a preference. As of September 2026 the API keys AI Studio
issues (the new `AQ.` "Auth key" format that replaced `AIza`) return
`401 ACCESS_TOKEN_TYPE_UNSUPPORTED` against the Generative Language API —
a known Google-side issue with no published fix, reproduced here on the
latest SDK with both `x-goog-api-key` and bearer auth. Vertex avoids that
path entirely.

```bash
gcloud services enable aiplatform.googleapis.com --project project-b5c60fe1-dbb8-4eb8-84b
```

Grant the runtime service account model access (the default compute
service account, unless you deploy with `--service-account`):

```bash
PROJECT_NUMBER=$(gcloud projects describe project-b5c60fe1-dbb8-4eb8-84b --format='value(projectNumber)')
gcloud projects add-iam-policy-binding project-b5c60fe1-dbb8-4eb8-84b \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

**Model names and regions do not carry over from AI Studio.** Vertex serves
versioned publisher models, so AI Studio's floating aliases 404 there
(`gemini-flash-latest` does not resolve). Availability is also regional:
`gemini-3.5-flash-lite` serves from `global` but 404s in `us-central1`,
`us-east5` and `europe-west4`. Check before changing either:

```bash
py -c "import google.genai as g; [print(m.name) for m in g.Client().models.list()]"
```

Every score, gap and backtest figure works with no model access at all —
only the copilot's prose needs it.

#### Behind a TLS-inspecting corporate network

If `gcloud` fails with `CERTIFICATE_VERIFY_FAILED — self-signed
certificate in certificate chain`, its bundled Python does not trust the
corporate root CA. Point it at a bundle that does rather than disabling
verification:

```bash
gcloud config set core/custom_ca_certs_file /path/to/ca-bundle.pem
```

On this machine that bundle was generated from the Windows trust store and
the setting is already persisted in gcloud's config.

## 1. Deploy the API

From the repository root — `gcloud run deploy --source .` builds the
container in the cloud via Cloud Build, so no local Docker is required:

```bash
gcloud config set project project-b5c60fe1-dbb8-4eb8-84b

gcloud run deploy mechnari-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=project-b5c60fe1-dbb8-4eb8-84b,GOOGLE_CLOUD_LOCATION=global,MECHNARI_MODEL=gemini-3.7-flash \
  --memory 1Gi
```

Note the **Service URL** it prints (`https://mechnari-api-xxxxx-uc.a.run.app`).
Confirm it's actually serving before moving on:

```bash
curl https://mechnari-api-xxxxx-uc.a.run.app/api/health
# {"status":"ok"}
```

## 2. Deploy the frontend — build, then deploy

`NEXT_PUBLIC_API_BASE` is compiled into the client bundle at build time, so
it has to be the API's real URL from step 1 — not `localhost`.

**This needs two commands, not one.** `gcloud run deploy --source .` cannot
supply it: `--set-build-env-vars` configures a *buildpacks* build and does
**not** populate a Dockerfile's `ARG`. With a Dockerfile the ARG stays
empty, the API base compiles to `""`, every request URL comes out relative,
and server-side rendering fails with:

```
TypeError: Failed to parse URL from /api/gap-metrics
```

which returns 500 on every page. This only shows up in the cloud — local
builds always work, because `.env.local` supplies the value.

So build the image explicitly with the build arg (`web/cloudbuild.yaml`
exists for this), then deploy that image. From the repository root:

```bash
API_URL=https://mechnari-api-xxxxx-uc.a.run.app
IMAGE=us-central1-docker.pkg.dev/project-b5c60fe1-dbb8-4eb8-84b/cloud-run-source-deploy/mechnari-web:latest

# The four Firebase values are NEXT_PUBLIC_*, so they are compiled in at
# build time exactly like the API base - passing them at run time does
# nothing. Omitting them is not an error: the build succeeds and the app
# works, just permanently signed out with the sign-in button hidden, which
# is a confusing thing to debug later. Copy them from web/.env.local.
gcloud builds submit web \
  --config web/cloudbuild.yaml \
  --substitutions=_API_BASE=$API_URL,_IMAGE=$IMAGE,_FB_API_KEY=$FB_API_KEY,_FB_AUTH_DOMAIN=$FB_AUTH_DOMAIN,_FB_PROJECT_ID=$FB_PROJECT_ID,_FB_APP_ID=$FB_APP_ID

gcloud run deploy mechnari-web \
  --image $IMAGE \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars COPILOTKIT_TELEMETRY_DISABLED=true,API_BASE_INTERNAL=$API_URL \
  --memory 512Mi
```

`API_BASE_INTERNAL` is read at run time by the CopilotKit runtime route,
which proxies to the AG-UI endpoint server-side.

## 3. Close the loop — CORS

The API only accepts requests from `localhost:3000` until you tell it about
the deployed frontend's real origin. This is an env-var change, so use
`services update` rather than redeploying — no rebuild needed:

```bash
gcloud run services update mechnari-api --region us-central1 \
  --update-env-vars ALLOWED_ORIGINS=https://mechnari-web-xxxxx-uc.a.run.app
```

## 4. Verify

Open the `mechnari-web` URL and walk the same path used to verify this
locally: `/design` → identify & draft → submit → `/quality` → approve →
`/company` shows the rollup. Check `read_console_messages` / browser
devtools for CORS errors if a fetch silently fails — that means step 3 was
skipped or the origin doesn't match exactly (scheme + host + no trailing
slash).

## The review queue: Firestore

The draft review queue is in Firestore, not on the container's disk. That
matters because Cloud Run's filesystem is per-instance and resets on
scale-to-zero — a draft could be submitted, the service could idle, and
the Quality queue would come back empty. That was real data loss, not a
theoretical limit.

Enabled once per project:

```bash
gcloud services enable firestore.googleapis.com --project project-b5c60fe1-dbb8-4eb8-84b
gcloud firestore databases create --location=nam5 --type=firestore-native \
  --project project-b5c60fe1-dbb8-4eb8-84b
```

The runtime service account needs read/write:

```bash
PROJECT_NUMBER=$(gcloud projects describe project-b5c60fe1-dbb8-4eb8-84b --format='value(projectNumber)')
gcloud projects add-iam-policy-binding project-b5c60fe1-dbb8-4eb8-84b \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/datastore.user"
```

`GOOGLE_CLOUD_PROJECT` is already among the API's env vars (Vertex needs
it too), so nothing else has to be set — `queue_store` picks Firestore up
from it.

**Check which store a deployment actually landed on.** `/api/health`
reports it, because a silent fall back to the ephemeral file is precisely
the failure this replaced:

```bash
curl https://mechnari-api-xxxxx-uc.a.run.app/api/health
# {"status":"ok","queue_backend":"firestore"}   <- what you want
# {"status":"ok","queue_backend":"file"}        <- the queue will empty itself
```

`queue_store` keeps the JSON file as a fallback when no project is
configured, so local development and the test suite run with no cloud
access. Switching backends does not migrate anything: drafts written to
the file before the switch stay there and are simply not in the queue any
more.

## The knowledge base: BigQuery, CSV fallback

BigQuery is the source of record for the seven knowledge-base tables — parts,
failure modes, warranty history and the rest — when `MECHNARI_DATA_SOURCE=bigquery`
is set on the API service. Unset, or on any BigQuery failure, `data_layer`
reads `data/*.csv` instead, so this is safe to add after the fact, which is
how it was actually done here: deployed first without it, added with a
`services update` exactly like the CORS step below.

Enabled once per project:

```bash
gcloud services enable bigquery.googleapis.com --project project-b5c60fe1-dbb8-4eb8-84b
```

Load the dataset — creates it, loads `data/*.csv`, and verifies row-for-row
against the CSVs it just read:

```bash
py bq_load.py
```

**Grant the runtime service account READER on the dataset, not
`roles/bigquery.dataViewer` project-wide.** There is no `bq` CLI on every
machine, so this used the Python client directly rather than a `bq
add-iam-policy-binding` this repo could not verify works everywhere:

```python
from google.cloud import bigquery
client = bigquery.Client(project="project-b5c60fe1-dbb8-4eb8-84b")
ds = client.get_dataset("project-b5c60fe1-dbb8-4eb8-84b.mechnari_engineering")
entries = list(ds.access_entries) + [bigquery.AccessEntry(
    role="READER", entity_type="userByEmail",
    entity_id="1041795730182-compute@developer.gserviceaccount.com")]
ds.access_entries = entries
client.update_dataset(ds, ["access_entries"])
```

Then point the API at it:

```bash
gcloud run services update mechnari-api --region us-central1 \
  --update-env-vars MECHNARI_DATA_SOURCE=bigquery,MECHNARI_BQ_DATASET=mechnari_engineering
```

`--update-env-vars` rather than `--set-env-vars`, same reason as the CORS
step below: the latter *replaces* the whole set, and silently dropped
`ALLOWED_ORIGINS` here once already.

**Verify what actually served the request**, not what was configured:

```bash
curl https://mechnari-api-xxxxx-uc.a.run.app/api/health
# {"status":"ok", ..., "data_source":"bigquery"}  <- what you want
# {"status":"ok", ..., "data_source":"csv"}        <- fell back; check /api/health/data for why
```

A cold process answering `bigquery` before it had read a single table was a
real bug here — `data_source` now reads one small table before answering,
specifically so this check means what it says.

## What still does *not* survive

The design engineer's own in-progress reports are in the browser's
localStorage, not Firestore. They are per-browser and not shared. Moving
them needs an identity to attach them to, and this app has none — the
three roles are tabs, not accounts. That is a product decision about
identity rather than a migration, so it is deliberately still open.

## Local equivalents, for comparison

```bash
py -m uvicorn api:app --port 8000 --reload      # API
npm --prefix web run dev                         # frontend
```

Also runnable via `.claude/launch.json`.
