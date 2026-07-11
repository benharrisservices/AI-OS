"""AI-OS unified CLI — Knowledge, Decision, and Agent Runtime."""

from ai_os.agent.cli import register_agent_commands
from ai_os.decision.cli import register_decision_commands
from ai_os.knowledge.cli import app

register_decision_commands(app)
register_agent_commands(app)

__all__ = ["app"]
