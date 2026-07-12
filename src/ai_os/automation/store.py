"""Automation persistence."""

from __future__ import annotations

import json
from pathlib import Path

from ai_os.automation.config import AutomationSettings
from ai_os.automation.models import Automation, ExecutionRecord, utc_now


class AutomationStore:
    def __init__(self, settings: AutomationSettings) -> None:
        self.settings = settings
        self.settings.ensure_dirs()

    def _automation_path(self, automation_id: str) -> Path:
        return self.settings.automations_dir / f"{automation_id}.yaml"

    def _execution_path(self, execution_id: str) -> Path:
        return self.settings.history_dir / f"{execution_id}.json"

    def _active_runs_path(self, automation_id: str) -> Path:
        return self.settings.state_dir / f"{automation_id}_active.json"

    def save_automation_yaml(self, automation: Automation, yaml_text: str) -> None:
        path = self._automation_path(automation.automation_id)
        path.write_text(yaml_text, encoding="utf-8")

    def save_execution(self, record: ExecutionRecord) -> None:
        path = self._execution_path(record.execution_id)
        path.write_text(
            json.dumps(record.model_dump(mode="json"), indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        self._append_history_index(record)

    def get_execution(self, execution_id: str) -> ExecutionRecord | None:
        path = self._execution_path(execution_id)
        if not path.exists():
            return None
        return ExecutionRecord.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_executions(
        self,
        automation_id: str | None = None,
        *,
        limit: int = 50,
    ) -> list[ExecutionRecord]:
        records: list[ExecutionRecord] = []
        for path in sorted(self.settings.history_dir.glob("aexec_*.json")):
            try:
                record = ExecutionRecord.model_validate(
                    json.loads(path.read_text(encoding="utf-8"))
                )
                if automation_id and record.automation_id != automation_id:
                    continue
                records.append(record)
            except Exception:
                continue
        records.sort(key=lambda r: r.scheduled_at, reverse=True)
        return records[:limit]

    def get_active_run_count(self, automation_id: str) -> int:
        path = self._active_runs_path(automation_id)
        if not path.exists():
            return 0
        data = json.loads(path.read_text(encoding="utf-8"))
        return int(data.get("count", 0))

    def increment_active_runs(self, automation_id: str) -> int:
        count = self.get_active_run_count(automation_id) + 1
        self._set_active_runs(automation_id, count)
        return count

    def decrement_active_runs(self, automation_id: str) -> int:
        count = max(0, self.get_active_run_count(automation_id) - 1)
        self._set_active_runs(automation_id, count)
        return count

    def _set_active_runs(self, automation_id: str, count: int) -> None:
        path = self._active_runs_path(automation_id)
        path.write_text(json.dumps({"count": count, "updated_at": utc_now().isoformat()}) + "\n")

    def _append_history_index(self, record: ExecutionRecord) -> None:
        index_path = self.settings.history_dir / "index.jsonl"
        line = json.dumps(
            {
                "execution_id": record.execution_id,
                "automation_id": record.automation_id,
                "status": record.status.value,
                "scheduled_at": record.scheduled_at.isoformat(),
            },
            default=str,
        )
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def save_runtime_state(self, automation: Automation) -> None:
        path = self.settings.state_dir / f"{automation.automation_id}_state.json"
        path.write_text(
            json.dumps(
                {
                    "automation_id": automation.automation_id,
                    "last_run_at": automation.last_run_at.isoformat() if automation.last_run_at else None,
                    "next_run_at": automation.next_run_at.isoformat() if automation.next_run_at else None,
                    "status": automation.status.value,
                    "updated_at": utc_now().isoformat(),
                },
                default=str,
            )
            + "\n",
            encoding="utf-8",
        )

    def load_runtime_state(self, automation_id: str) -> dict | None:
        path = self.settings.state_dir / f"{automation_id}_state.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
