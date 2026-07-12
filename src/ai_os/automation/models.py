"""Automation Layer contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AutomationStatus(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    PAUSED = "paused"


class ScheduleType(str, Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring"
    CRON = "cron"
    DELAYED = "delayed"


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    FILESYSTEM = "filesystem"
    WORKFLOW_COMPLETION = "workflow_completion"
    WEBHOOK = "webhook"
    STARTUP = "startup"


class ExecutionStatus(str, Enum):
    SCHEDULED = "scheduled"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutomationPolicy(BaseModel):
    """Controls how an automation runs and recovers from failure."""

    max_retries: int = Field(default=3, ge=0)
    concurrency_limit: int = Field(default=1, ge=1)
    timeout_seconds: int = Field(default=300, ge=1)
    backoff_seconds: int = Field(default=60, ge=0)
    pause_on_failure: bool = Field(default=False)


class ScheduleSpec(BaseModel):
    """When a scheduled automation should run."""

    schedule_type: ScheduleType
    run_at: datetime | None = Field(default=None, description="Absolute time for one_time.")
    delay_seconds: int | None = Field(default=None, description="Delay from trigger for delayed.")
    interval_seconds: int | None = Field(default=None, description="Interval for recurring.")
    cron_expression: str | None = Field(default=None, description="5-field cron for cron type.")


class TriggerSpec(BaseModel):
    """What event causes an automation to run."""

    trigger_type: TriggerType
    watch_path: str | None = Field(default=None, description="Directory to watch for filesystem.")
    watch_pattern: str | None = Field(default=None, description="Glob pattern for filesystem events.")
    source_workflow_id: str | None = Field(
        default=None,
        description="Workflow ID that triggers on completion.",
    )
    webhook_token: str | None = Field(default=None, description="Token for webhook validation.")


class Automation(BaseModel):
    """A workflow automation definition."""

    schema_version: str = "1.0"
    automation_id: str
    name: str
    description: str = ""
    workflow_id: str
    input: dict[str, Any] = Field(default_factory=dict)
    schedule: ScheduleSpec | None = None
    trigger: TriggerSpec
    policy: AutomationPolicy = Field(default_factory=AutomationPolicy)
    status: AutomationStatus = AutomationStatus.ENABLED
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None


class ExecutionRecord(BaseModel):
    """History of a single automation execution."""

    schema_version: str = "1.0"
    execution_id: str
    automation_id: str
    workflow_id: str
    task_id: str | None = None
    trigger_type: TriggerType
    status: ExecutionStatus
    scheduled_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int = 0
    retry_count: int = 0
    error: str | None = None
