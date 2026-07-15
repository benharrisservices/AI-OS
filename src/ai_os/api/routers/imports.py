"""Import/onboarding API — wraps onboarding and KnowledgeImporter."""

from __future__ import annotations

import re
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from ai_os.api.auth import require_api_key
from ai_os.api.serialize import to_json
from ai_os.knowledge.onboarding import SUPPORTED_SUFFIXES, get_preset, load_presets, validate_import
from ai_os.knowledge.populate import KnowledgeImporter

router = APIRouter(prefix="/imports", tags=["imports"])

# Upload safety limits
_MAX_FILES = 20
_MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB per file
_MAX_TOTAL_BYTES = 50 * 1024 * 1024  # 50 MB per request
_BLOCKED_SUFFIXES = {
    ".exe", ".bin", ".dll", ".so", ".dylib",
    ".sh", ".bash", ".zsh", ".bat", ".cmd", ".ps1",
    ".env", ".pem", ".key", ".p12", ".pfx", ".crt",
    ".wasm", ".jar", ".apk", ".dmg", ".iso",
}
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class ValidateBody(BaseModel):
    preset_id: str
    source_path: str


class ImportBody(BaseModel):
    preset_id: str
    source_path: str
    tags: list[str] = Field(default_factory=list)


def _safe_filename(original: str | None) -> str:
    raw = Path(original or "").name  # strip client path components
    if not raw or raw in {".", ".."}:
        raise HTTPException(400, "Invalid filename")
    if ".." in raw or "/" in raw or "\\" in raw:
        raise HTTPException(400, f"Path traversal rejected: {original}")
    suffix = Path(raw).suffix.lower()
    if suffix in _BLOCKED_SUFFIXES:
        raise HTTPException(400, f"Blocked file type: {suffix}")
    if suffix not in SUPPORTED_SUFFIXES:
        raise HTTPException(
            400,
            f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(SUPPORTED_SUFFIXES))}",
        )
    stem = _SAFE_NAME.sub("_", Path(raw).stem).strip("._") or "upload"
    stem = stem[:80]
    return f"{stem}-{uuid.uuid4().hex[:8]}{suffix}"


@router.get("/presets")
def list_presets() -> list:
    return [to_json(p) for p in load_presets()]


@router.post("/validate", dependencies=[Depends(require_api_key)])
def validate_import_request(body: ValidateBody) -> dict:
    preset = get_preset(body.preset_id)
    if not preset:
        raise HTTPException(404, f"Unknown preset: {body.preset_id}")
    path = Path(body.source_path).expanduser()
    if not path.exists():
        raise HTTPException(400, f"Path does not exist: {path}")
    result = validate_import(body.preset_id, path)
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


@router.post("/run", dependencies=[Depends(require_api_key)])
def run_import(body: ImportBody) -> dict:
    preset = get_preset(body.preset_id)
    if not preset:
        raise HTTPException(404, f"Unknown preset: {body.preset_id}")
    path = Path(body.source_path).expanduser()
    if not path.exists():
        raise HTTPException(400, f"Path does not exist: {path}")
    validation = validate_import(body.preset_id, path)
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


@router.post("/upload", dependencies=[Depends(require_api_key)])
async def upload_import(
    files: list[UploadFile] = File(...),
    preset_id: str = Form(...),
    tags: str = Form(""),
) -> dict:
    """Authenticated upload-based ingestion for production.

    Files are stored under the persistent knowledge raw dir and passed through
    the existing KnowledgeImporter — no duplicated parse/chunk/index logic.
    """
    from ai_os.knowledge.config import get_settings
    from ai_os.knowledge.health import HealthService
    from ai_os.knowledge.maintenance import MaintenanceService

    if not files:
        raise HTTPException(400, "No files were uploaded")
    if len(files) > _MAX_FILES:
        raise HTTPException(400, f"Too many files (max {_MAX_FILES})")

    preset = get_preset(preset_id)
    if not preset:
        known = ", ".join(p.id for p in load_presets())
        raise HTTPException(
            404,
            f"Unknown preset: {preset_id}. Select one of: {known}",
        )

    settings = get_settings()
    settings.ensure_dirs()
    dest = settings.knowledge_raw_dir / "uploads" / f"upload-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    dest.mkdir(parents=True, exist_ok=True)

    saved = 0
    total_bytes = 0
    rejections: list[str] = []

    for upload in files:
        try:
            safe_name = _safe_filename(upload.filename)
        except HTTPException as exc:
            rejections.append(str(exc.detail))
            continue

        data = await upload.read()
        size = len(data)
        if size == 0:
            rejections.append(f"{upload.filename}: empty file rejected")
            continue
        if size > _MAX_FILE_BYTES:
            rejections.append(
                f"{upload.filename}: exceeds per-file limit "
                f"({_MAX_FILE_BYTES // (1024 * 1024)} MB)"
            )
            continue
        if total_bytes + size > _MAX_TOTAL_BYTES:
            rejections.append(
                f"{upload.filename}: would exceed total request limit "
                f"({_MAX_TOTAL_BYTES // (1024 * 1024)} MB)"
            )
            break

        (dest / safe_name).write_bytes(data)
        total_bytes += size
        saved += 1

    if saved == 0:
        raise HTTPException(
            400,
            {
                "errors": rejections or ["No valid files were uploaded"],
                "ready": False,
            },
        )

    validation = validate_import(preset_id, dest)
    if not validation.ready and validation.new_files == 0 and validation.duplicate_files == 0:
        raise HTTPException(400, {"errors": validation.errors or rejections, "ready": False})

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] or list(preset.tags)
    progress = KnowledgeImporter().import_path(
        dest, source_type=preset.source_type, tags=tag_list
    )
    MaintenanceService(settings).ensure_search_indexes()
    health = HealthService(settings).report(run_integrity=False)

    return {
        "saved_files": saved,
        "rejected": rejections,
        "upload_dir": str(dest),
        "total": progress.total,
        "processed": progress.processed,
        "ingested": progress.ingested,
        "skipped": progress.skipped,
        "failed": progress.failed,
        "errors": progress.errors,
        "document_count": health.document_count,
        "chunk_count": health.chunk_count,
        "duplicate_files": validation.duplicate_files,
    }
