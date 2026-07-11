"""Document metadata extraction and enrichment."""

from __future__ import annotations

import re
from pathlib import Path

from ai_os.knowledge.models import DocumentRecord, ExtractedDocument, Format, IntakeRecord
from ai_os.knowledge.normalize import count_headings, count_words


def infer_language(text: str) -> str:
    sample = text[:2000].lower()
    if re.search(r"\b(the|and|for|with)\b", sample):
        return "en"
    return "en"


def build_document_record(
    *,
    doc_id: str,
    source_id: str,
    intake: IntakeRecord,
    extracted: ExtractedDocument,
    fmt: Format,
    settings_pipeline_version: str,
) -> DocumentRecord:
    body = extracted.body
    language = extracted.language or infer_language(body)
    raw_path = str(Path("knowledge/raw") / source_id / f"original{Path(intake.original_filename or '').suffix or ''}")
    processed_path = str(Path("knowledge/processed/documents") / doc_id / "document.md")

    return DocumentRecord(
        pipeline_version=settings_pipeline_version,
        doc_id=doc_id,
        source_id=source_id,
        title=extracted.title,
        language=language,
        format=fmt,
        extraction_quality=extracted.extraction_quality,
        page_count=extracted.page_count,
        word_count=count_words(body),
        char_count=len(body),
        heading_count=count_headings(body),
        tags=list(intake.tags),
        source_uri=intake.path_or_url,
        raw_path=raw_path,
        processed_path=processed_path,
        custom=dict(extracted.metadata),
    )
