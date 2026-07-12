"""Model routing API — wraps ModelRouter and profiles."""

from __future__ import annotations

from fastapi import APIRouter

from ai_os.api.serialize import to_json
from ai_os.routing.config import RoutingSettings
from ai_os.routing.models import ModelRequest, RoutingPriority
from ai_os.routing.profiles import list_profiles
from ai_os.routing.router import ModelRouter

router = APIRouter(prefix="/models", tags=["models"])


class RouteRequestBody(ModelRequest):
    pass


@router.get("")
def list_models() -> list:
    return [to_json(p) for p in list_profiles()]


@router.get("/routing")
def routing_settings() -> dict:
    settings = RoutingSettings()
    return to_json(settings)


@router.post("/route")
def route_model(body: ModelRequest) -> dict:
    route = ModelRouter().route(body)
    return to_json(route)
