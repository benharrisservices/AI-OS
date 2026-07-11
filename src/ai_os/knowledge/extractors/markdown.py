"""Markdown extractor."""

from __future__ import annotations

import re
from pathlib import Path

from ai_os.knowledge.models import ExtractedDocument, ExtractionQuality, Format

_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TITLE_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


class MarkdownExtractor:
    supported_formats = (Format.MARKDOWN,)

    def extract(self, data: bytes, path: Path | None = None) -> ExtractedDocument:
        text = data.decode("utf-8", errors="replace")
        body = text
        metadata: dict[str, str] = {}

        match = _FRONT_MATTER_RE.match(text)
        if match:
            import yaml

            metadata = yaml.safe_load(match.group(1)) or {}
            body = text[match.end() :]

        title = metadata.get("title")
        if not title:
            heading = _TITLE_RE.search(body)
            title = heading.group(1).strip() if heading else (path.stem if path else "Untitled")

        language = metadata.get("language", "en")
        return ExtractedDocument(
            title=str(title),
            body=body.strip(),
            language=str(language),
            extraction_quality=ExtractionQuality.FULL,
            metadata=metadata,
        )
