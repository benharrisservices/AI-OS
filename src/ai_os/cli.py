"""AI-OS unified CLI — Knowledge Engine and Decision Engine."""

from ai_os.decision.cli import register_decision_commands
from ai_os.knowledge.cli import app

register_decision_commands(app)

__all__ = ["app"]
