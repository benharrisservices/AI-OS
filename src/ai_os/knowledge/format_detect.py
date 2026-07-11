"""Format detection utilities."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from ai_os.knowledge.models import Format

EXTENSION_MAP: dict[str, Format] = {
    ".md": Format.MARKDOWN,
    ".markdown": Format.MARKDOWN,
    ".txt": Format.TXT,
    ".pdf": Format.PDF,
    ".docx": Format.DOCX,
    ".html": Format.HTML,
    ".htm": Format.HTML,
}


def detect_format_from_path(path: Path) -> Format | None:
    ext = path.suffix.lower()
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]
    return None


def detect_format_from_bytes(data: bytes, path: Path | None = None) -> Format:
    if path:
        by_ext = detect_format_from_path(path)
        if by_ext:
            return by_ext

    if data.startswith(b"%PDF"):
        return Format.PDF
    if data[:2] == b"PK" and b"word/" in data[:4096]:
        return Format.DOCX
    stripped = data.lstrip()
    if stripped.startswith(b"<!DOCTYPE") or stripped.startswith(b"<html"):
        return Format.HTML
    if stripped.startswith(b"---") or stripped.startswith(b"#"):
        return Format.MARKDOWN
    return Format.TXT


def guess_mime(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"
