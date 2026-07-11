"""Base tool implementation helpers."""

from __future__ import annotations

from typing import Any

from ai_os.agent.ids import new_invocation_id
from ai_os.agent.models import ExecutionContext, ToolPermission, ToolResult


class BaseTool:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permissions: list[ToolPermission]
    enabled: bool = True

    def _result(self, input_data: dict[str, Any], output: dict[str, Any]) -> ToolResult:
        return ToolResult(
            invocation_id=new_invocation_id(),
            tool_name=self.name,
            success=True,
            output=output,
        )

    def _error(self, message: str) -> ToolResult:
        return ToolResult(
            invocation_id=new_invocation_id(),
            tool_name=self.name,
            success=False,
            error=message,
        )

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext) -> ToolResult:
        raise NotImplementedError
