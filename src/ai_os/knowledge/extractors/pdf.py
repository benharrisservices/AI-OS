"""PDF text extractor."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from ai_os.knowledge.models import ExtractedDocument, ExtractionQuality, Format


class PdfExtractor:
    supported_formats = (Format.PDF,)

    def extract(self, data: bytes, path: Path | None = None) -> ExtractedDocument:
        reader = PdfReader(BytesIO(data))
        pages: list[str] = []
        for index, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                pages.append(f"<!-- page: {index} -->\n\n{page_text}")

        body = "\n\n".join(pages).strip()
        title = (path.stem if path else None) or (
            (reader.metadata.title if reader.metadata else None) or "Untitled PDF"
        )
        quality = ExtractionQuality.FULL if body else ExtractionQuality.FAILED
        if body and len(body) < 100:
            quality = ExtractionQuality.DEGRADED

        return ExtractedDocument(
            title=str(title),
            body=body,
            extraction_quality=quality,
            page_count=len(reader.pages),
        )
