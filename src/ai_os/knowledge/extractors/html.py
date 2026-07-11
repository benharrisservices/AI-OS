"""HTML extractor."""

from __future__ import annotations

from pathlib import Path

import html2text
from bs4 import BeautifulSoup

from ai_os.knowledge.models import ExtractedDocument, ExtractionQuality, Format


class HtmlExtractor:
    supported_formats = (Format.HTML,)

    def extract(self, data: bytes, path: Path | None = None) -> ExtractedDocument:
        html = data.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")

        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()

        main = soup.find("main") or soup.find("article") or soup.find("body") or soup
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else (path.stem if path else "Untitled")

        converter = html2text.HTML2Text()
        converter.ignore_links = False
        converter.body_width = 0
        body = converter.handle(str(main)).strip()

        quality = ExtractionQuality.FULL if len(body) > 50 else ExtractionQuality.DEGRADED
        if not body:
            quality = ExtractionQuality.FAILED

        return ExtractedDocument(
            title=title,
            body=body,
            extraction_quality=quality,
        )
