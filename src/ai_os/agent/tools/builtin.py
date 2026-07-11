"""Built-in tool implementations."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from ai_os.agent.config import AgentSettings
from ai_os.agent.models import ExecutionContext, ToolPermission
from ai_os.agent.tools import register_tool
from ai_os.agent.tools.base import BaseTool
from ai_os.decision.models import DecisionRequest, ReasoningStrategyName
from ai_os.decision.pipeline import DecisionPipeline
from ai_os.knowledge.models import RetrievalQuery
from ai_os.knowledge.retrieval import KnowledgeRetrieval


class KnowledgeRetrieveTool(BaseTool):
    name = "knowledge_retrieve"
    description = "Retrieve supporting knowledge via the Knowledge Engine."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "default": 8},
            "mode": {"type": "string", "default": "hybrid"},
        },
        "required": ["query"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "chunk_count": {"type": "integer"},
            "citations": {"type": "array"},
            "token_estimate": {"type": "integer"},
        },
    }
    permissions = [ToolPermission.KNOWLEDGE_READ]

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext) -> ToolResult:
        bundle = KnowledgeRetrieval().retrieve(
            RetrievalQuery(
                query=input_data["query"],
                top_k=input_data.get("top_k", 8),
                mode=input_data.get("mode", "hybrid"),
            )
        )
        return self._result(
            input_data,
            {
                "query": bundle.query,
                "chunk_count": len(bundle.chunks),
                "token_estimate": bundle.token_estimate,
                "citations": [c.model_dump() for c in bundle.citations],
                "chunks": [c.model_dump() for c in bundle.chunks],
            },
        )


class DecisionMakeTool(BaseTool):
    name = "decision_make"
    description = "Run the Decision Engine on a question."
    input_schema = {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "strategy": {"type": "string", "default": "analytical"},
            "context": {"type": "string"},
        },
        "required": ["question"],
    }
    output_schema = {
        "type": "object",
        "properties": {
            "decision_id": {"type": "string"},
            "recommendation": {"type": "object"},
            "confidence": {"type": "number"},
        },
    }
    permissions = [ToolPermission.DECISION_EXECUTE]

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext) -> ToolResult:
        strategy_name = input_data.get("strategy", "analytical")
        try:
            strategy = ReasoningStrategyName(strategy_name)
        except ValueError:
            return self._error(f"Unknown strategy: {strategy_name}")

        result = DecisionPipeline().decide(
            DecisionRequest(
                question=input_data["question"],
                strategy=strategy,
                context=input_data.get("context"),
            )
        )
        return self._result(
            input_data,
            {
                "decision_id": result.decision_id,
                "confidence": result.confidence,
                "recommendation": result.recommendation.model_dump() if result.recommendation else None,
                "summary": result.recommendation.summary if result.recommendation else None,
                "options_count": len(result.options),
            },
        )


class FilesystemReadTool(BaseTool):
    name = "filesystem_read"
    description = "Read a local file."
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }
    output_schema = {"type": "object", "properties": {"content": {"type": "string"}}}
    permissions = [ToolPermission.FILESYSTEM_READ]

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext) -> ToolResult:
        path = Path(input_data["path"]).expanduser()
        if not path.exists():
            return self._error(f"File not found: {path}")
        return self._result(input_data, {"content": path.read_text(encoding="utf-8"), "path": str(path)})


class FilesystemWriteTool(BaseTool):
    name = "filesystem_write"
    description = "Write content to a local file."
    input_schema = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string"},
        },
        "required": ["path", "content"],
    }
    output_schema = {"type": "object", "properties": {"path": {"type": "string"}, "bytes_written": {"type": "integer"}}}
    permissions = [ToolPermission.FILESYSTEM_WRITE]

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext) -> ToolResult:
        path = Path(input_data["path"]).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        content = input_data["content"]
        path.write_text(content, encoding="utf-8")
        return self._result(input_data, {"path": str(path), "bytes_written": len(content.encode("utf-8"))})


class FilesystemListTool(BaseTool):
    name = "filesystem_list"
    description = "List files in a local directory."
    input_schema = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }
    output_schema = {"type": "object", "properties": {"files": {"type": "array"}}}
    permissions = [ToolPermission.FILESYSTEM_READ]

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext) -> ToolResult:
        path = Path(input_data["path"]).expanduser()
        if not path.is_dir():
            return self._error(f"Not a directory: {path}")
        files = [str(p) for p in sorted(path.iterdir())]
        return self._result(input_data, {"files": files, "count": len(files)})


class ShellExecTool(BaseTool):
    name = "shell_exec"
    description = "Execute a shell command (disabled by default)."
    input_schema = {
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    }
    output_schema = {"type": "object", "properties": {"stdout": {"type": "string"}, "exit_code": {"type": "integer"}}}
    permissions = [ToolPermission.SHELL_EXECUTE]
    enabled = False

    def __init__(self, settings: AgentSettings | None = None) -> None:
        self._settings = settings or AgentSettings()
        self.enabled = self._settings.shell_enabled

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext) -> ToolResult:
        if not self.enabled:
            return self._error("Shell execution is disabled. Set AGENT_SHELL_ENABLED=true to enable.")
        import subprocess

        try:
            proc = subprocess.run(
                input_data["command"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return self._result(
                input_data,
                {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode},
            )
        except Exception as exc:
            return self._error(str(exc))


class HttpRequestTool(BaseTool):
    name = "http_request"
    description = "Make an HTTP GET request."
    input_schema = {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "method": {"type": "string", "default": "GET"},
        },
        "required": ["url"],
    }
    output_schema = {"type": "object", "properties": {"status_code": {"type": "integer"}, "body": {"type": "string"}}}
    permissions = [ToolPermission.HTTP_REQUEST]

    def __init__(self, settings: AgentSettings | None = None) -> None:
        self._settings = settings or AgentSettings()
        self.enabled = self._settings.http_enabled

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext) -> ToolResult:
        if not self.enabled:
            return self._error("HTTP requests are disabled.")
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.request(input_data.get("method", "GET"), input_data["url"])
            return self._result(
                input_data,
                {
                    "status_code": response.status_code,
                    "body": response.text[:4000],
                    "url": str(response.url),
                },
            )
        except Exception as exc:
            return self._error(str(exc))


class DateTimeNowTool(BaseTool):
    name = "datetime_now"
    description = "Return the current UTC date and time."
    input_schema = {"type": "object", "properties": {}}
    output_schema = {
        "type": "object",
        "properties": {
            "iso": {"type": "string"},
            "timestamp": {"type": "number"},
        },
    }
    permissions = [ToolPermission.SYSTEM_READ]

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext) -> ToolResult:
        now = datetime.now(timezone.utc)
        return self._result(
            input_data,
            {"iso": now.isoformat(), "timestamp": now.timestamp(), "timezone": "UTC"},
        )


def register_builtin_tools(settings: AgentSettings | None = None) -> None:
    settings = settings or AgentSettings()
    for tool in (
        KnowledgeRetrieveTool(),
        DecisionMakeTool(),
        FilesystemReadTool(),
        FilesystemWriteTool(),
        FilesystemListTool(),
        ShellExecTool(settings),
        HttpRequestTool(settings),
        DateTimeNowTool(),
    ):
        register_tool(tool)
