"""Decision persistence — runtime records in memory/decisions/."""

from __future__ import annotations

import json
from pathlib import Path

from ai_os.decision.config import DecisionSettings
from ai_os.decision.models import DecisionResult


class DecisionStore:
    def __init__(self, settings: DecisionSettings) -> None:
        self.settings = settings
        self.settings.ensure_dirs()

    def _path(self, decision_id: str) -> Path:
        return self.settings.decisions_dir / f"{decision_id}.json"

    def save(self, result: DecisionResult) -> None:
        path = self._path(result.decision_id)
        path.write_text(
            json.dumps(result.model_dump(mode="json"), indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        self._append_index(result)

    def get(self, decision_id: str) -> DecisionResult | None:
        path = self._path(decision_id)
        if not path.exists():
            return None
        return DecisionResult.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def list_all(self) -> list[DecisionResult]:
        results: list[DecisionResult] = []
        for path in sorted(self.settings.decisions_dir.glob("dec_*.json")):
            try:
                results.append(
                    DecisionResult.model_validate(json.loads(path.read_text(encoding="utf-8")))
                )
            except Exception:
                continue
        return sorted(results, key=lambda r: r.created_at, reverse=True)

    def _append_index(self, result: DecisionResult) -> None:
        index_path = self.settings.decisions_dir / "index.jsonl"
        line = json.dumps(
            {
                "decision_id": result.decision_id,
                "question": result.request.question,
                "strategy": result.strategy.value,
                "confidence": result.confidence,
                "status": result.status.value,
                "created_at": result.created_at.isoformat(),
                "recommendation": result.recommendation.title if result.recommendation else None,
            },
            default=str,
        )
        with index_path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
