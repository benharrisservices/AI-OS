"""Workflow definition loading."""

from __future__ import annotations

from pathlib import Path

import yaml

from ai_os.agent.config import AgentSettings
from ai_os.agent.models import Agent, Workflow, WorkflowStep


class WorkflowLoader:
    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings
        self.settings.ensure_dirs()

    def load_workflow(self, workflow_id: str) -> Workflow | None:
        path = self.settings.workflows_dir / f"{workflow_id}.yaml"
        if not path.exists():
            return None
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return Workflow.model_validate(data)

    def list_workflows(self) -> list[Workflow]:
        workflows: list[Workflow] = []
        for path in sorted(self.settings.workflows_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                workflows.append(Workflow.model_validate(data))
            except Exception:
                continue
        return workflows


class AgentLoader:
    def __init__(self, settings: AgentSettings) -> None:
        self.settings = settings
        self.settings.ensure_dirs()

    def list_agents(self) -> list[Agent]:
        agents: list[Agent] = []
        for path in sorted(self.settings.agents_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8"))
                agents.append(Agent.model_validate(data))
            except Exception:
                continue
        if not agents:
            agents = _default_agents()
        return agents

    def get_agent(self, agent_id: str) -> Agent | None:
        for agent in self.list_agents():
            if agent.agent_id == agent_id:
                return agent
        return None


def _default_agents() -> list[Agent]:
    from ai_os.agent.ids import new_agent_id
    from ai_os.agent.models import ToolPermission

    return [
        Agent(
            agent_id=new_agent_id("reviewer"),
            name="Reviewer",
            description="Retrieves knowledge and produces structured decisions.",
            tools=["knowledge_retrieve", "decision_make", "filesystem_write", "datetime_now"],
            permissions=[
                ToolPermission.KNOWLEDGE_READ,
                ToolPermission.DECISION_EXECUTE,
                ToolPermission.FILESYSTEM_WRITE,
                ToolPermission.SYSTEM_READ,
            ],
        ),
        Agent(
            agent_id=new_agent_id("executor"),
            name="Executor",
            description="Performs filesystem and system operations.",
            tools=["filesystem_read", "filesystem_write", "filesystem_list", "datetime_now"],
            permissions=[
                ToolPermission.FILESYSTEM_READ,
                ToolPermission.FILESYSTEM_WRITE,
                ToolPermission.SYSTEM_READ,
            ],
        ),
    ]
