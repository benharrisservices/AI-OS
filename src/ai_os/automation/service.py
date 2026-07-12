"""Automation service — determines WHEN workflows execute."""

from __future__ import annotations

import fnmatch
import time
from pathlib import Path
from typing import Any

from ai_os.agent.engine import ExecutionEngine
from ai_os.agent.models import TaskStatus
from ai_os.automation.config import AutomationSettings
from ai_os.automation.ids import new_execution_id
from ai_os.automation.loader import AutomationLoader
from ai_os.automation.models import (
    Automation,
    AutomationStatus,
    ExecutionRecord,
    ExecutionStatus,
    ScheduleType,
    TriggerType,
    utc_now,
)
from ai_os.automation.scheduler import compute_next_run, is_due
from ai_os.automation.store import AutomationStore


class AutomationService:
    """Schedules and triggers workflow execution via Agent Runtime."""

    def __init__(
        self,
        settings: AutomationSettings | None = None,
        execution_engine: ExecutionEngine | None = None,
    ) -> None:
        self.settings = settings or AutomationSettings()
        self.settings.ensure_dirs()
        self.store = AutomationStore(self.settings)
        self.loader = AutomationLoader(self.settings)
        self.engine = execution_engine or ExecutionEngine(automation_service=self)
        self._startup_triggered: set[str] = set()

    def list_automations(self) -> list[Automation]:
        return self.loader.list_all()

    def get_automation(self, automation_id: str) -> Automation | None:
        return self.loader.load(automation_id)

    def enable(self, automation_id: str) -> Automation:
        automation = self._require(automation_id)
        automation.status = AutomationStatus.ENABLED
        automation.updated_at = utc_now()
        self._persist(automation)
        return automation

    def disable(self, automation_id: str) -> Automation:
        automation = self._require(automation_id)
        automation.status = AutomationStatus.DISABLED
        automation.updated_at = utc_now()
        self._persist(automation)
        return automation

    def pause(self, automation_id: str) -> Automation:
        automation = self._require(automation_id)
        automation.status = AutomationStatus.PAUSED
        automation.updated_at = utc_now()
        self._persist(automation)
        return automation

    def schedule(
        self,
        automation_id: str,
        *,
        run_at: str | None = None,
        delay_seconds: int | None = None,
        cron: str | None = None,
        interval_seconds: int | None = None,
    ) -> Automation:
        """Configure or update the schedule for an automation."""
        from datetime import datetime

        automation = self._require(automation_id)
        if cron:
            from ai_os.automation.models import ScheduleSpec

            automation.schedule = ScheduleSpec(
                schedule_type=ScheduleType.CRON,
                cron_expression=cron,
            )
        elif interval_seconds:
            from ai_os.automation.models import ScheduleSpec

            automation.schedule = ScheduleSpec(
                schedule_type=ScheduleType.RECURRING,
                interval_seconds=interval_seconds,
            )
        elif delay_seconds is not None:
            from ai_os.automation.models import ScheduleSpec

            automation.schedule = ScheduleSpec(
                schedule_type=ScheduleType.DELAYED,
                delay_seconds=delay_seconds,
            )
        elif run_at:
            from ai_os.automation.models import ScheduleSpec

            automation.schedule = ScheduleSpec(
                schedule_type=ScheduleType.ONE_TIME,
                run_at=datetime.fromisoformat(run_at),
            )

        if automation.schedule:
            automation.next_run_at = compute_next_run(automation.schedule)
        automation.updated_at = utc_now()
        self._persist(automation)
        return automation

    def run(
        self,
        automation_id: str,
        *,
        trigger_type: TriggerType = TriggerType.MANUAL,
        input_override: dict[str, Any] | None = None,
    ) -> ExecutionRecord:
        """Execute an automation immediately."""
        automation = self._require(automation_id)
        if automation.status == AutomationStatus.DISABLED:
            raise ValueError(f"Automation is disabled: {automation_id}")
        if automation.status == AutomationStatus.PAUSED:
            raise ValueError(f"Automation is paused: {automation_id}")

        active = self.store.get_active_run_count(automation_id)
        if active >= automation.policy.concurrency_limit:
            record = self._create_record(
                automation,
                trigger_type,
                status=ExecutionStatus.CANCELLED,
                error="Concurrency limit reached",
            )
            self.store.save_execution(record)
            return record

        record = self._create_record(automation, trigger_type, status=ExecutionStatus.SCHEDULED)
        self.store.save_execution(record)

        return self._execute_with_retries(automation, record, input_override or {})

    def history(self, automation_id: str | None = None, *, limit: int = 50) -> list[ExecutionRecord]:
        return self.store.list_executions(automation_id, limit=limit)

    def tick(self) -> list[ExecutionRecord]:
        """Process due scheduled automations."""
        results: list[ExecutionRecord] = []
        for automation in self.list_automations():
            if automation.status != AutomationStatus.ENABLED:
                continue
            if automation.trigger.trigger_type not in (TriggerType.SCHEDULE, TriggerType.MANUAL):
                if automation.schedule is None:
                    continue
            if automation.schedule is None:
                continue
            if not is_due(automation.next_run_at):
                continue
            record = self.run(automation.automation_id, trigger_type=TriggerType.SCHEDULE)
            results.append(record)
            automation.last_run_at = utc_now()
            if automation.schedule.schedule_type == ScheduleType.ONE_TIME:
                automation.next_run_at = None
            else:
                automation.next_run_at = compute_next_run(automation.schedule)
            self._persist(automation)
        return results

    def on_startup(self) -> list[ExecutionRecord]:
        """Fire startup triggers once per process lifetime."""
        results: list[ExecutionRecord] = []
        for automation in self.list_automations():
            if automation.trigger.trigger_type != TriggerType.STARTUP:
                continue
            if automation.automation_id in self._startup_triggered:
                continue
            if automation.status != AutomationStatus.ENABLED:
                continue
            self._startup_triggered.add(automation.automation_id)
            results.append(self.run(automation.automation_id, trigger_type=TriggerType.STARTUP))
        return results

    def on_workflow_completed(
        self,
        workflow_id: str,
        task_id: str,
        *,
        success: bool,
    ) -> list[ExecutionRecord]:
        """Fire workflow_completion triggers."""
        results: list[ExecutionRecord] = []
        for automation in self.list_automations():
            if automation.trigger.trigger_type != TriggerType.WORKFLOW_COMPLETION:
                continue
            if automation.status != AutomationStatus.ENABLED:
                continue
            source = automation.trigger.source_workflow_id
            if source and source != workflow_id:
                continue
            input_data = dict(automation.input)
            input_data["_trigger"] = {
                "workflow_id": workflow_id,
                "task_id": task_id,
                "success": success,
            }
            results.append(
                self.run(
                    automation.automation_id,
                    trigger_type=TriggerType.WORKFLOW_COMPLETION,
                    input_override=input_data,
                )
            )
        return results

    def on_filesystem_event(self, path: str) -> list[ExecutionRecord]:
        """Fire filesystem triggers matching the changed path."""
        results: list[ExecutionRecord] = []
        changed = Path(path)
        for automation in self.list_automations():
            if automation.trigger.trigger_type != TriggerType.FILESYSTEM:
                continue
            if automation.status != AutomationStatus.ENABLED:
                continue
            watch = automation.trigger.watch_path
            pattern = automation.trigger.watch_pattern or "*"
            if watch and not str(changed).startswith(str(Path(watch).expanduser())):
                continue
            if not fnmatch.fnmatch(changed.name, pattern):
                continue
            input_data = dict(automation.input)
            input_data["_trigger"] = {"path": str(changed)}
            results.append(
                self.run(
                    automation.automation_id,
                    trigger_type=TriggerType.FILESYSTEM,
                    input_override=input_data,
                )
            )
        return results

    def trigger_webhook(self, automation_id: str, token: str) -> ExecutionRecord:
        """Validate webhook token and run automation."""
        automation = self._require(automation_id)
        if automation.trigger.trigger_type != TriggerType.WEBHOOK:
            raise ValueError(f"Automation is not a webhook trigger: {automation_id}")
        expected = automation.trigger.webhook_token
        if not expected or expected != token:
            raise ValueError("Invalid webhook token")
        return self.run(automation.automation_id, trigger_type=TriggerType.WEBHOOK)

    def _execute_with_retries(
        self,
        automation: Automation,
        record: ExecutionRecord,
        input_data: dict[str, Any],
    ) -> ExecutionRecord:
        max_retries = automation.policy.max_retries
        backoff = automation.policy.backoff_seconds

        for attempt in range(max_retries + 1):
            if attempt > 0:
                record.retry_count = attempt
                record.status = ExecutionStatus.SCHEDULED
                self.store.save_execution(record)
                time.sleep(backoff)

            record.status = ExecutionStatus.STARTED
            record.started_at = utc_now()
            self.store.save_execution(record)
            self.store.increment_active_runs(automation.automation_id)
            start = time.perf_counter()
            try:
                result = self.engine.run_workflow(automation.workflow_id, input_data)
                duration_ms = int((time.perf_counter() - start) * 1000)

                if result.status == TaskStatus.COMPLETED:
                    record.status = ExecutionStatus.COMPLETED
                    record.task_id = result.task_id
                    record.duration_ms = duration_ms
                    record.completed_at = utc_now()
                    record.error = None
                    self.store.save_execution(record)
                    automation.last_run_at = utc_now()
                    self._persist(automation)
                    return record

                record.error = result.error or "Workflow failed"
                record.duration_ms = duration_ms
            except Exception as exc:
                record.error = str(exc)
                record.duration_ms = int((time.perf_counter() - start) * 1000)
            finally:
                self.store.decrement_active_runs(automation.automation_id)

            record.completed_at = utc_now()

            if attempt < max_retries:
                record.status = ExecutionStatus.SCHEDULED
            else:
                record.status = ExecutionStatus.FAILED
                if automation.policy.pause_on_failure:
                    automation.status = AutomationStatus.PAUSED
                    self._persist(automation)

            self.store.save_execution(record)

        return record

    def _create_record(
        self,
        automation: Automation,
        trigger_type: TriggerType,
        *,
        status: ExecutionStatus = ExecutionStatus.SCHEDULED,
        error: str | None = None,
    ) -> ExecutionRecord:
        return ExecutionRecord(
            execution_id=new_execution_id(),
            automation_id=automation.automation_id,
            workflow_id=automation.workflow_id,
            trigger_type=trigger_type,
            status=status,
            error=error,
        )

    def _require(self, automation_id: str) -> Automation:
        automation = self.loader.load(automation_id)
        if automation is None:
            raise ValueError(f"Automation not found: {automation_id}")
        return automation

    def _persist(self, automation: Automation) -> None:
        self.loader.save(automation)
        self.store.save_runtime_state(automation)
