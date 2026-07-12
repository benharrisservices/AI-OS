"""AI-OS unified CLI — Knowledge, Decision, Agent Runtime, Memory, and Automation."""

from ai_os.agent.cli import register_agent_commands
from ai_os.automation.cli import register_automation_commands
from ai_os.decision.cli import register_decision_commands
from ai_os.knowledge.cli import app
from ai_os.memory.cli import register_memory_commands

register_decision_commands(app)
register_agent_commands(app)
register_memory_commands(app)
register_automation_commands(app)

__all__ = ["app"]
