"""Agent Runtime contracts — provider-agnostic, multi-agent ready."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class StepFailureAction(str, Enum):
    RETRY = "retry"
    FAIL = "fail"
    SKIP = "skip"


class ToolPermission(str, Enum):
    KNOWLEDGE_READ = "knowledge:read"
    DECISION_EXECUTE = "decision:execute"
    FILESYSTEM_READ = "filesystem:read"
    FILESYSTEM_WRITE = "filesystem:write"
    SHELL_EXECUTE = "shell:execute"
    HTTP_REQUEST = "http:request"
    SYSTEM_READ = "system:read"


class Agent(BaseModel):
    """An autonomous executor with a defined tool scope.

    Supports future multi-agent execution via ``agent_id`` and delegation fields.
    """

    agent_id: str = Field(description="Stable agent identifier.")
    name: str = Field(description="Human-readable agent name.")
    description: str = Field(description="What this agent is responsible for.")
    tools: list[str] = Field(description="Tool names this agent may invoke.")
    permissions: list[ToolPermission] = Field(
        default_factory=list,
        description="Granted permissions; enforced at tool invocation.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowStep(BaseModel):
    """A single step in a reusable workflow definition."""

    step_id: str = Field(description="Unique step identifier within the workflow.")
    name: str = Field(description="Human-readable step label.")
    tool_name: str = Field(description="Tool to invoke for this step.")
    input: dict[str, Any] = Field(
        default_factory=dict,
        description="Tool input; values may reference context via templates.",
    )
    on_failure: StepFailureAction = Field(
        default=StepFailureAction.RETRY,
        description="Behavior when the step fails.",
    )
    max_retries: int = Field(default=3, description="Retries allowed for this step.")


class Workflow(BaseModel):
    """Reusable workflow definition — not hard-coded execution logic."""

    workflow_id: str = Field(description="Stable workflow identifier.")
    name: str = Field(description="Human-readable workflow name.")
    description: str = Field(description="What this workflow accomplishes.")
    version: str = Field(default="1.0.0", description="Workflow definition version.")
    agent_id: str | None = Field(
        default=None,
        description="Default agent; may be overridden at run time.",
    )
    steps: list[WorkflowStep] = Field(description="Ordered steps to execute.")


class ExecutionContext(BaseModel):
    """Mutable context passed between workflow steps."""

    task_id: str = Field(description="Owning task identifier.")
    agent_id: str | None = Field(default=None, description="Agent executing this task.")
    workflow_id: str | None = Field(default=None, description="Workflow being executed.")
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Accumulated variables from step outputs.",
    )
    parent_task_id: str | None = Field(
        default=None,
        description="Parent task for delegated sub-workflows (multi-agent future).",
    )
    step_outputs: dict[str, dict[str, Any]] = Field(
        default_factory=dict,
        description="Outputs keyed by step_id.",
    )


class AgentTask(BaseModel):
    """A unit of work to be executed by the Agent Runtime."""

    schema_version: str = "1.0"
    task_id: str = Field(description="Unique task identifier.")
    agent_id: str | None = Field(default=None, description="Agent assigned to this task.")
    workflow_id: str | None = Field(default=None, description="Workflow driving this task.")
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    input: dict[str, Any] = Field(default_factory=dict, description="Task input parameters.")
    output: dict[str, Any] = Field(default_factory=dict, description="Final task output.")
    context: ExecutionContext = Field(description="Execution context for step passing.")
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class ToolInvocation(BaseModel):
    """Record of a single tool call during execution."""

    invocation_id: str
    task_id: str
    step_id: str | None = None
    tool_name: str
    input: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    error: str | None = None


class ToolResult(BaseModel):
    """Output of a tool invocation."""

    invocation_id: str
    tool_name: str
    success: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ExecutionResult(BaseModel):
    """Final result of executing a task or workflow."""

    task_id: str
    status: TaskStatus
    outputs: dict[str, Any] = Field(default_factory=dict)
    steps_completed: list[str] = Field(default_factory=list)
    tool_invocations: list[ToolInvocation] = Field(default_factory=list)
    duration_ms: int = 0
    error: str | None = None
