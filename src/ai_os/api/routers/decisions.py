"""Decisions API — wraps DecisionPipeline and DecisionStore."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ai_os.api.serialize import to_json
from ai_os.decision.config import get_decision_settings
from ai_os.decision.models import DecisionRequest
from ai_os.decision.pipeline import DecisionPipeline
from ai_os.decision.store import DecisionStore
from ai_os.decision.strategies import list_strategies

router = APIRouter(prefix="/decisions", tags=["decisions"])


@router.get("")
def list_decisions() -> list:
    return [to_json(d) for d in DecisionStore(get_decision_settings()).list_all()]


@router.get("/strategies")
def get_strategies() -> list:
    return [{"name": s.value} for s in list_strategies()]


@router.get("/{decision_id}")
def get_decision(decision_id: str) -> dict:
    result = DecisionStore(get_decision_settings()).get(decision_id)
    if not result:
        raise HTTPException(404, "Decision not found")
    return to_json(result)


@router.post("")
def create_decision(request: DecisionRequest) -> dict:
    result = DecisionPipeline().decide(request)
    return to_json(result)
