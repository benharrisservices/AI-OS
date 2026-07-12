"""Automation definition loading."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_os.automation.config import AutomationSettings
from ai_os.automation.models import Automation


class AutomationLoader:
    def __init__(self, settings: AutomationSettings) -> None:
        self.settings = settings
        self.settings.ensure_dirs()

    def load(self, automation_id: str) -> Automation | None:
        path = self.settings.automations_dir / f"{automation_id}.yaml"
        if not path.exists():
            return None
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        automation = Automation.model_validate(data)
        state = self._load_state(automation_id)
        if state:
            if state.get("last_run_at"):
                from datetime import datetime

                automation.last_run_at = datetime.fromisoformat(state["last_run_at"])
            if state.get("next_run_at"):
                from datetime import datetime

                automation.next_run_at = datetime.fromisoformat(state["next_run_at"])
            if state.get("status"):
                from ai_os.automation.models import AutomationStatus

                automation.status = AutomationStatus(state["status"])
        return automation

    def list_all(self) -> list[Automation]:
        automations: list[Automation] = []
        for path in sorted(self.settings.automations_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                automations.append(Automation.model_validate(data))
            except Exception:
                continue
        return automations

    def save(self, automation: Automation) -> None:
        path = self.settings.automations_dir / f"{automation.automation_id}.yaml"
        path.write_text(
            yaml.dump(automation.model_dump(mode="json"), sort_keys=False),
            encoding="utf-8",
        )

    def _load_state(self, automation_id: str) -> dict | None:
        from ai_os.automation.store import AutomationStore

        return AutomationStore(self.settings).load_runtime_state(automation_id)
