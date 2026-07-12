"""Register skills as Agent Runtime tools."""

from __future__ import annotations

from typing import Any

from ai_os.agent.models import ExecutionContext, ToolPermission
from ai_os.agent.tools import register_tool
from ai_os.agent.tools.base import BaseTool
from ai_os.capabilities.registry import list_skills


class SkillTool(BaseTool):
    """Wraps a capability skill as an Agent Runtime tool."""

    def __init__(self, skill) -> None:
        self._skill = skill
        self.name = f"skill_{skill.metadata.skill_id.replace('-', '_')}"
        self.description = skill.metadata.description
        self.input_schema = skill.metadata.input_schema or {"type": "object", "properties": {}}
        self.output_schema = skill.metadata.output_schema or {"type": "object"}
        self.permissions = [ToolPermission.KNOWLEDGE_READ, ToolPermission.DECISION_EXECUTE]
        self.enabled = True

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext):
        output = self._skill.execute(input_data)
        if output.success:
            return self._result(input_data, output.model_dump())
        return self._error(output.error or "Skill execution failed")


def register_skill_tools() -> list[str]:
    names: list[str] = []
    for skill in list_skills():
        tool = SkillTool(skill)
        register_tool(tool)
        names.append(tool.name)
    return names
