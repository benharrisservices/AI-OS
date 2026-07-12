"""Workflows and agents API — wraps Agent Runtime."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai_os.api.serialize import to_json
from ai_os.agent.config import get_agent_settings
from ai_os.agent.engine import ExecutionEngine
from ai_os.agent.store import TaskStore
from ai_os.agent.workflows import AgentLoader, WorkflowLoader

router = APIRouter(tags=["workflows"])


class RunWorkflowBody(BaseModel):
    inputs: dict[str, Any] = Field(default_factory=dict)
    input_file: str | None = None


@router.get("/workflows")
def list_workflows() -> list:
    return [to_json(w) for w in WorkflowLoader(get_agent_settings()).list_workflows()]


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str) -> dict:
    workflow = WorkflowLoader(get_agent_settings()).load_workflow(workflow_id)
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    return to_json(workflow)


@router.post("/workflows/{workflow_id}/run")
def run_workflow(workflow_id: str, body: RunWorkflowBody) -> dict:
    inputs = dict(body.inputs)
    if body.input_file:
        inputs["input_file"] = body.input_file
    result = ExecutionEngine().run_workflow(workflow_id, inputs)
    return to_json(result)


@router.get("/agents")
def list_agents() -> list:
    return [to_json(a) for a in AgentLoader(get_agent_settings()).list_agents()]


@router.get("/tasks")
def list_tasks() -> list:
    return [to_json(t) for t in TaskStore(get_agent_settings()).list_tasks()]


@router.get("/tasks/{task_id}")
def get_task(task_id: str) -> dict:
    task = TaskStore(get_agent_settings()).get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    logs = TaskStore(get_agent_settings()).get_logs(task_id)
    return {"task": to_json(task), "logs": logs}
