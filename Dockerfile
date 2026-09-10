# Mechnari.ai API - deployed to Cloud Run.
#
# This container is the whole Python side: the deterministic engines
# (data_layer, gap_detection, risk_engine, retrieval, backtest, queue_store)
# and the ADK agent, reached through api.py.
FROM python:3.11-slim

WORKDIR /app

# Layer the dependency install separately from the source copy so a code
# change doesn't invalidate the (slow) google-adk / scikit-learn install.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Every module, not a hand-written list of them. The list version went
# stale the moment new modules appeared and failed the deploy with
# "ModuleNotFoundError: No module named 'auth'" - auth.py, report_store.py
# and dfmea_sheet.py had all been added without it. A manifest that has no
# mechanism to stay correct will drift, and it drifts silently until the
# container will not start.
#
# What must NOT ship is excluded in .dockerignore instead: tests, the
# frontend, local state, secrets. That is one place to look, and adding a
# module cannot break it.
COPY *.py ./
COPY mechnari_agent/ ./mechnari_agent/
COPY data/ ./data/

# Cloud Run injects PORT; uvicorn must bind to it, not a hardcoded 8000.
ENV PORT=8080
EXPOSE 8080
CMD exec uvicorn api:app --host 0.0.0.0 --port ${PORT}
