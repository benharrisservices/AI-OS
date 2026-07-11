"""Token counting utilities."""

from __future__ import annotations

import re

_WORD_RE = re.compile(r"\S+")


def count_tokens(text: str) -> int:
    """Approximate token count using whitespace-delimited words."""
    if not text.strip():
        return 0
    return len(_WORD_RE.findall(text))


def split_by_tokens(text: str, max_tokens: int, overlap: int) -> list[str]:
    words = _WORD_RE.findall(text)
    if not words:
        return []
    if len(words) <= max_tokens:
        return [text.strip()]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = max(0, end - overlap)
    return chunks
