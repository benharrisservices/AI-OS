"""Agent execution engine — orchestrates tools without LLM logic."""

from __future__ import annotations

import time

from ai_os.agent.config import AgentSettings
from ai_os.agent.ids import new_invocation_id, new_task_id
from ai_os.agent.models import (
    AgentTask,
    ExecutionContext,
    ExecutionResult,
    StepFailureAction,
    TaskStatus,
    ToolInvocation,
    Workflow,
    utc_now,
)
from ai_os.agent.resolve import build_bindings, resolve_value
from ai_os.agent.store import TaskStore
from ai_os.agent.tools import discover_tools, get_tool
from ai_os.agent.workflows import AgentLoader, WorkflowLoader
from ai_os.memory.manager import MemoryManager
from ai_os.memory.models import EpisodicEventType, PromotionPolicy


class ExecutionEngine:
    """Creates tasks, runs sequential workflows, handles retries and failures.

    The execution engine never performs retrieval or reasoning itself — it
    delegates to registered tools that wrap the Knowledge and Decision engines.
    """

    def __init__(
        self,
        settings: AgentSettings | None = None,
        memory_manager: MemoryManager | None = None,
    ) -> None:
        self.settings = settings or AgentSettings()
        self.settings.ensure_dirs()
        discover_tools(self.settings)
        self.store = TaskStore(self.settings)
        self.workflow_loader = WorkflowLoader(self.settings)
        self.agent_loader = AgentLoader(self.settings)
        self.memory = memory_manager or MemoryManager()

    def create_task(
        self,
        *,
        workflow_id: str | None = None,
        agent_id: str | None = None,
        input_data: dict | None = None,
        max_retries: int | None = None,
    ) -> AgentTask:
        task = AgentTask(
            task_id=new_task_id(),
            agent_id=agent_id,
            workflow_id=workflow_id,
            input=input_data or {},
            max_retries=max_retries or self.settings.default_max_retries,
            context=ExecutionContext(
                task_id="",
                agent_id=agent_id,
                workflow_id=workflow_id,
            ),
        )
        task.context.task_id = task.task_id
        bundle = self.memory.retrieve_for_task(
            task_id=task.task_id,
            agent_id=agent_id,
            workflow_id=workflow_id,
        )
        task.context.relevant_memories = bundle.to_context_dict()
        self.store.save_task(task)
        self.store.append_log(task.task_id, f"Task created: {task.task_id}")
        return task

    def execute_task(self, task_id: str) -> ExecutionResult:
        task = self.store.get_task(task_id)
        if task is None:
            raise ValueError(f"Unknown task: {task_id}")

        if task.workflow_id:
            workflow = self.workflow_loader.load_workflow(task.workflow_id)
            if workflow is None:
                raise ValueError(f"Unknown workflow: {task.workflow_id}")
            return self._execute_workflow(task, workflow)

        return ExecutionResult(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error="Task has no workflow assigned",
        )

    def run_workflow(self, workflow_id: str, input_data: dict | None = None) -> ExecutionResult:
        workflow = self.workflow_loader.load_workflow(workflow_id)
        if workflow is None:
            raise ValueError(f"Unknown workflow: {workflow_id}")

        task = self.create_task(
            workflow_id=workflow_id,
            agent_id=workflow.agent_id,
            input_data=input_data or {},
        )
        return self.execute_task(task.task_id)

    def _execute_workflow(self, task: AgentTask, workflow: Workflow) -> ExecutionResult:
        start = time.perf_counter()
        invocations: list[ToolInvocation] = []
        completed_steps: list[str] = []

        task.status = TaskStatus.RUNNING
        task.started_at = utc_now()
        self.store.save_task(task)
        self.store.append_log(task.task_id, f"Workflow started: {workflow.workflow_id}")

        self.memory.sync_working(
            task_id=task.task_id,
            scope=f"workflow:{workflow.workflow_id}",
            content={"input": task.input, "status": "running"},
            metadata={
                "agent_id": task.agent_id,
                "workflow_id": workflow.workflow_id,
            },
        )

        agent = self.agent_loader.get_agent(task.agent_id) if task.agent_id else None
        allowed_tools = set(agent.tools) if agent else None

        for step in workflow.steps:
            success = self._run_step_with_retry(
                task, workflow, step, invocations, completed_steps, allowed_tools
            )
            if not success:
                task.status = TaskStatus.FAILED
                task.completed_at = utc_now()
                self.store.save_task(task)
                self._record_workflow_memory(task, workflow, success=False)
                duration_ms = int((time.perf_counter() - start) * 1000)
                return ExecutionResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    outputs=task.output,
                    steps_completed=completed_steps,
                    tool_invocations=invocations,
                    duration_ms=duration_ms,
                    error=task.error,
                )

        task.status = TaskStatus.COMPLETED
        task.output = dict(task.context.variables)
        task.completed_at = utc_now()
        self.store.save_task(task)
        self.store.append_log(task.task_id, "Workflow completed successfully")
        self._record_workflow_memory(task, workflow, success=True)

        duration_ms = int((time.perf_counter() - start) * 1000)
        return ExecutionResult(
            task_id=task.task_id,
            status=TaskStatus.COMPLETED,
            outputs=task.output,
            steps_completed=completed_steps,
            tool_invocations=invocations,
            duration_ms=duration_ms,
        )

    def _run_step_with_retry(
        self,
        task: AgentTask,
        workflow: Workflow,
        step,
        invocations: list[ToolInvocation],
        completed_steps: list[str],
        allowed_tools: set[str] | None,
    ) -> bool:
        max_retries = step.max_retries
        for attempt in range(max_retries + 1):
            if attempt > 0:
                task.status = TaskStatus.RETRYING
                task.retry_count = attempt
                self.store.save_task(task)
                self.store.append_log(
                    task.task_id,
                    f"Retrying step {step.step_id} (attempt {attempt + 1})",
                    level="warning",
                )

            invocation, result = self._invoke_step(task, step, allowed_tools)
            invocations.append(invocation)
            self.store.save_invocation(invocation)

            if result.success:
                task.context.step_outputs[step.step_id] = result.output
                task.context.variables.update(result.output)
                completed_steps.append(step.step_id)
                self.store.append_log(task.task_id, f"Step completed: {step.step_id}")
                return True

            invocation.error = result.error
            task.error = result.error
            self.store.append_log(
                task.task_id,
                f"Step failed: {step.step_id} — {result.error}",
                level="error",
            )

            if step.on_failure == StepFailureAction.SKIP:
                self.store.append_log(task.task_id, f"Skipping step: {step.step_id}")
                return True
            if step.on_failure == StepFailureAction.FAIL:
                return False
            if attempt >= max_retries:
                return False

        return False

    def _invoke_step(self, task: AgentTask, step, allowed_tools: set[str] | None):
        tool = get_tool(step.tool_name)
        if tool is None:
            invocation = ToolInvocation(
                invocation_id=new_invocation_id(),
                task_id=task.task_id,
                step_id=step.step_id,
                tool_name=step.tool_name,
                status=TaskStatus.FAILED,
                error=f"Unknown tool: {step.tool_name}",
            )
            from ai_os.agent.models import ToolResult

            return invocation, ToolResult(
                invocation_id=invocation.invocation_id,
                tool_name=step.tool_name,
                success=False,
                error=invocation.error,
            )

        if allowed_tools is not None and step.tool_name not in allowed_tools:
            invocation = ToolInvocation(
                invocation_id=new_invocation_id(),
                task_id=task.task_id,
                step_id=step.step_id,
                tool_name=step.tool_name,
                status=TaskStatus.FAILED,
                error=f"Agent not permitted to use tool: {step.tool_name}",
            )
            from ai_os.agent.models import ToolResult

            return invocation, ToolResult(
                invocation_id=invocation.invocation_id,
                tool_name=step.tool_name,
                success=False,
                error=invocation.error,
            )

        if not tool.enabled:
            invocation = ToolInvocation(
                invocation_id=new_invocation_id(),
                task_id=task.task_id,
                step_id=step.step_id,
                tool_name=step.tool_name,
                status=TaskStatus.FAILED,
            )
            from ai_os.agent.models import ToolResult

            return invocation, ToolResult(
                invocation_id=invocation.invocation_id,
                tool_name=step.tool_name,
                success=False,
                error=f"Tool disabled: {step.tool_name}",
            )

        bindings = build_bindings(
            task_input=task.input,
            step_outputs=task.context.step_outputs,
            variables=task.context.variables,
            memory=task.context.relevant_memories,
        )
        resolved_input = resolve_value(step.input, bindings)

        invocation = ToolInvocation(
            invocation_id=new_invocation_id(),
            task_id=task.task_id,
            step_id=step.step_id,
            tool_name=step.tool_name,
            input=resolved_input,
            status=TaskStatus.RUNNING,
        )

        result = tool.invoke(resolved_input, task.context)
        invocation.status = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
        invocation.completed_at = utc_now()
        invocation.error = result.error
        return invocation, result

    def _record_workflow_memory(self, task: AgentTask, workflow: Workflow, *, success: bool) -> None:
        """Record workflow execution as episodic memory and promote working context."""
        event_type = EpisodicEventType.SUCCESS if success else EpisodicEventType.FAILURE
        title = f"{'Completed' if success else 'Failed'}: {workflow.name}"
        summary = (
            f"Workflow {workflow.workflow_id} {'completed' if success else 'failed'} "
            f"for task {task.task_id}"
        )
        self.memory.create_episodic(
            event_type=event_type,
            title=title,
            summary=summary,
            content={
                "workflow_id": workflow.workflow_id,
                "steps_completed": list(task.context.step_outputs.keys()),
                "output": task.output,
                "error": task.error,
            },
            source_ref=task.task_id,
            tags=[workflow.workflow_id],
            metadata={"agent_id": task.agent_id, "workflow_id": workflow.workflow_id},
        )

        self.memory.promote_working_for_task(
            task.task_id,
            policy=PromotionPolicy.WORKFLOW_COMPLETION,
            title=title,
            summary=summary,
        )
