"""Deterministic and stable identifier generation."""

from __future__ import annotations

import hashlib
import re

from ulid import ULID


def new_source_id() -> str:
    return f"src_{ULID()}"


def new_doc_id(source_id: str, boundary: str = "default") -> str:
    digest = hashlib.sha256(f"{source_id}:{boundary}".encode()).hexdigest()[:16]
    return f"doc_{digest}"


def slugify_heading(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug).strip("-")
    return slug or "section"


def content_hash(text: str) -> str:
    normalized = text.strip().encode("utf-8")
    return f"sha256:{hashlib.sha256(normalized).hexdigest()}"


def fingerprint_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def chunk_id(
    doc_id: str,
    heading_path: str,
    embed_text: str,
    chunk_index: int,
    chunk_level: str,
) -> str:
    payload = f"{doc_id}|{heading_path}|{content_hash(embed_text)}|{chunk_index}|{chunk_level}"
    digest = hashlib.sha256(payload.encode()).hexdigest()[:20]
    return f"chk_{digest}"
