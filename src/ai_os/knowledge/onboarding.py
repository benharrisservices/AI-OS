"""Guided knowledge onboarding — presets, validation, estimates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.ids import fingerprint_bytes
from ai_os.knowledge.models import SourceStatus
from ai_os.knowledge.pipeline import KnowledgePipeline
from ai_os.knowledge.registry import SourceRegistry

PRESETS_PATH = Path(__file__).resolve().parents[3] / "config" / "onboarding" / "presets.yaml"
SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".pdf", ".docx", ".html", ".htm"}
SECONDS_PER_FILE = 3.0  # rough estimate including embedding


@dataclass
class ImportPreset:
    id: str
    name: str
    order: int
    source_type: str
    suggested_path: str
    tags: list[str]
    description: str


@dataclass
class FileScan:
    path: Path
    size_bytes: int
    status: str  # new, duplicate, unsupported, error
    detail: str = ""


@dataclass
class ImportValidation:
    preset: ImportPreset
    source_path: Path
    files: list[FileScan] = field(default_factory=list)
    total_files: int = 0
    new_files: int = 0
    duplicate_files: int = 0
    unsupported_files: int = 0
    total_bytes: int = 0
    estimated_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)
    ready: bool = False

    @property
    def estimated_minutes(self) -> float:
        return round(self.estimated_seconds / 60, 1)


def load_presets() -> list[ImportPreset]:
    if not PRESETS_PATH.exists():
        raise FileNotFoundError(f"Presets not found: {PRESETS_PATH}")
    data = yaml.safe_load(PRESETS_PATH.read_text(encoding="utf-8"))
    presets = [
        ImportPreset(
            id=p["id"],
            name=p["name"],
            order=p["order"],
            source_type=p["source_type"],
            suggested_path=p["suggested_path"],
            tags=p.get("tags", []),
            description=p["description"],
        )
        for p in data.get("presets", [])
    ]
    return sorted(presets, key=lambda p: p.order)


def get_preset(preset_id: str) -> ImportPreset | None:
    return next((p for p in load_presets() if p.id == preset_id), None)


def collect_files(path: Path, source_type: str) -> list[Path]:
    path = path.expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    if source_type == "chats":
        if path.is_file():
            return [path]
        return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in {".json", ".jsonl", ".txt"})

    if source_type == "git":
        if not (path / ".git").exists():
            raise ValueError(f"Not a git repository: {path}")
        return sorted(
            p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES
        )

    if path.is_file():
        return [path]

    if path.is_dir():
        if source_type in ("folder", "markdown", "docs", "pdf", "docx"):
            suffix_filter = SUPPORTED_SUFFIXES
            if source_type == "pdf":
                suffix_filter = {".pdf"}
            elif source_type == "docx":
                suffix_filter = {".docx"}
            elif source_type == "markdown":
                suffix_filter = {".md", ".markdown"}
            return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in suffix_filter)
        return sorted(p for p in path.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_SUFFIXES)

    raise ValueError(f"Cannot scan: {path}")


def validate_import(preset_id: str, source_path: str | Path) -> ImportValidation:
    """Dry-run validation — does not import anything."""
    preset = get_preset(preset_id)
    if preset is None:
        raise ValueError(f"Unknown preset: {preset_id}")

    settings = KnowledgeSettings()
    registry = SourceRegistry(settings)
    path = Path(source_path).expanduser()

    validation = ImportValidation(preset=preset, source_path=path)

    try:
        files = collect_files(path, preset.source_type)
    except (FileNotFoundError, ValueError) as exc:
        validation.errors.append(str(exc))
        return validation

    validation.total_files = len(files)

    for file_path in files:
        try:
            if preset.source_type == "chats" and file_path.suffix.lower() in {".json", ".jsonl", ".txt"}:
                data = file_path.read_bytes()
                scan = FileScan(path=file_path, size_bytes=len(data), status="new")
                existing = registry.find_by_uri(file_path.as_uri())
                if existing and existing.fingerprint == fingerprint_bytes(data):
                    scan.status = "duplicate"
                    scan.detail = "already in knowledge base"
                    validation.duplicate_files += 1
                else:
                    validation.new_files += 1
                validation.total_bytes += len(data)
                validation.files.append(scan)
                continue

            if file_path.suffix.lower() not in SUPPORTED_SUFFIXES and preset.source_type != "chats":
                validation.unsupported_files += 1
                validation.files.append(
                    FileScan(path=file_path, size_bytes=0, status="unsupported", detail=file_path.suffix)
                )
                continue

            data = file_path.read_bytes()
            max_bytes = settings.knowledge_max_file_size_mb * 1024 * 1024
            if len(data) > max_bytes:
                validation.errors.append(f"Too large: {file_path.name} ({len(data)} bytes)")
                validation.files.append(
                    FileScan(path=file_path, size_bytes=len(data), status="error", detail="file too large")
                )
                continue

            scan = FileScan(path=file_path, size_bytes=len(data), status="new")
            existing = registry.find_by_uri(file_path.as_uri())
            if existing and existing.fingerprint == fingerprint_bytes(data):
                scan.status = "duplicate"
                scan.detail = "already in knowledge base"
                validation.duplicate_files += 1
            else:
                validation.new_files += 1

            validation.total_bytes += len(data)
            validation.files.append(scan)
        except OSError as exc:
            validation.errors.append(f"{file_path}: {exc}")
            validation.files.append(FileScan(path=file_path, size_bytes=0, status="error", detail=str(exc)))

    validation.estimated_seconds = validation.new_files * SECONDS_PER_FILE
    validation.ready = validation.new_files > 0 and not validation.errors
    return validation


def format_bytes(num: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "item"
