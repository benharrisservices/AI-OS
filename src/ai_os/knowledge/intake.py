"""Intake: accept files and URLs into knowledge/raw."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import httpx

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.format_detect import detect_format_from_bytes, detect_format_from_path, guess_mime
from ai_os.knowledge.ids import fingerprint_bytes, new_doc_id, new_source_id
from ai_os.knowledge.io import write_json
from ai_os.knowledge.models import (
    ErrorRecord,
    Format,
    IntakeChannel,
    IntakeRecord,
    SourceRegistryRecord,
    SourceStatus,
)
from ai_os.knowledge.registry import SourceRegistry

EXTENSION_BY_FORMAT: dict[Format, str] = {
    Format.MARKDOWN: ".md",
    Format.TXT: ".txt",
    Format.PDF: ".pdf",
    Format.DOCX: ".docx",
    Format.HTML: ".html",
    Format.URL: ".html",
}


class IntakeError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class IntakeService:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.registry = SourceRegistry(settings)
        self.settings.ensure_dirs()

    def ingest_file(
        self,
        path: Path,
        *,
        tags: list[str] | None = None,
        channel: IntakeChannel = IntakeChannel.CLI,
    ) -> SourceRegistryRecord:
        path = path.expanduser().resolve()
        if not path.exists():
            raise IntakeError("INTAKE_READ_ERROR", f"File not found: {path}", retryable=False)

        data = path.read_bytes()
        max_bytes = self.settings.knowledge_max_file_size_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise IntakeError("INTAKE_FILE_TOO_LARGE", f"File exceeds {self.settings.knowledge_max_file_size_mb} MB")

        fmt = detect_format_from_path(path) or detect_format_from_bytes(data, path)
        if fmt is None:
            raise IntakeError("INTAKE_UNSUPPORTED_FORMAT", f"Unsupported format: {path.suffix}")

        fingerprint = fingerprint_bytes(data)
        uri = path.as_uri()
        existing = self.registry.find_by_uri(uri)
        if existing and existing.fingerprint == fingerprint:
            existing.status = SourceStatus.UNCHANGED
            self.registry.upsert(existing)
            return existing

        source_id = existing.source_id if existing else new_source_id()
        ext = EXTENSION_BY_FORMAT.get(fmt, path.suffix or ".bin")
        dest_dir = self.settings.knowledge_raw_dir / source_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        original_path = dest_dir / f"original{ext}"
        original_path.write_bytes(data)

        intake = IntakeRecord(
            source_id=source_id,
            kind="file",
            path_or_url=uri,
            format=fmt,
            fingerprint=fingerprint,
            original_filename=path.name,
            mime_type=guess_mime(path),
            byte_size=len(data),
            tags=tags or [],
            intake_channel=channel,
        )
        write_json(dest_dir / "intake.json", intake)

        record = SourceRegistryRecord(
            source_id=source_id,
            status=SourceStatus.PENDING,
            format=fmt,
            fingerprint=fingerprint,
            original_filename=path.name,
            original_uri=uri,
            byte_size=len(data),
            doc_ids=[new_doc_id(source_id)],
            tags=tags or [],
            intake_channel=channel,
        )
        self.registry.upsert(record)
        return record

    def ingest_url(
        self,
        url: str,
        *,
        tags: list[str] | None = None,
        channel: IntakeChannel = IntakeChannel.CLI,
    ) -> SourceRegistryRecord:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise IntakeError("INTAKE_URL_BLOCKED", f"Unsupported URL scheme: {parsed.scheme}")

        with httpx.Client(
            timeout=self.settings.url_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": self.settings.url_user_agent},
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.content

        fingerprint = fingerprint_bytes(data)
        existing = self.registry.find_by_uri(url)
        if existing and existing.fingerprint == fingerprint:
            existing.status = SourceStatus.UNCHANGED
            self.registry.upsert(existing)
            return existing

        source_id = existing.source_id if existing else new_source_id()
        dest_dir = self.settings.knowledge_raw_dir / source_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "snapshot.html").write_bytes(data)
        (dest_dir / "original.html").write_bytes(data)
        headers = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "final_url": str(response.url),
        }
        (dest_dir / "headers.json").write_text(json.dumps(headers, indent=2), encoding="utf-8")

        intake = IntakeRecord(
            source_id=source_id,
            kind="url",
            path_or_url=url,
            format=Format.URL,
            fingerprint=fingerprint,
            original_filename=None,
            mime_type=response.headers.get("content-type"),
            byte_size=len(data),
            tags=tags or [],
            intake_channel=channel,
            final_url=str(response.url),
            http_status=response.status_code,
            fetched_at=intake_timestamp(),
            content_type=response.headers.get("content-type"),
        )
        write_json(dest_dir / "intake.json", intake)

        record = SourceRegistryRecord(
            source_id=source_id,
            status=SourceStatus.PENDING,
            format=Format.URL,
            fingerprint=fingerprint,
            original_uri=url,
            byte_size=len(data),
            doc_ids=[new_doc_id(source_id)],
            tags=tags or [],
            intake_channel=channel,
        )
        self.registry.upsert(record)
        return record


def intake_timestamp():
    from ai_os.knowledge.models import utc_now

    return utc_now()
