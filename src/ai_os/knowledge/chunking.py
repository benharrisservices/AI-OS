"""Deterministic hierarchical chunking."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.ids import chunk_id, content_hash, slugify_heading
from ai_os.knowledge.models import ChunkLevel, ChunkRecord, DocumentRecord
from ai_os.knowledge.tokens import count_tokens, split_by_tokens

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_FENCE_RE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)


@dataclass
class Section:
    heading_path: str
    title: str
    body: str
    start_offset: int
    end_offset: int


def _parse_outline(body: str) -> list[Section]:
    matches = list(_HEADING_RE.finditer(body))
    if not matches:
        return [
            Section(
                heading_path="content",
                title="content",
                body=body.strip(),
                start_offset=0,
                end_offset=len(body),
            )
        ]

    sections: list[Section] = []
    heading_stack: list[tuple[int, str, str]] = []

    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        slug = slugify_heading(title)

        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        heading_stack.append((level, slug, title))
        heading_path = "/".join(item[1] for item in heading_stack)

        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        section_body = body[start:end].strip()
        if section_body:
            sections.append(
                Section(
                    heading_path=heading_path,
                    title=title,
                    body=section_body,
                    start_offset=start,
                    end_offset=end,
                )
            )
    return sections


def _protect_fences(text: str) -> tuple[str, dict[str, str]]:
    placeholders: dict[str, str] = {}

    def replacer(match: re.Match[str]) -> str:
        key = f"__FENCE_{len(placeholders)}__"
        placeholders[key] = match.group(0)
        return key

    protected = _FENCE_RE.sub(replacer, text)
    return protected, placeholders


def _restore_fences(text: str, placeholders: dict[str, str]) -> str:
    restored = text
    for key, value in placeholders.items():
        restored = restored.replace(key, value)
    return restored


def _split_section(
    section: Section,
    max_tokens: int,
    overlap: int,
) -> list[str]:
    protected, placeholders = _protect_fences(section.body)
    parts = split_by_tokens(protected, max_tokens, overlap)
    return [_restore_fences(part, placeholders).strip() for part in parts if part.strip()]


def chunk_document(
    document: DocumentRecord,
    body: str,
    settings: KnowledgeSettings,
) -> list[ChunkRecord]:
    sections = _parse_outline(body)
    records: list[ChunkRecord] = []
    parent_index = 0
    child_global_index = 0

    for section in sections:
        parent_parts = _split_section(section, settings.parent_max_tokens, 0)
        if not parent_parts:
            continue

        parent_chunk_ids: list[str] = []
        for part_index, parent_text in enumerate(parent_parts):
            parent_embed = f"Document: {document.title} > {section.heading_path}\n\n{parent_text}"
            parent_id = chunk_id(
                document.doc_id,
                section.heading_path,
                parent_embed,
                parent_index,
                ChunkLevel.PARENT.value,
            )
            parent_chunk_ids.append(parent_id)
            records.append(
                ChunkRecord(
                    chunk_id=parent_id,
                    doc_id=document.doc_id,
                    source_id=document.source_id,
                    chunk_level=ChunkLevel.PARENT,
                    parent_chunk_id=None,
                    chunk_index=parent_index,
                    heading_path=section.heading_path,
                    title=document.title,
                    language=document.language,
                    token_count=count_tokens(parent_text),
                    char_count=len(parent_text),
                    content_hash=content_hash(parent_embed),
                    embed_text=parent_embed,
                    body_text=parent_text,
                    start_offset=section.start_offset,
                    end_offset=section.end_offset,
                    tags=list(document.tags),
                )
            )
            parent_index += 1

            child_parts = _split_section(
                Section(section.heading_path, section.title, parent_text, section.start_offset, section.end_offset),
                settings.knowledge_chunk_size,
                settings.knowledge_chunk_overlap,
            )
            if not child_parts:
                child_parts = [parent_text]
            for child_text in child_parts:
                if (
                    count_tokens(child_text) < settings.min_chunk_tokens
                    and len(child_parts) > 1
                ):
                    continue
                child_embed = f"Document: {document.title} > {section.heading_path}\n\n{child_text}"
                child_id = chunk_id(
                    document.doc_id,
                    section.heading_path,
                    child_embed,
                    child_global_index,
                    ChunkLevel.CHILD.value,
                )
                records.append(
                    ChunkRecord(
                        chunk_id=child_id,
                        doc_id=document.doc_id,
                        source_id=document.source_id,
                        chunk_level=ChunkLevel.CHILD,
                        parent_chunk_id=parent_chunk_ids[-1],
                        chunk_index=child_global_index,
                        heading_path=section.heading_path,
                        title=document.title,
                        language=document.language,
                        token_count=count_tokens(child_text),
                        char_count=len(child_text),
                        content_hash=content_hash(child_embed),
                        embed_text=child_embed,
                        body_text=child_text,
                        start_offset=section.start_offset,
                        end_offset=section.end_offset,
                        tags=list(document.tags),
                    )
                )
                child_global_index += 1

    return records
