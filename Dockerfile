# Mechnari.ai API - deployed to Cloud Run.
#
# This container is the whole Python side: the deterministic engines
# (data_layer, gap_detection, risk_engine, retrieval, backtest, queue_store)
# and the ADK agent, reached through api.py. Streamlit (app.py) is not
# built here - it stays a local/dev-only entry point into the same engines.
FROM python:3.11-slim

WORKDIR /app

# Layer the dependency install separately from the source copy so a code
# change doesn't invalidate the (slow) google-adk / scikit-learn install.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY taxonomy.py data_layer.py gap_detection.py risk_engine.py retrieval.py \
     backtest.py queue_store.py mechnari_tools.py api.py ./
COPY mechnari_agent/ ./mechnari_agent/
COPY data/ ./data/

# Cloud Run injects PORT; uvicorn must bind to it, not a hardcoded 8000.
ENV PORT=8080
EXPOSE 8080
CMD exec uvicorn api:app --host 0.0.0.0 --port ${PORT}
