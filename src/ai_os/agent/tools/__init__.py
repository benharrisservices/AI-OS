"""Tool protocol and registry."""

from __future__ import annotations

from typing import Any, Protocol

from ai_os.agent.models import ExecutionContext, ToolPermission, ToolResult


class Tool(Protocol):
    """A callable capability exposed to the Agent Runtime."""

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    permissions: list[ToolPermission]
    enabled: bool

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext) -> ToolResult: ...


_REGISTRY: dict[str, Tool] = {}


def register_tool(tool: Tool) -> None:
    _REGISTRY[tool.name] = tool


def get_tool(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def list_tools(*, enabled_only: bool = False) -> list[Tool]:
    tools = list(_REGISTRY.values())
    if enabled_only:
        tools = [t for t in tools if t.enabled]
    return sorted(tools, key=lambda t: t.name)


def discover_tools(settings: AgentSettings | None = None) -> list[str]:
    """Load and register all built-in tools; return registered names."""
    from ai_os.agent.config import AgentSettings
    from ai_os.agent.tools.builtin import register_builtin_tools

    register_builtin_tools(settings or AgentSettings())
    return list(_REGISTRY.keys())
