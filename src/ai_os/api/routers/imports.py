"""Import/onboarding API — wraps onboarding and KnowledgeImporter."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_os.api.serialize import to_json
from ai_os.knowledge.onboarding import get_preset, load_presets, validate_import
from ai_os.knowledge.populate import KnowledgeImporter

router = APIRouter(prefix="/imports", tags=["imports"])


class ValidateBody(BaseModel):
    preset_id: str
    source_path: str


class ImportBody(BaseModel):
    preset_id: str
    source_path: str
    tags: list[str] = Field(default_factory=list)


@router.get("/presets")
def list_presets() -> list:
    return [to_json(p) for p in load_presets()]


@router.post("/validate")
def validate_import_request(body: ValidateBody) -> dict:
    preset = get_preset(body.preset_id)
    if not preset:
        raise HTTPException(404, f"Unknown preset: {body.preset_id}")
    path = Path(body.source_path).expanduser()
    if not path.exists():
        raise HTTPException(400, f"Path does not exist: {path}")
    result = validate_import(preset, path)
    return {
        "preset": to_json(result.preset),
        "source_path": str(result.source_path),
        "total_files": result.total_files,
        "new_files": result.new_files,
        "duplicate_files": result.duplicate_files,
        "unsupported_files": result.unsupported_files,
        "total_bytes": result.total_bytes,
        "estimated_seconds": result.estimated_seconds,
        "estimated_minutes": result.estimated_minutes,
        "ready": result.ready,
        "errors": result.errors,
        "files": [
            {"path": str(f.path), "size_bytes": f.size_bytes, "status": f.status, "detail": f.detail}
            for f in result.files[:100]
        ],
    }


@router.post("/run")
def run_import(body: ImportBody) -> dict:
    preset = get_preset(body.preset_id)
    if not preset:
        raise HTTPException(404, f"Unknown preset: {body.preset_id}")
    path = Path(body.source_path).expanduser()
    if not path.exists():
        raise HTTPException(400, f"Path does not exist: {path}")
    validation = validate_import(preset, path)
    if not validation.ready:
        raise HTTPException(400, {"errors": validation.errors, "ready": False})
    tags = body.tags or preset.tags
    progress = KnowledgeImporter().import_path(path, source_type=preset.source_type, tags=tags)
    from ai_os.knowledge.maintenance import MaintenanceService
    from ai_os.knowledge.config import get_settings

    MaintenanceService(get_settings()).ensure_search_indexes()
    return {
        "total": progress.total,
        "processed": progress.processed,
        "ingested": progress.ingested,
        "skipped": progress.skipped,
        "failed": progress.failed,
        "errors": progress.errors,
    }
