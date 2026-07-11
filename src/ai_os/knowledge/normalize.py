"""Canonical Markdown normalization."""

from __future__ import annotations

import re

import yaml

from ai_os.knowledge.models import DocumentRecord, ExtractedDocument

_HEADING_SKIP_RE = re.compile(r"^(#{1,6})\s+", re.MULTILINE)


def _fix_heading_levels(body: str) -> str:
    levels = [len(m.group(1)) for m in _HEADING_SKIP_RE.finditer(body)]
    if not levels:
        return body
    # Ensure no level jumps greater than 1 from previous heading level.
    lines = body.splitlines()
    result: list[str] = []
    prev_level = 0
    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if not match:
            result.append(line)
            continue
        level = len(match.group(1))
        if prev_level and level > prev_level + 1:
            level = prev_level + 1
        prev_level = level
        result.append(f"{'#' * level} {match.group(2)}")
    return "\n".join(result)


def normalize_body(body: str) -> str:
    text = body.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return _fix_heading_levels(text.strip())


def build_document_markdown(document: DocumentRecord, body: str) -> str:
    front_matter = {
        "doc_id": document.doc_id,
        "source_id": document.source_id,
        "title": document.title,
        "language": document.language,
        "tags": document.tags,
        "created_at": document.created_at.isoformat(),
    }
    yaml_block = yaml.safe_dump(front_matter, sort_keys=False).strip()
    normalized = normalize_body(body)
    return f"---\n{yaml_block}\n---\n\n{normalized}\n"


def count_headings(body: str) -> int:
    return len(re.findall(r"^#{1,6}\s+", body, flags=re.MULTILINE))


def count_words(body: str) -> int:
    return len(re.findall(r"\S+", body))


def enrich_extracted(extracted: ExtractedDocument) -> ExtractedDocument:
    extracted.body = normalize_body(extracted.body)
    return extracted
