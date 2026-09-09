"""
Mechnari.ai - HTTP API
=======================
A thin FastAPI wrapper around the same deterministic engines the Streamlit
app calls directly - data_layer, gap_detection, risk_engine, retrieval,
backtest, queue_store, and the ADK agent. Nothing in this file computes
anything: every route is a call into an already-tested module and a JSON
shaping of its return value. This is what the Next.js frontend talks to;
Streamlit keeps working unchanged, calling the same modules in-process.

Run with:  uvicorn api:app --reload --port 8000
"""

import os
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import agui_endpoint
import backtest
import data_layer
import dfmea_sheet
import gap_detection
import queue_store
import retrieval
import risk_engine
from mechnari_agent import agent as mechnari_agent

app = FastAPI(title="Mechnari.ai API", version="1.0.0")

# The Next.js dev server by default. The deployed frontend origin is added
# via ALLOWED_ORIGINS (comma-separated) as a Cloud Run env var - never "*",
# because this API can trigger a knowledge-base reload and read the draft
# queue, neither of which should be reachable cross-origin from an
# untrusted page.
_extra_origins = [
    origin.strip()
    for origin in os.environ.get("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", *_extra_origins],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """A JSON-safe list of records, NaN turned into null rather than the
    invalid-JSON literal `NaN` pandas would otherwise emit."""
    return df.astype(object).where(pd.notnull(df), None).to_dict("records")


def _dataset_error(exc: data_layer.DatasetError) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/parts")
def get_parts(system_package: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        parts = data_layer.parts()
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)
    if system_package:
        parts = parts[parts["system_package"] == system_package]
    return _records(parts)


@app.get("/api/system-packages")
def get_system_packages() -> List[str]:
    try:
        parts = data_layer.parts()
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)
    return sorted(parts["system_package"].unique().tolist())


@app.get("/api/part-types")
def get_part_types() -> List[Dict[str, Any]]:
    try:
        return _records(data_layer.part_types())
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)


class ProposeRequest(BaseModel):
    part_name: str
    function: str = ""
    material: str = ""
    part_type_id: str = ""


@app.post("/api/propose-dfmea")
def propose_dfmea(req: ProposeRequest) -> Dict[str, Any]:
    query = retrieval.describe(req.part_name, req.function, req.material)
    if not query.strip():
        raise HTTPException(400, "Describe the part before asking for a proposal.")
    try:
        proposal = retrieval.propose_dfmea(query, part_type_id=req.part_type_id or None)
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)
    except KeyError:
        raise HTTPException(400, "Unknown part_type_id.")

    if proposal["status"] != "success":
        return {"status": proposal["status"], "reason": proposal["reason"]}

    # The levers ride along with the row rather than being fetched per row.
    # find_ap_levers is a pure table lookup, so computing 20-odd of them here
    # costs nothing and saves the client a request per High row.
    candidates = _records(proposal["candidates"])
    for row in candidates:
        row["levers"] = risk_engine.find_ap_levers(
            int(row["severity"]), int(row["occurrence"]), int(row["detection"])
        )["levers"]

    return {
        "status": "success",
        "reason": proposal["reason"],
        "confident": proposal["confident"],
        "confirmed": proposal["confirmed"],
        "part_type_id": proposal["part_type_id"],
        "part_type_name": proposal["part_type_name"],
        "family_name": proposal["family_name"],
        "confidence": proposal["confidence"],
        "safety_candidates": proposal["safety_candidates"],
        "neighbours": _records(proposal["neighbours"]),
        "candidates": candidates,
    }


class SheetItem(BaseModel):
    part_number: str = ""
    description: str = ""
    function: str = ""
    material: str = ""
    system_package: str = ""
    part_type_id: str = ""
    existing_part_id: str = ""


class SheetRequest(BaseModel):
    # One entry for a single part, several for a package/assembly. The
    # shape is the same either way so the frontend does not need two
    # request paths for what is one operation repeated.
    items: List[SheetItem]


@app.post("/api/dfmea-sheet")
def dfmea_sheet_route(req: SheetRequest) -> Dict[str, Any]:
    if not req.items:
        raise HTTPException(400, "Send at least one part.")
    if len(req.items) > 25:
        raise HTTPException(400, "At most 25 parts per package in one request.")
    try:
        return dfmea_sheet.build([item.model_dump() for item in req.items])
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)
    except KeyError:
        raise HTTPException(400, "Unknown part_type_id.")


class LeverRequest(BaseModel):
    severity: int
    occurrence: int
    detection: int


@app.post("/api/ap-levers")
def ap_levers(req: LeverRequest) -> Dict[str, Any]:
    return risk_engine.find_ap_levers(req.severity, req.occurrence, req.detection)


class DraftRow(BaseModel):
    mode_id: str
    failure_mode: str
    potential_cause: str
    effect_description: str
    severity: int
    occurrence: int
    detection: int
    action_priority: str
    learned_from: str
    evidence_ids: str
    recommended_action: str


class SubmitDraftRequest(BaseModel):
    part_name: str
    function: str
    material: str
    system_package: str
    part_type_name: str
    accepted_rows: List[DraftRow]
    declined_rows: List[DraftRow]
    submitted_by: str = "Design Engineer"


@app.post("/api/queue/submit")
def submit_draft(req: SubmitDraftRequest) -> Dict[str, str]:
    draft_id = queue_store.submit_draft(
        part_name=req.part_name, function=req.function, material=req.material,
        system_package=req.system_package, part_type_name=req.part_type_name,
        accepted_rows=[r.model_dump() for r in req.accepted_rows],
        declined_rows=[r.model_dump() for r in req.declined_rows],
        submitted_by=req.submitted_by,
    )
    return {"draft_id": draft_id}


@app.get("/api/queue")
def list_queue() -> List[Dict[str, Any]]:
    return queue_store.list_queue()


@app.get("/api/queue/{draft_id}")
def get_draft(draft_id: str) -> Dict[str, Any]:
    draft = queue_store.get_draft(draft_id)
    if draft is None:
        raise HTTPException(404, "Unknown draft_id: %s" % draft_id)
    return draft


class StatusRequest(BaseModel):
    status: str
    comments: str = ""


@app.post("/api/queue/{draft_id}/status")
def set_draft_status(draft_id: str, req: StatusRequest) -> Dict[str, bool]:
    try:
        ok = queue_store.set_status(draft_id, req.status, req.comments)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if not ok:
        raise HTTPException(404, "Unknown draft_id: %s" % draft_id)
    return {"ok": True}


@app.get("/api/audit/{part_id}")
def audit_part(part_id: str) -> Dict[str, Any]:
    try:
        parts = data_layer.parts()
        sev_all = gap_detection.severity_consistency_findings()
        occ_all = risk_engine.occurrence_findings()
        gaps = gap_detection.detect_gaps(part_id)
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)
    except KeyError:
        raise HTTPException(404, "Unknown part_id: %s" % part_id)

    part_row = parts[parts["part_id"] == part_id]
    return {
        "part": _records(part_row)[0] if not part_row.empty else None,
        "severity_findings": _records(sev_all[sev_all["part_id"] == part_id]),
        "occurrence_findings": _records(occ_all[occ_all["part_id"] == part_id]),
        "gaps": _records(gaps),
    }


@app.get("/api/issues/summary")
def issue_summary() -> List[Dict[str, Any]]:
    """Every part with a warranty issue on record - active or retired - and
    how many. Company-wide visibility into what's actually gone wrong,
    independent of what any one DFMEA says."""
    try:
        return _records(data_layer.issue_summary())
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)


@app.get("/api/issues/{part_id}")
def issues_for_part(part_id: str) -> List[Dict[str, Any]]:
    try:
        return _records(data_layer.issue_history(part_id))
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)


@app.get("/api/gaps")
def all_gaps(system_package: Optional[str] = None) -> List[Dict[str, Any]]:
    try:
        gaps = gap_detection.detect_gaps()
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)
    if system_package:
        gaps = gaps[gaps["system_package"] == system_package]
    return _records(gaps)


@app.get("/api/gap-metrics")
def gap_metrics() -> Dict[str, Any]:
    try:
        return gap_detection.headline_metrics()
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)


@app.get("/api/risk-metrics")
def risk_metrics() -> Dict[str, Any]:
    try:
        return risk_engine.headline_metrics()
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)


@app.get("/api/backtest")
def backtest_detail(cutoff: str = backtest.DEFAULT_CUTOFF) -> Dict[str, Any]:
    try:
        result = backtest.temporal_backtest(cutoff)
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)
    return {
        "cutoff": cutoff,
        "summary": result["summary"],
        "train_records": result["train_records"],
        "test_records": result["test_records"],
        "detail": _records(result["detail"]),
    }


@app.get("/api/backtest/sweep")
def backtest_sweep() -> List[Dict[str, Any]]:
    try:
        return _records(backtest.sweep())
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)


@app.get("/api/backtest/cold-start")
def backtest_cold_start() -> Dict[str, Any]:
    try:
        result = backtest.cold_start_backtest()
    except data_layer.DatasetError as exc:
        raise _dataset_error(exc)
    result.pop("detail", None)
    return result


@app.get("/api/backtest/cutoffs")
def backtest_cutoffs() -> Dict[str, Any]:
    return {"cutoffs": backtest.CUTOFF_SWEEP, "default": backtest.DEFAULT_CUTOFF}


class CopilotRequest(BaseModel):
    question: str
    session_id: str = "web"


@app.post("/api/copilot/ask")
def copilot_ask(req: CopilotRequest) -> Dict[str, Any]:
    # ask_copilot is a synchronous function that runs its own event loop
    # internally (asyncio.run). FastAPI calls plain `def` routes - this one
    # included - in a worker thread, which has no event loop of its own, so
    # that nested asyncio.run() is safe here. Making this route `async def`
    # instead would break it (asyncio.run cannot nest inside a running loop).
    return mechnari_agent.ask_copilot(req.question, session_id=req.session_id)


@app.post("/api/reload")
def reload_knowledge_base() -> Dict[str, bool]:
    data_layer.reload()
    retrieval.reload()
    return {"ok": True}


@app.get("/api/copilot/health")
def copilot_health() -> Dict[str, Any]:
    """Whether the streaming copilot can be expected to work, so the
    frontend can say something honest before opening an SSE stream that is
    only going to fail on auth."""
    check = agui_endpoint.api_key_works()
    return {"api_key_present": agui_endpoint.api_key_present(),
            "api_key_works": check["ok"],
            "reason": check["reason"],
            "agui_path": agui_endpoint.AGUI_PATH}


# Mounted last, and deliberately at the end of this file: the AG-UI
# endpoint streams Server-Sent Events for the CopilotKit frontend, which is
# a different transport from every JSON route above. Same agent, same
# tools, same rule that agents never write a score - only the delivery
# differs. /api/copilot/ask stays as the synchronous fallback.
agui_endpoint.mount(app)
