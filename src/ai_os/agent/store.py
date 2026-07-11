"""Task and execution log persistence."""

from __future__ import annotations

import json
from pathlib import Path

from ai_os.agent.config import AgentSettings
from ai_os.agent.models import AgentTask, ToolInvocation, utc_now


class TaskStore:
    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings
        self.settings.ensure_dirs()

    def _task_path(self, task_id: str) -> Path:
        return self.settings.tasks_dir / f"{task_id}.json"

    def save_task(self, task: AgentTask) -> None:
        task.updated_at = utc_now()
        self._task_path(task.task_id).write_text(
            json.dumps(task.model_dump(mode="json"), indent=2, default=str) + "\n",
            encoding="utf-8",
        )

    def get_task(self, task_id: str) -> AgentTask | None:
        path = self._task_path(task_id)
        if not path.exists():
            return None
        return AgentTask.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_tasks(self) -> list[AgentTask]:
        tasks: list[AgentTask] = []
        for path in sorted(self.settings.tasks_dir.glob("task_*.json")):
            try:
                tasks.append(AgentTask.model_validate(json.loads(path.read_text(encoding="utf-8"))))
            except Exception:
                continue
        return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def append_log(self, task_id: str, message: str, *, level: str = "info") -> None:
        log_path = self.settings.logs_dir / f"{task_id}.jsonl"
        entry = {"timestamp": utc_now().isoformat(), "level": level, "message": message}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, default=str) + "\n")

    def get_logs(self, task_id: str) -> list[dict]:
        log_path = self.settings.logs_dir / f"{task_id}.jsonl"
        if not log_path.exists():
            return []
        return [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def save_invocation(self, invocation: ToolInvocation) -> None:
        inv_dir = self.settings.tasks_dir / "invocations"
        inv_dir.mkdir(parents=True, exist_ok=True)
        path = inv_dir / f"{invocation.invocation_id}.json"
        path.write_text(
            json.dumps(invocation.model_dump(mode="json"), indent=2, default=str) + "\n",
            encoding="utf-8",
        )
