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
gcloud services enable aiplatform.googleapis.com --project project-b284a92b-1eec-4e4c-add
```

Grant the runtime service account model access (the default compute
service account, unless you deploy with `--service-account`):

```bash
PROJECT_NUMBER=$(gcloud projects describe project-b284a92b-1eec-4e4c-add --format='value(projectNumber)')
gcloud projects add-iam-policy-binding project-b284a92b-1eec-4e4c-add \
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
gcloud config set project project-b284a92b-1eec-4e4c-add

gcloud run deploy mechnari-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=project-b284a92b-1eec-4e4c-add,GOOGLE_CLOUD_LOCATION=global,MECHNARI_MODEL=gemini-3.5-flash-lite \
  --memory 1Gi
```

Note the **Service URL** it prints (`https://mechnari-api-xxxxx-uc.a.run.app`).
Confirm it's actually serving before moving on:

```bash
curl https://mechnari-api-xxxxx-uc.a.run.app/api/health
# {"status":"ok"}
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
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=project-b284a92b-1eec-4e4c-add,GOOGLE_CLOUD_LOCATION=global,MECHNARI_MODEL=gemini-3.5-flash-lite,ALLOWED_ORIGINS=https://mechnari-web-xxxxx-uc.a.run.app \
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
