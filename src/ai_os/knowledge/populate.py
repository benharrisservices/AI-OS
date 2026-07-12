"""Knowledge population utilities — import from diverse sources."""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import httpx

from ai_os.knowledge.config import KnowledgeSettings
from ai_os.knowledge.models import SourceStatus
from ai_os.knowledge.pipeline import KnowledgePipeline


@dataclass
class ImportProgress:
    total: int = 0
    processed: int = 0
    ingested: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

    def report(self, *, on_progress: Callable[[str], None] | None = None) -> str:
        msg = f"processed={self.processed}/{self.total} ingested={self.ingested} skipped={self.skipped} failed={self.failed}"
        if on_progress:
            on_progress(msg)
        return msg


class KnowledgeImporter:
    """Import content into the knowledge pipeline without altering engine architecture."""

    SUPPORTED_SUFFIXES = {".md", ".markdown", ".txt", ".pdf", ".docx", ".html", ".htm"}

    def __init__(self, settings: KnowledgeSettings | None = None) -> None:
        self.settings = settings or KnowledgeSettings()
        self.settings.ensure_dirs()
        self.pipeline = KnowledgePipeline(self.settings)

    def import_path(
        self,
        source: Path | str,
        *,
        source_type: str = "auto",
        tags: list[str] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> ImportProgress:
        path = Path(source).expanduser().resolve()
        progress = ImportProgress()

        if source_type == "auto":
            source_type = self._detect_type(path)

        handlers = {
            "markdown": self._import_directory,
            "folder": self._import_directory,
            "docs": self._import_directory,
            "text": self._import_file,
            "pdf": self._import_file,
            "docx": self._import_file,
            "git": self._import_git,
            "github": self._import_github,
            "chats": self._import_chats,
        }
        handler = handlers.get(source_type, self._import_auto)
        return handler(path, tags=tags, progress=progress, on_progress=on_progress)

    def _detect_type(self, path: Path) -> str:
        if path.is_file():
            suffix = path.suffix.lower()
            if suffix in {".json", ".jsonl"}:
                return "chats"
            return suffix.lstrip(".") or "text"
        if (path / ".git").exists():
            return "git"
        return "folder"

    def _import_auto(
        self,
        path: Path,
        *,
        tags: list[str] | None,
        progress: ImportProgress,
        on_progress: Callable[[str], None] | None,
    ) -> ImportProgress:
        if path.is_file():
            return self._import_file(path, tags=tags, progress=progress, on_progress=on_progress)
        return self._import_directory(path, tags=tags, progress=progress, on_progress=on_progress)

    def _import_file(
        self,
        path: Path,
        *,
        tags: list[str] | None,
        progress: ImportProgress,
        on_progress: Callable[[str], None] | None,
    ) -> ImportProgress:
        progress.total = 1
        self._ingest_one(path, tags=tags, progress=progress, on_progress=on_progress)
        return progress

    def _import_directory(
        self,
        directory: Path,
        *,
        tags: list[str] | None,
        progress: ImportProgress,
        on_progress: Callable[[str], None] | None,
    ) -> ImportProgress:
        if not directory.is_dir():
            progress.errors.append(f"Not a directory: {directory}")
            progress.failed = 1
            return progress

        files = sorted(
            p for p in directory.rglob("*") if p.is_file() and p.suffix.lower() in self.SUPPORTED_SUFFIXES
        )
        progress.total = len(files)
        for path in files:
            self._ingest_one(path, tags=tags, progress=progress, on_progress=on_progress)
        return progress

    def _ingest_one(
        self,
        path: Path,
        *,
        tags: list[str] | None,
        progress: ImportProgress,
        on_progress: Callable[[str], None] | None,
    ) -> None:
        progress.processed += 1
        try:
            record = self.pipeline.ingest_file(path, tags=tags)
            if record.status == SourceStatus.UNCHANGED:
                progress.skipped += 1
                if on_progress:
                    on_progress(f"skip (duplicate) {path.name}")
            else:
                progress.ingested += 1
                if on_progress:
                    on_progress(f"ingested {path.name}")
        except Exception as exc:
            progress.failed += 1
            progress.errors.append(f"{path}: {exc}")
            if on_progress:
                on_progress(f"failed {path.name}: {exc}")

    def _import_git(
        self,
        path: Path,
        *,
        tags: list[str] | None,
        progress: ImportProgress,
        on_progress: Callable[[str], None] | None,
    ) -> ImportProgress:
        if not (path / ".git").exists():
            progress.errors.append(f"Not a git repository: {path}")
            progress.failed = 1
            return progress
        return self._import_directory(path, tags=tags or ["git-import"], progress=progress, on_progress=on_progress)

    def _import_github(
        self,
        spec: Path,
        *,
        tags: list[str] | None,
        progress: ImportProgress,
        on_progress: Callable[[str], None] | None,
    ) -> ImportProgress:
        """Import from github.com/owner/repo or owner/repo string."""
        repo_spec = str(spec).replace("https://github.com/", "").strip("/")
        if "/" not in repo_spec:
            progress.errors.append(f"Invalid GitHub spec: {repo_spec} (use owner/repo)")
            progress.failed = 1
            return progress

        token = os.environ.get("GITHUB_TOKEN")
        headers = {"Accept": "application/vnd.github+json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        owner, repo = repo_spec.split("/", 1)
        url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        try:
            with httpx.Client(timeout=30.0) as client:
                r = client.get(url, headers=headers)
                if r.status_code != 200:
                    progress.errors.append(f"GitHub API: {r.status_code} {r.text[:200]}")
                    progress.failed = 1
                    return progress
                content_b64 = r.json().get("content", "")
                readme = base64.b64decode(content_b64).decode("utf-8", errors="replace")
        except Exception as exc:
            progress.errors.append(str(exc))
            progress.failed = 1
            return progress

        dest = self.settings.knowledge_raw_dir / "imports" / f"github-{owner}-{repo}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f"# {owner}/{repo}\n\n{readme}", encoding="utf-8")
        return self._import_file(dest, tags=tags or ["github-import"], progress=progress, on_progress=on_progress)

    def _import_chats(
        self,
        path: Path,
        *,
        tags: list[str] | None,
        progress: ImportProgress,
        on_progress: Callable[[str], None] | None,
    ) -> ImportProgress:
        """Import exported chat logs (JSON array or plain text)."""
        if not path.is_file():
            progress.errors.append(f"Chat export must be a file: {path}")
            progress.failed = 1
            return progress

        dest_dir = self.settings.knowledge_raw_dir / "imports" / "chats"
        dest_dir.mkdir(parents=True, exist_ok=True)

        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            messages = data if isinstance(data, list) else data.get("messages", data.get("conversations", []))
            lines: list[str] = [f"# Chat export from {path.name}\n"]
            for i, msg in enumerate(messages):
                if isinstance(msg, dict):
                    role = msg.get("role", msg.get("author", "unknown"))
                    content = msg.get("content", msg.get("text", ""))
                    if isinstance(content, list):
                        content = " ".join(
                            c.get("text", str(c)) if isinstance(c, dict) else str(c) for c in content
                        )
                    lines.append(f"\n## {role}\n\n{content}\n")
                else:
                    lines.append(f"\n## message {i}\n\n{msg}\n")
            dest = dest_dir / f"{path.stem}.md"
            dest.write_text("\n".join(lines), encoding="utf-8")
        else:
            dest = dest_dir / f"{path.stem}.md"
            dest.write_text(f"# Chat export\n\n{path.read_text(encoding='utf-8')}", encoding="utf-8")

        return self._import_file(dest, tags=tags or ["chat-import"], progress=progress, on_progress=on_progress)

    def clone_and_import(
        self,
        git_url: str,
        *,
        tags: list[str] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> ImportProgress:
        """Clone a remote git repository to a temp dir and import supported files."""
        progress = ImportProgress()
        tmp = Path(tempfile.mkdtemp(prefix="ai-os-import-"))
        try:
            if on_progress:
                on_progress(f"cloning {git_url}")
            subprocess.run(["git", "clone", "--depth", "1", git_url, str(tmp)], check=True, capture_output=True)
            return self._import_directory(tmp, tags=tags or ["git-clone"], progress=progress, on_progress=on_progress)
        except subprocess.CalledProcessError as exc:
            progress.errors.append(exc.stderr.decode() if exc.stderr else str(exc))
            progress.failed = 1
            return progress
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
