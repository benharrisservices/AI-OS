"""Filesystem watcher for automatic ingestion."""

from __future__ import annotations

import time
from pathlib import Path

from watchfiles import Change, watch

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.pipeline import KnowledgePipeline

SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".pdf", ".docx", ".html", ".htm"}


class InboxWatcher:
    def __init__(self, settings: KnowledgeSettings) -> None:
        self.settings = settings
        self.pipeline = KnowledgePipeline(settings)
        self.watch_dir = settings.knowledge_watch_dir
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self._pending: dict[str, float] = {}

    def _is_supported(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES

    def _schedule(self, path: Path) -> None:
        self._pending[str(path)] = time.monotonic()

    def _drain_pending(self) -> list[Path]:
        now = time.monotonic()
        ready = [
            Path(p)
            for p, scheduled in list(self._pending.items())
            if now - scheduled >= self.settings.watch_debounce_seconds
        ]
        for path in ready:
            self._pending.pop(str(path), None)
        return ready

    def process_path(self, path: Path) -> None:
        if not self._is_supported(path):
            return
        self.pipeline.ingest_file(path)

    def run_once(self) -> int:
        """Process all supported files currently in the watch directory."""
        count = 0
        for path in sorted(self.watch_dir.rglob("*")):
            if self._is_supported(path):
                self.pipeline.ingest_file(path)
                count += 1
        return count

    def watch_forever(self) -> None:
        """Block and ingest files as they appear or change in the watch directory."""
        for changes in watch(self.watch_dir, recursive=True, debounce=int(self.settings.watch_debounce_seconds * 1000)):
            for change, path_str in changes:
                if change not in {Change.added, Change.modified}:
                    continue
                path = Path(path_str)
                if self._is_supported(path):
                    self._schedule(path)

            for path in self._drain_pending():
                try:
                    self.process_path(path)
                except Exception as exc:
                    print(f"[watch] failed to ingest {path}: {exc}")
