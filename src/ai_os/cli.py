"""AI-OS unified CLI."""

from ai_os.agent.cli import register_agent_commands
from ai_os.automation.cli import register_automation_commands
from ai_os.capabilities.cli import register_capability_commands
from ai_os.decision.cli import register_decision_commands
from ai_os.integrations.cli import register_integration_commands
from ai_os.knowledge.cli import app
from ai_os.memory.cli import register_memory_commands
from ai_os.routing.cli import register_routing_commands
from ai_os.ux.cli import register_ux_commands

register_decision_commands(app)
register_agent_commands(app)
register_memory_commands(app)
register_automation_commands(app)
register_capability_commands(app)
register_integration_commands(app)
register_routing_commands(app)
register_ux_commands(app)

__all__ = ["app"]
