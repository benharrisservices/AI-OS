"""Agent Runtime tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from ai_os.agent.config import AgentSettings
from ai_os.agent.engine import ExecutionEngine
from ai_os.agent.models import (
    Agent,
    AgentTask,
    ExecutionContext,
    StepFailureAction,
    TaskStatus,
    ToolPermission,
    Workflow,
    WorkflowStep,
)
from ai_os.agent.resolve import build_bindings, resolve_value
from ai_os.agent.store import TaskStore
from ai_os.agent.tools import discover_tools, get_tool, list_tools, register_tool
from ai_os.agent.tools.base import BaseTool
from ai_os.agent.workflows import AgentLoader, WorkflowLoader
from ai_os.memory.config import MemorySettings
from ai_os.memory.manager import MemoryManager


@pytest.fixture
def memory_settings(tmp_path: Path) -> MemorySettings:
    base = tmp_path / "memory"
    settings = MemorySettings(
        MEMORY_WORKING_DIR=base / "working",
        MEMORY_EPISODIC_DIR=base / "episodic",
        MEMORY_SEMANTIC_DIR=base / "semantic",
        MEMORY_PROCEDURAL_DIR=base / "procedural",
        MEMORY_WORKING_TTL_MINUTES=30,
    )
    settings.ensure_dirs()
    return settings


@pytest.fixture
def memory_manager(memory_settings: MemorySettings) -> MemoryManager:
    return MemoryManager(memory_settings)


def _engine(agent_settings: AgentSettings, memory_manager: MemoryManager) -> ExecutionEngine:
    return ExecutionEngine(agent_settings, memory_manager=memory_manager)


@pytest.fixture
def agent_settings(tmp_path: Path) -> AgentSettings:
    base = tmp_path / "agent"
    settings = AgentSettings(
        AGENT_TASKS_DIR=base / "tasks",
        AGENT_LOGS_DIR=base / "logs",
        AGENT_WORKFLOWS_DIR=base / "workflows",
        AGENT_DEFINITIONS_DIR=base / "agents",
        AGENT_SHELL_ENABLED=False,
        AGENT_HTTP_ENABLED=True,
    )
    settings.ensure_dirs()
    return settings


@pytest.fixture
def sample_workflow(agent_settings: AgentSettings) -> Workflow:
    workflow = Workflow(
        workflow_id="test-flow",
        name="Test Flow",
        description="Sequential tool execution test",
        agent_id="agt_tester",
        steps=[
            WorkflowStep(step_id="timestamp", name="Timestamp", tool_name="datetime_now", input={}),
            WorkflowStep(
                step_id="write",
                name="Write output",
                tool_name="filesystem_write",
                input={
                    "path": "{{input.output_path}}",
                    "content": "completed at {{vars.iso}}",
                },
            ),
        ],
    )
    path = agent_settings.workflows_dir / "test-flow.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(workflow.model_dump(mode="json"), sort_keys=False), encoding="utf-8")
    return workflow


@pytest.fixture
def sample_agent(agent_settings: AgentSettings) -> Agent:
    agent = Agent(
        agent_id="agt_tester",
        name="Tester",
        description="Test agent",
        tools=["datetime_now", "filesystem_write"],
        permissions=[ToolPermission.SYSTEM_READ, ToolPermission.FILESYSTEM_WRITE],
    )
    path = agent_settings.agents_dir / "tester.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(agent.model_dump(mode="json"), sort_keys=False), encoding="utf-8")
    return agent


class TestContracts:
    def test_agent_task_defaults(self) -> None:
        task = AgentTask(
            task_id="task_test",
            context=ExecutionContext(task_id="task_test"),
        )
        assert task.status == TaskStatus.PENDING
        assert task.max_retries == 3

    def test_workflow_step_failure_action(self) -> None:
        step = WorkflowStep(
            step_id="s1",
            name="Step",
            tool_name="datetime_now",
            on_failure=StepFailureAction.SKIP,
        )
        assert step.on_failure == StepFailureAction.SKIP


class TestResolve:
    def test_resolve_input_reference(self) -> None:
        bindings = build_bindings(
            task_input={"topic": "review"},
            step_outputs={},
            variables={},
        )
        assert resolve_value("{{input.topic}}", bindings) == "review"

    def test_resolve_step_output(self) -> None:
        bindings = build_bindings(
            task_input={},
            step_outputs={"decide": {"summary": "Proceed"}},
            variables={},
        )
        assert resolve_value("{{steps.decide.summary}}", bindings) == "Proceed"

    def test_resolve_missing_key(self) -> None:
        bindings = build_bindings(task_input={}, step_outputs={}, variables={})
        assert "MISSING" in resolve_value("{{vars.missing}}", bindings)


class TestToolRegistry:
    def test_discover_builtin_tools(self, agent_settings: AgentSettings) -> None:
        names = discover_tools(agent_settings)
        assert "knowledge_retrieve" in names
        assert "decision_make" in names
        assert "datetime_now" in names
        assert "shell_exec" in names

    def test_shell_disabled_by_default(self, agent_settings: AgentSettings) -> None:
        discover_tools(agent_settings)
        shell = get_tool("shell_exec")
        assert shell is not None
        assert shell.enabled is False

    def test_tool_has_schema_and_permissions(self, agent_settings: AgentSettings) -> None:
        discover_tools(agent_settings)
        tool = get_tool("filesystem_read")
        assert tool is not None
        assert "path" in tool.input_schema["properties"]
        assert ToolPermission.FILESYSTEM_READ in tool.permissions


class FlakyTool(BaseTool):
    name = "flaky"
    description = "Fails then succeeds"
    input_schema = {"type": "object", "properties": {}}
    output_schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
    permissions: list[ToolPermission] = []

    def __init__(self) -> None:
        self.attempts = 0

    def invoke(self, input_data: dict[str, Any], context: ExecutionContext):
        self.attempts += 1
        if self.attempts < 2:
            return self._error("transient failure")
        return self._result(input_data, {"ok": True})


class TestExecutionEngine:
    def test_workflow_execution(
        self,
        agent_settings: AgentSettings,
        memory_manager: MemoryManager,
        sample_workflow: Workflow,
        sample_agent: Agent,
    ) -> None:
        discover_tools(agent_settings)
        engine = _engine(agent_settings, memory_manager)
        output_path = str(agent_settings.tasks_dir / "result.txt")
        result = engine.run_workflow("test-flow", {"output_path": output_path})

        assert result.status == TaskStatus.COMPLETED
        assert result.steps_completed == ["timestamp", "write"]
        assert Path(output_path).exists()
        assert "completed at" in Path(output_path).read_text(encoding="utf-8")

    def test_task_state_transitions(
        self,
        agent_settings: AgentSettings,
        memory_manager: MemoryManager,
        sample_workflow: Workflow,
        sample_agent: Agent,
    ) -> None:
        discover_tools(agent_settings)
        engine = _engine(agent_settings, memory_manager)
        task = engine.create_task(workflow_id="test-flow", input_data={"output_path": "/tmp/x"})
        assert task.status == TaskStatus.PENDING

        result = engine.execute_task(task.task_id)
        stored = engine.store.get_task(task.task_id)
        assert stored is not None
        assert result.status == TaskStatus.COMPLETED
        assert stored.status == TaskStatus.COMPLETED
        assert stored.started_at is not None
        assert stored.completed_at is not None

    def test_execution_logging(
        self,
        agent_settings: AgentSettings,
        memory_manager: MemoryManager,
        sample_workflow: Workflow,
        sample_agent: Agent,
    ) -> None:
        discover_tools(agent_settings)
        engine = _engine(agent_settings, memory_manager)
        result = engine.run_workflow(
            "test-flow",
            {"output_path": str(agent_settings.tasks_dir / "logged.txt")},
        )
        logs = engine.store.get_logs(result.task_id)
        messages = [entry["message"] for entry in logs]
        assert any("Task created" in m for m in messages)
        assert any("Workflow started" in m for m in messages)
        assert any("Workflow completed successfully" in m for m in messages)

    def test_tool_invocation_persisted(
        self,
        agent_settings: AgentSettings,
        memory_manager: MemoryManager,
        sample_workflow: Workflow,
        sample_agent: Agent,
    ) -> None:
        discover_tools(agent_settings)
        engine = _engine(agent_settings, memory_manager)
        result = engine.run_workflow(
            "test-flow",
            {"output_path": str(agent_settings.tasks_dir / "inv.txt")},
        )
        assert len(result.tool_invocations) == 2
        inv_dir = agent_settings.tasks_dir / "invocations"
        assert inv_dir.exists()
        assert len(list(inv_dir.glob("inv_*.json"))) == 2


class TestRetries:
    def test_step_retries_until_success(
        self, agent_settings: AgentSettings, memory_manager: MemoryManager
    ) -> None:
        flaky = FlakyTool()
        register_tool(flaky)

        agent = Agent(
            agent_id="agt_flaky",
            name="Flaky Agent",
            description="Uses flaky tool",
            tools=["flaky"],
            permissions=[],
        )
        agent_path = agent_settings.agents_dir / "flaky.yaml"
        agent_path.write_text(yaml.dump(agent.model_dump(mode="json"), sort_keys=False), encoding="utf-8")

        workflow = Workflow(
            workflow_id="retry-flow",
            name="Retry Flow",
            description="Retry test",
            agent_id="agt_flaky",
            steps=[
                WorkflowStep(
                    step_id="flaky",
                    name="Flaky",
                    tool_name="flaky",
                    input={},
                    max_retries=2,
                ),
            ],
        )
        path = agent_settings.workflows_dir / "retry-flow.yaml"
        path.write_text(yaml.dump(workflow.model_dump(mode="json"), sort_keys=False), encoding="utf-8")

        engine = _engine(agent_settings, memory_manager)
        result = engine.run_workflow("retry-flow", {})
        assert result.status == TaskStatus.COMPLETED
        assert flaky.attempts == 2

        task = engine.store.get_task(result.task_id)
        assert task is not None
        assert task.retry_count == 1


class TestFailureRecovery:
    def test_unknown_tool_fails_workflow(
        self, agent_settings: AgentSettings, memory_manager: MemoryManager, sample_agent: Agent
    ) -> None:
        discover_tools(agent_settings)
        workflow = Workflow(
            workflow_id="bad-tool",
            name="Bad Tool",
            description="Missing tool",
            agent_id="agt_tester",
            steps=[
                WorkflowStep(step_id="bad", name="Bad", tool_name="nonexistent_tool", input={}),
            ],
        )
        path = agent_settings.workflows_dir / "bad-tool.yaml"
        path.write_text(yaml.dump(workflow.model_dump(mode="json"), sort_keys=False), encoding="utf-8")

        engine = _engine(agent_settings, memory_manager)
        result = engine.run_workflow("bad-tool", {})
        assert result.status == TaskStatus.FAILED
        assert "Unknown tool" in (result.error or "")

    def test_skip_on_failure(
        self, agent_settings: AgentSettings, memory_manager: MemoryManager, sample_agent: Agent
    ) -> None:
        discover_tools(agent_settings)
        workflow = Workflow(
            workflow_id="skip-flow",
            name="Skip Flow",
            description="Skip failing step",
            agent_id="agt_tester",
            steps=[
                WorkflowStep(
                    step_id="bad",
                    name="Bad",
                    tool_name="nonexistent_tool",
                    input={},
                    on_failure=StepFailureAction.SKIP,
                    max_retries=0,
                ),
                WorkflowStep(step_id="ts", name="Timestamp", tool_name="datetime_now", input={}),
            ],
        )
        path = agent_settings.workflows_dir / "skip-flow.yaml"
        path.write_text(yaml.dump(workflow.model_dump(mode="json"), sort_keys=False), encoding="utf-8")

        engine = _engine(agent_settings, memory_manager)
        result = engine.run_workflow("skip-flow", {})
        assert result.status == TaskStatus.COMPLETED
        assert result.steps_completed == ["ts"]

    def test_agent_tool_permission_denied(
        self, agent_settings: AgentSettings, memory_manager: MemoryManager
    ) -> None:
        discover_tools(agent_settings)
        restricted = Agent(
            agent_id="agt_restricted",
            name="Restricted",
            description="No tools",
            tools=["datetime_now"],
            permissions=[ToolPermission.SYSTEM_READ],
        )
        path = agent_settings.agents_dir / "restricted.yaml"
        path.write_text(yaml.dump(restricted.model_dump(mode="json"), sort_keys=False), encoding="utf-8")

        workflow = Workflow(
            workflow_id="denied",
            name="Denied",
            description="Permission test",
            agent_id="agt_restricted",
            steps=[
                WorkflowStep(step_id="write", name="Write", tool_name="filesystem_write", input={"path": "/tmp/x", "content": "x"}),
            ],
        )
        wf_path = agent_settings.workflows_dir / "denied.yaml"
        wf_path.write_text(yaml.dump(workflow.model_dump(mode="json"), sort_keys=False), encoding="utf-8")

        engine = _engine(agent_settings, memory_manager)
        result = engine.run_workflow("denied", {})
        assert result.status == TaskStatus.FAILED
        assert "not permitted" in (result.error or "").lower()


class TestWorkflowLoader:
    def test_list_workflows(self, agent_settings: AgentSettings, sample_workflow: Workflow) -> None:
        workflows = WorkflowLoader(agent_settings).list_workflows()
        assert any(w.workflow_id == "test-flow" for w in workflows)


class TestKnowledgeDecisionTools:
    @patch("ai_os.agent.tools.builtin.KnowledgeRetrieval")
    @patch("ai_os.agent.tools.builtin.DecisionPipeline")
    def test_knowledge_and_decision_wrappers(
        self,
        mock_pipeline_cls: MagicMock,
        mock_retrieval_cls: MagicMock,
        agent_settings: AgentSettings,
    ) -> None:
        from ai_os.knowledge.models import ContextBundle, RetrievalMetadata

        mock_retrieval_cls.return_value.retrieve.return_value = ContextBundle(
            query="test",
            chunks=[],
            citations=[],
            token_estimate=0,
            retrieval_metadata=RetrievalMetadata(search_mode="hybrid", latency_ms=1),
        )
        mock_result = MagicMock()
        mock_result.decision_id = "dec_1"
        mock_result.confidence = 0.8
        mock_result.recommendation = None
        mock_result.options = []
        mock_pipeline_cls.return_value.decide.return_value = mock_result

        discover_tools(agent_settings)
        ctx = ExecutionContext(task_id="task_1")

        kr = get_tool("knowledge_retrieve")
        assert kr is not None
        kr_result = kr.invoke({"query": "test"}, ctx)
        assert kr_result.success
        assert kr_result.output["chunk_count"] == 0

        dm = get_tool("decision_make")
        assert dm is not None
        dm_result = dm.invoke({"question": "What next?"}, ctx)
        assert dm_result.success
        assert dm_result.output["decision_id"] == "dec_1"
