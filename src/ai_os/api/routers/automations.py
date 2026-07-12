"""Automations API — wraps AutomationService."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ai_os.api.serialize import to_json
from ai_os.automation.config import get_automation_settings
from ai_os.automation.service import AutomationService

router = APIRouter(prefix="/automations", tags=["automations"])


class ScheduleBody(BaseModel):
    cron: str | None = None
    interval_seconds: int | None = None
    delay_seconds: int | None = None
    run_at: str | None = None


def _service() -> AutomationService:
    return AutomationService(get_automation_settings())


@router.get("")
def list_automations() -> list:
    return [to_json(a) for a in _service().list_automations()]


@router.get("/history")
def automation_history(limit: int = Query(20, le=100)) -> list:
    return [to_json(r) for r in _service().history(limit=limit)]


@router.get("/{automation_id}")
def get_automation(automation_id: str) -> dict:
    automation = _service().get_automation(automation_id)
    if not automation:
        raise HTTPException(404, "Automation not found")
    return to_json(automation)


@router.post("/{automation_id}/run")
def run_automation(automation_id: str, token: str | None = None) -> dict:
    service = _service()
    if token:
        record = service.trigger_webhook(automation_id, token)
    else:
        record = service.run(automation_id)
    return to_json(record)


@router.post("/{automation_id}/enable")
def enable_automation(automation_id: str) -> dict:
    return to_json(_service().enable(automation_id))


@router.post("/{automation_id}/disable")
def disable_automation(automation_id: str) -> dict:
    return to_json(_service().disable(automation_id))


@router.put("/{automation_id}/schedule")
def schedule_automation(automation_id: str, body: ScheduleBody) -> dict:
    return to_json(
        _service().schedule(
            automation_id,
            cron=body.cron,
            interval_seconds=body.interval_seconds,
            delay_seconds=body.delay_seconds,
            run_at=body.run_at,
        )
    )
