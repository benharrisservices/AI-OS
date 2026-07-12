"""Automation Layer tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml

from ai_os.agent.models import ExecutionResult, TaskStatus
from ai_os.automation.config import AutomationSettings
from ai_os.automation.models import (
    Automation,
    AutomationPolicy,
    AutomationStatus,
    ExecutionStatus,
    ScheduleSpec,
    ScheduleType,
    TriggerSpec,
    TriggerType,
    utc_now,
)
from ai_os.automation.scheduler import compute_next_run, is_due
from ai_os.automation.service import AutomationService
from ai_os.automation.store import AutomationStore


@pytest.fixture
def automation_settings(tmp_path: Path) -> AutomationSettings:
    base = tmp_path / "automation"
    return AutomationSettings(
        AUTOMATION_DEFINITIONS_DIR=base / "definitions",
        AUTOMATION_HISTORY_DIR=base / "history",
        AUTOMATION_STATE_DIR=base / "state",
        AUTOMATION_DEFAULT_BACKOFF_SECONDS=0,
    )


@pytest.fixture
def mock_engine() -> MagicMock:
    engine = MagicMock()
    engine.run_workflow.return_value = ExecutionResult(
        task_id="task_auto_test",
        status=TaskStatus.COMPLETED,
        duration_ms=10,
    )
    return engine


def _write_automation(settings: AutomationSettings, automation: Automation) -> None:
    settings.automations_dir.mkdir(parents=True, exist_ok=True)
    path = settings.automations_dir / f"{automation.automation_id}.yaml"
    path.write_text(
        yaml.dump(automation.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )


@pytest.fixture
def sample_automation(automation_settings: AutomationSettings) -> Automation:
    automation = Automation(
        automation_id="test-auto",
        name="Test Automation",
        description="Test",
        workflow_id="test-flow",
        input={"key": "value"},
        trigger=TriggerSpec(trigger_type=TriggerType.MANUAL),
        policy=AutomationPolicy(max_retries=1, concurrency_limit=1, backoff_seconds=0),
    )
    _write_automation(automation_settings, automation)
    return automation


class TestContracts:
    def test_automation_defaults(self) -> None:
        auto = Automation(
            automation_id="auto_x",
            name="X",
            workflow_id="wf",
            trigger=TriggerSpec(trigger_type=TriggerType.MANUAL),
        )
        assert auto.status == AutomationStatus.ENABLED
        assert auto.policy.max_retries == 3

    def test_execution_status_values(self) -> None:
        assert ExecutionStatus.SCHEDULED.value == "scheduled"
        assert ExecutionStatus.CANCELLED.value == "cancelled"


class TestScheduler:
    def test_one_time_future(self) -> None:
        future = utc_now() + timedelta(hours=2)
        schedule = ScheduleSpec(schedule_type=ScheduleType.ONE_TIME, run_at=future)
        assert compute_next_run(schedule) == future

    def test_one_time_past_returns_none(self) -> None:
        past = utc_now() - timedelta(hours=1)
        schedule = ScheduleSpec(schedule_type=ScheduleType.ONE_TIME, run_at=past)
        assert compute_next_run(schedule) is None

    def test_recurring_interval(self) -> None:
        schedule = ScheduleSpec(schedule_type=ScheduleType.RECURRING, interval_seconds=3600)
        nxt = compute_next_run(schedule)
        assert nxt is not None
        assert nxt > utc_now()

    def test_delayed_execution(self) -> None:
        schedule = ScheduleSpec(schedule_type=ScheduleType.DELAYED, delay_seconds=300)
        nxt = compute_next_run(schedule)
        assert nxt is not None
        assert nxt <= utc_now() + timedelta(seconds=301)

    def test_cron_next_run(self) -> None:
        schedule = ScheduleSpec(schedule_type=ScheduleType.CRON, cron_expression="0 9 * * *")
        after = datetime(2026, 7, 11, 8, 0, tzinfo=timezone.utc)
        nxt = compute_next_run(schedule, after=after)
        assert nxt.hour == 9
        assert nxt.minute == 0

    def test_is_due(self) -> None:
        past = utc_now() - timedelta(minutes=5)
        assert is_due(past) is True
        future = utc_now() + timedelta(hours=1)
        assert is_due(future) is False


class TestPolicies:
    def test_enable_disable(self, automation_settings: AutomationSettings, sample_automation: Automation) -> None:
        service = AutomationService(automation_settings)
        service.disable("test-auto")
        auto = service.get_automation("test-auto")
        assert auto is not None
        assert auto.status == AutomationStatus.DISABLED
        service.enable("test-auto")
        auto = service.get_automation("test-auto")
        assert auto is not None
        assert auto.status == AutomationStatus.ENABLED

    def test_pause(self, automation_settings: AutomationSettings, sample_automation: Automation) -> None:
        service = AutomationService(automation_settings)
        service.pause("test-auto")
        assert service.get_automation("test-auto").status == AutomationStatus.PAUSED

    def test_disabled_cannot_run(
        self, automation_settings: AutomationSettings, sample_automation: Automation, mock_engine: MagicMock
    ) -> None:
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        service.disable("test-auto")
        with pytest.raises(ValueError, match="disabled"):
            service.run("test-auto")

    def test_concurrency_limit(
        self, automation_settings: AutomationSettings, sample_automation: Automation, mock_engine: MagicMock
    ) -> None:
        store = AutomationStore(automation_settings)
        store.increment_active_runs("test-auto")
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        record = service.run("test-auto")
        assert record.status == ExecutionStatus.CANCELLED
        mock_engine.run_workflow.assert_not_called()

    def test_retry_on_failure(
        self, automation_settings: AutomationSettings, sample_automation: Automation, mock_engine: MagicMock
    ) -> None:
        mock_engine.run_workflow.return_value = ExecutionResult(
            task_id="task_fail",
            status=TaskStatus.FAILED,
            error="step failed",
            duration_ms=5,
        )
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        record = service.run("test-auto")
        assert record.status == ExecutionStatus.FAILED
        assert record.retry_count == 1
        assert mock_engine.run_workflow.call_count == 2


class TestTriggers:
    def test_manual_run(
        self, automation_settings: AutomationSettings, sample_automation: Automation, mock_engine: MagicMock
    ) -> None:
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        record = service.run("test-auto", trigger_type=TriggerType.MANUAL)
        assert record.status == ExecutionStatus.COMPLETED
        assert record.trigger_type == TriggerType.MANUAL
        mock_engine.run_workflow.assert_called_once()

    def test_filesystem_trigger(
        self, automation_settings: AutomationSettings, mock_engine: MagicMock
    ) -> None:
        automation = Automation(
            automation_id="fs-auto",
            name="FS",
            workflow_id="wf",
            trigger=TriggerSpec(
                trigger_type=TriggerType.FILESYSTEM,
                watch_path="/tmp",
                watch_pattern="*.md",
            ),
        )
        _write_automation(automation_settings, automation)
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        results = service.on_filesystem_event("/tmp/notes.md")
        assert len(results) == 1
        assert results[0].trigger_type == TriggerType.FILESYSTEM

    def test_workflow_completion_trigger(
        self, automation_settings: AutomationSettings, mock_engine: MagicMock
    ) -> None:
        automation = Automation(
            automation_id="wf-auto",
            name="WF",
            workflow_id="followup",
            trigger=TriggerSpec(
                trigger_type=TriggerType.WORKFLOW_COMPLETION,
                source_workflow_id="daily-review",
            ),
        )
        _write_automation(automation_settings, automation)
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        results = service.on_workflow_completed("daily-review", "task_1", success=True)
        assert len(results) == 1

    def test_webhook_trigger(
        self, automation_settings: AutomationSettings, mock_engine: MagicMock
    ) -> None:
        automation = Automation(
            automation_id="hook-auto",
            name="Hook",
            workflow_id="wf",
            trigger=TriggerSpec(trigger_type=TriggerType.WEBHOOK, webhook_token="secret123"),
        )
        _write_automation(automation_settings, automation)
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        record = service.trigger_webhook("hook-auto", "secret123")
        assert record.status == ExecutionStatus.COMPLETED

    def test_webhook_invalid_token(
        self, automation_settings: AutomationSettings, mock_engine: MagicMock
    ) -> None:
        automation = Automation(
            automation_id="hook-auto",
            name="Hook",
            workflow_id="wf",
            trigger=TriggerSpec(trigger_type=TriggerType.WEBHOOK, webhook_token="secret123"),
        )
        _write_automation(automation_settings, automation)
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        with pytest.raises(ValueError, match="Invalid webhook token"):
            service.trigger_webhook("hook-auto", "wrong")

    def test_startup_trigger(
        self, automation_settings: AutomationSettings, mock_engine: MagicMock
    ) -> None:
        automation = Automation(
            automation_id="boot-auto",
            name="Boot",
            workflow_id="wf",
            trigger=TriggerSpec(trigger_type=TriggerType.STARTUP),
        )
        _write_automation(automation_settings, automation)
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        results = service.on_startup()
        assert len(results) == 1
        assert results[0].trigger_type == TriggerType.STARTUP
        assert service.on_startup() == []


class TestHistory:
    def test_execution_record_fields(
        self, automation_settings: AutomationSettings, sample_automation: Automation, mock_engine: MagicMock
    ) -> None:
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        record = service.run("test-auto")
        assert record.execution_id.startswith("aexec_")
        assert record.duration_ms >= 0
        assert record.started_at is not None
        assert record.completed_at is not None

    def test_history_listing(
        self, automation_settings: AutomationSettings, sample_automation: Automation, mock_engine: MagicMock
    ) -> None:
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        service.run("test-auto")
        history = service.history("test-auto")
        assert len(history) >= 1
        assert history[0].automation_id == "test-auto"


class TestSchedule:
    def test_schedule_cron(
        self, automation_settings: AutomationSettings, sample_automation: Automation
    ) -> None:
        service = AutomationService(automation_settings)
        auto = service.schedule("test-auto", cron="0 8 * * *")
        assert auto.schedule is not None
        assert auto.schedule.cron_expression == "0 8 * * *"
        assert auto.next_run_at is not None

    def test_tick_runs_due(
        self, automation_settings: AutomationSettings, mock_engine: MagicMock
    ) -> None:
        automation = Automation(
            automation_id="due-auto",
            name="Due",
            workflow_id="wf",
            schedule=ScheduleSpec(schedule_type=ScheduleType.RECURRING, interval_seconds=60),
            trigger=TriggerSpec(trigger_type=TriggerType.SCHEDULE),
            next_run_at=utc_now() - timedelta(minutes=1),
        )
        _write_automation(automation_settings, automation)
        service = AutomationService(automation_settings, execution_engine=mock_engine)
        results = service.tick()
        assert len(results) == 1
        assert results[0].status == ExecutionStatus.COMPLETED


class TestPersistence:
    def test_store_round_trip(self, automation_settings: AutomationSettings) -> None:
        from ai_os.automation.ids import new_execution_id
        from ai_os.automation.models import ExecutionRecord

        store = AutomationStore(automation_settings)
        record = ExecutionRecord(
            execution_id=new_execution_id(),
            automation_id="auto_x",
            workflow_id="wf",
            trigger_type=TriggerType.MANUAL,
            status=ExecutionStatus.COMPLETED,
            duration_ms=42,
        )
        store.save_execution(record)
        loaded = store.get_execution(record.execution_id)
        assert loaded is not None
        assert loaded.duration_ms == 42

    def test_no_knowledge_import(self) -> None:
        import ai_os.automation.service as service_module

        source = Path(service_module.__file__).read_text(encoding="utf-8")
        assert "ai_os.knowledge" not in source
        assert "ai_os.decision" not in source
