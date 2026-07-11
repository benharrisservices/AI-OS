"""Extractor protocol and registry."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from ai_os.knowledge.models import ExtractedDocument, Format


class Extractor(Protocol):
    supported_formats: tuple[Format, ...]

    def extract(self, data: bytes, path: Path | None = None) -> ExtractedDocument: ...


_EXTRACTORS: dict[Format, Extractor] = {}


def register_extractor(extractor: Extractor) -> None:
    for fmt in extractor.supported_formats:
        _EXTRACTORS[fmt] = extractor


def get_extractor(fmt: Format) -> Extractor:
    if fmt not in _EXTRACTORS:
        raise ValueError(f"No extractor registered for format: {fmt}")
    return _EXTRACTORS[fmt]


def extract_document(data: bytes, fmt: Format, path: Path | None = None) -> ExtractedDocument:
    return get_extractor(fmt).extract(data, path)
