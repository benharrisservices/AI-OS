"""Plain text extractor."""

from __future__ import annotations

from pathlib import Path

from ai_os.knowledge.models import ExtractedDocument, ExtractionQuality, Format


class PlainTextExtractor:
    supported_formats = (Format.TXT,)

    def extract(self, data: bytes, path: Path | None = None) -> ExtractedDocument:
        text = data.decode("utf-8", errors="replace").strip()
        lines = [line for line in text.splitlines() if line.strip()]
        title = lines[0][:120] if lines and len(lines[0]) < 120 else (path.stem if path else "Untitled")
        body = text
        if lines and lines[0] == title and len(lines) > 1:
            body = "\n\n".join(lines[1:])

        return ExtractedDocument(
            title=title,
            body=body,
            extraction_quality=ExtractionQuality.FULL if body else ExtractionQuality.FAILED,
        )
