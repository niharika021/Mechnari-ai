# Deploying Mechnari.ai to Cloud Run

Two services, deployed in order — the API first, because the frontend needs
its URL baked in at build time.

## Prerequisites

- A Google Cloud project with billing enabled
- `gcloud` CLI, authenticated: `gcloud auth login`
- The APIs this needs, enabled once per project:

  ```bash
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
  ```

- `GEMINI_API_KEY` — a valid key from <https://aistudio.google.com/apikey>.
  Every score, gap and backtest figure works without one; only the copilot's
  prose explanations need it.

## 1. Deploy the API

From the repository root — `gcloud run deploy --source .` builds the
container in the cloud via Cloud Build, so no local Docker is required:

```bash
gcloud config set project mechnari-ai-82319

gcloud run deploy mechnari-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=<your fresh key from aistudio.google.com/apikey>,GOOGLE_API_KEY=<your fresh key from aistudio.google.com/apikey> \
  --memory 1Gi
```

Note the **Service URL** it prints (`https://mechnari-api-xxxxx-uc.a.run.app`).
Confirm it's actually serving before moving on:

```bash
curl https://mechnari-api-xxxxx-uc.a.run.app/api/health
# {"status":"ok"}
```

For a real deployment (not a demo), prefer Secret Manager over
`--set-env-vars` for the key:

```bash
echo -n "<your fresh key from aistudio.google.com/apikey>" | gcloud secrets create gemini-api-key --data-file=-
gcloud run deploy mechnari-api --source . --region us-central1 \
  --allow-unauthenticated \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest,GOOGLE_API_KEY=gemini-api-key:latest \
  --memory 1Gi
```

## 2. Deploy the frontend

`NEXT_PUBLIC_API_BASE` is compiled into the client bundle at build time, so
it has to be the API's real URL from step 1 — not `localhost`. From `web/`:

```bash
cd web

gcloud run deploy mechnari-web \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-build-env-vars NEXT_PUBLIC_API_BASE=https://mechnari-api-xxxxx-uc.a.run.app \
  --memory 512Mi
```

## 3. Close the loop — CORS

The API only accepts requests from `localhost:3000` until you tell it about
the deployed frontend's real origin. Redeploy the API with that origin added:

```bash
gcloud run deploy mechnari-api --source . --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GEMINI_API_KEY=<your fresh key from aistudio.google.com/apikey>,GOOGLE_API_KEY=<your fresh key from aistudio.google.com/apikey>,ALLOWED_ORIGINS=https://mechnari-web-xxxxx-uc.a.run.app \
  --memory 1Gi
```

## 4. Verify

Open the `mechnari-web` URL and walk the same path used to verify this
locally: `/design` → identify & draft → submit → `/quality` → approve →
`/company` shows the rollup. Check `read_console_messages` / browser
devtools for CORS errors if a fetch silently fails — that means step 3 was
skipped or the origin doesn't match exactly (scheme + host + no trailing
slash).

## What does *not* survive a redeploy

`queue_store.py` writes the draft review queue to a JSON file in the
container's own filesystem. Cloud Run's filesystem is per-instance and
resets on scale-to-zero or a new revision — fine for a live demo, not a
durable store. The real fix (swapping `queue_store` for Firestore or
Cloud SQL) is future work; the module's write/read interface is small
enough that nothing above it should need to change.

## Local equivalents, for comparison

```bash
py -m uvicorn api:app --port 8000 --reload      # API
npm --prefix web run dev                         # frontend
streamlit run app.py                              # Streamlit fallback
```

Also runnable via `.claude/launch.json`.
