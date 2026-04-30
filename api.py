"""
api.py - FastAPI route definitions for Zyphraxis.

All routes are collected in `router` (an APIRouter).
main.py mounts this router onto the top-level FastAPI app.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from auth import verify_api_key, check_rate_limit
from config import API_CONFIG
from logger import zyphraxis_log

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class TreatmentRequest(BaseModel):
    tumor_escape_h: float = Field(
        ..., gt=0,
        description="Hours until estimated tumour escape (must be > 0)",
        examples=[960],
    )
    max_risk: float = Field(
        0.3, ge=0, le=1,
        description="Maximum acceptable aggregate risk score [0-1]",
        examples=[0.25],
    )
    human_use: bool = Field(
        True,
        description="Whether the patient is eligible for human-trial treatments",
    )
    mode: str = Field(
        "balanced",
        description="Optimisation mode: 'aggressive' | 'balanced' | 'conservative'",
        examples=["balanced"],
    )
    patient_id: Optional[str] = Field(
        None,
        description="Optional patient identifier (used for logging/traceability only)",
    )


class StepMetrics(BaseModel):
    total_time_h: float
    risk_score: float
    estimated_cost: float
    hla_mismatches: int
    confidence: float


class TreatmentResponse(BaseModel):
    status: str
    plan: List[Dict[str, Any]]
    metrics: Optional[StepMetrics] = None
    explanation: str
    timestamp: str
    request_id: Optional[str] = None
    alternatives: int = 0


class LearnRequest(BaseModel):
    plan: Any = Field(..., description="The plan dict previously returned by /generate_plan")
    observed_time_h: float = Field(..., gt=0, description="Actual observed treatment time in hours")
    observed_risk: float   = Field(..., ge=0, le=1, description="Observed risk outcome [0-1]")


# ---------------------------------------------------------------------------
# Helper: get engine from app.state
# ---------------------------------------------------------------------------

def _get_engine(request: Request):
    engine = getattr(request.app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Engine not initialised")
    return engine


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/health", tags=["meta"])
def health_check():
    """Liveness probe. Returns 200 when the service is running."""
    return {"status": "healthy", "version": API_CONFIG["version"]}


@router.get("/scenarios", tags=["meta"])
def list_scenarios():
    """Return the list of pre-built demo scenarios."""
    try:
        with open("scenarios.json", "r") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return []


@router.post("/generate_plan", response_model=TreatmentResponse, tags=["planning"])
def generate_plan(
    request: TreatmentRequest,
    http_request: Request,
    api_key_data: dict = Depends(verify_api_key),
):
    """
    Generate the optimal treatment plan for a patient.

    Returns a TreatmentResponse with status 'success' when a plan is found,
    or 'NO_PATH' when no plan satisfies the given constraints.
    """
    engine   = _get_engine(http_request)
    start    = time.time()
    req_dict = request.model_dump()

    zyphraxis_log.log_request(req_dict, request.patient_id)
    check_rate_limit(api_key_data)

    try:
        result = engine.run_planner(
            tumor_escape_h = request.tumor_escape_h,
            max_risk       = request.max_risk,
            human_use      = request.human_use,
            mode           = request.mode,
        )
    except Exception as exc:
        zyphraxis_log.log_error(exc, req_dict)
        raise HTTPException(status_code=500, detail=f"Brain execution failed: {exc}") from exc

    latency_ms = round((time.time() - start) * 1_000, 2)
    ts         = datetime.now(timezone.utc).isoformat()

    if result.get("status") in ("NO_PATH", "INVALID_INPUT") or not result.get("plan"):
        explanation = result.get("explanation", "No viable treatment path under given constraints.")
        zyphraxis_log.log_no_path(explanation, req_dict)
        response = TreatmentResponse(
            status       = result.get("status", "NO_PATH"),
            plan         = [],
            metrics      = None,
            explanation  = explanation,
            timestamp    = ts,
            request_id   = request.patient_id,
            alternatives = 0,
        )
    else:
        metrics_raw = result.get("metrics") or {}
        response = TreatmentResponse(
            status       = result["status"],
            plan         = result["plan"],
            metrics      = StepMetrics(**metrics_raw),
            explanation  = result["explanation"],
            timestamp    = ts,
            request_id   = request.patient_id,
            alternatives = result.get("alternatives", 0),
        )

    zyphraxis_log.log_response(response.model_dump(), request.patient_id, latency_ms)
    return response


@router.post("/learn", status_code=200, tags=["learning"])
def learn(request: LearnRequest, http_request: Request):
    """
    Submit observed outcomes to update the engine's learning memory.
    """
    engine = _get_engine(http_request)
    try:
        engine.update_from_outcome(
            plan          = request.plan,
            observed_time = request.observed_time_h,
            observed_risk = request.observed_risk,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Learning update failed: {exc}") from exc

    zyphraxis_log.log_learn({
        "observed_time_h": request.observed_time_h,
        "observed_risk":   request.observed_risk,
    })
    return {"status": "updated"}
