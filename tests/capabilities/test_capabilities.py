"""Capability Layer tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_os.capabilities.builtin import register_builtin_skills
from ai_os.capabilities.models import SkillOutput
from ai_os.capabilities.registry import discover_skills, get_skill, list_skills
from ai_os.capabilities.tools import SkillTool, register_skill_tools


class TestSkillRegistry:
    def test_discover_all_skills(self) -> None:
        ids = discover_skills()
        assert len(ids) == 16
        assert "deep-research" in ids
        assert "decision-brief-generation" in ids

    def test_skill_metadata(self) -> None:
        discover_skills()
        skill = get_skill("email-drafting")
        assert skill is not None
        assert skill.metadata.required_tools
        assert "communication" in skill.metadata.tags

    def test_register_as_agent_tools(self) -> None:
        from ai_os.agent.tools import list_tools

        register_builtin_skills()
        names = register_skill_tools()
        assert any(n.startswith("skill_") for n in names)
        tools = list_tools()
        assert any(t.name == "skill_deep_research" for t in tools)


class TestSkillExecution:
    @patch("ai_os.capabilities.helpers.retrieve_knowledge")
    def test_deep_research(self, mock_retrieve: MagicMock) -> None:
        mock_retrieve.return_value = {
            "query": "test",
            "chunk_count": 3,
            "citations": [{"cite_key": "[1]"}],
            "context": "context",
            "token_estimate": 100,
        }
        discover_skills()
        skill = get_skill("deep-research")
        assert skill is not None
        output = skill.execute({"query": "AI trends"})
        assert output.success
        assert output.confidence > 0.3

    @patch("ai_os.capabilities.helpers.make_decision")
    def test_email_drafting(self, mock_decide: MagicMock) -> None:
        mock_decide.return_value = {
            "decision_id": "dec_1",
            "confidence": 0.8,
            "summary": "Dear team, ...",
            "recommendation": None,
            "options_count": 2,
        }
        discover_skills()
        skill = get_skill("email-drafting")
        output = skill.execute({"topic": "Project update", "recipient": "team"})
        assert output.success
        assert "Dear" in output.summary or output.result.get("draft")

    def test_missing_input_fails(self) -> None:
        discover_skills()
        skill = get_skill("deep-research")
        assert skill is not None
        output = skill.execute({})
        assert not output.success


class TestSkillTool:
    @patch("ai_os.capabilities.helpers.retrieve_knowledge")
    def test_skill_tool_invoke(self, mock_retrieve: MagicMock) -> None:
        from ai_os.agent.models import ExecutionContext

        mock_retrieve.return_value = {
            "query": "x", "chunk_count": 1, "citations": [], "context": "", "token_estimate": 10,
        }
        discover_skills()
        skill = get_skill("web-research")
        tool = SkillTool(skill)
        result = tool.invoke({"query": "test"}, ExecutionContext(task_id="t1"))
        assert result.success
