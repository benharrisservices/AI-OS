"""Built-in skills — compose Knowledge, Decision, and Memory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_os.capabilities.base import BaseSkill
from ai_os.capabilities.helpers import make_decision, retrieve_knowledge, search_memory
from ai_os.capabilities.models import SkillMetadata
from ai_os.capabilities.registry import register_skill
from ai_os.decision.models import ReasoningStrategyName


def _research_skill(
    skill_id: str,
    name: str,
    description: str,
    tags: list[str],
    *,
    top_k: int = 12,
) -> BaseSkill:
    class ResearchSkill(BaseSkill):
        metadata = SkillMetadata(
            skill_id=skill_id,
            name=name,
            description=description,
            required_tools=["knowledge_retrieve"],
            required_models=["any"],
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}, "top_k": {"type": "integer"}},
                "required": ["query"],
            },
            output_schema={
                "type": "object",
                "properties": {"context": {"type": "string"}, "chunk_count": {"type": "integer"}},
            },
            tags=tags,
        )

        def execute(self, input_data: dict[str, Any]):
            query = input_data.get("query", "")
            if not query:
                return self._failure("query is required")
            data = retrieve_knowledge(query, top_k=input_data.get("top_k", top_k))
            conf = self.confidence_from_evidence(data["chunk_count"], len(data["citations"]))
            return self._success(
                result=data,
                summary=f"Retrieved {data['chunk_count']} chunks for: {query[:80]}",
                confidence=conf,
            )

    return ResearchSkill()


class DocumentSummarisationSkill(BaseSkill):
    metadata = SkillMetadata(
        skill_id="document-summarisation",
        name="Document Summarisation",
        description="Summarise a document or knowledge query.",
        required_tools=["knowledge_retrieve", "filesystem_read"],
        required_models=["reasoning"],
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "path": {"type": "string"},
            },
        },
        tags=["documents", "summarisation"],
    )

    def execute(self, input_data: dict[str, Any]):
        context_parts: list[str] = []
        if path := input_data.get("path"):
            p = Path(str(path)).expanduser()
            if p.exists():
                context_parts.append(p.read_text(encoding="utf-8")[:8000])
        if query := input_data.get("query"):
            data = retrieve_knowledge(query, top_k=8)
            context_parts.append(data["context"])
        if not context_parts:
            return self._failure("Provide query or path")
        combined = "\n\n".join(context_parts)
        decision = make_decision(
            f"Summarise the following:\n{combined[:6000]}",
            strategy=ReasoningStrategyName.OPERATIONAL,
        )
        return self._success(
            result={"summary": decision.get("summary"), "decision_id": decision.get("decision_id")},
            summary=decision.get("summary") or "Summary generated",
            confidence=decision.get("confidence", 0.6),
        )


class SpecificationGenerationSkill(BaseSkill):
    metadata = SkillMetadata(
        skill_id="specification-generation",
        name="Specification Generation",
        description="Generate a structured specification from requirements.",
        required_tools=["knowledge_retrieve", "decision_make"],
        required_models=["reasoning"],
        input_schema={
            "type": "object",
            "properties": {"requirements": {"type": "string"}},
            "required": ["requirements"],
        },
        tags=["specs", "planning"],
    )

    def execute(self, input_data: dict[str, Any]):
        req = input_data.get("requirements", "")
        if not req:
            return self._failure("requirements is required")
        ctx = retrieve_knowledge(req, top_k=6)
        decision = make_decision(
            f"Generate a structured specification for: {req}",
            strategy=ReasoningStrategyName.STRATEGIC,
            context=ctx["context"],
        )
        return self._success(
            result={"specification": decision.get("summary"), **decision},
            summary=decision.get("summary") or "Specification generated",
            confidence=decision.get("confidence", 0.65),
        )


class EmailDraftingSkill(BaseSkill):
    metadata = SkillMetadata(
        skill_id="email-drafting",
        name="Email Drafting",
        description="Draft a professional email.",
        required_tools=["decision_make"],
        required_models=["reasoning"],
        input_schema={
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "tone": {"type": "string", "default": "professional"},
                "recipient": {"type": "string"},
            },
            "required": ["topic"],
        },
        tags=["communication", "email"],
    )

    def execute(self, input_data: dict[str, Any]):
        topic = input_data.get("topic", "")
        tone = input_data.get("tone", "professional")
        recipient = input_data.get("recipient", "")
        decision = make_decision(
            f"Draft a {tone} email to {recipient} about: {topic}",
            strategy=ReasoningStrategyName.OPERATIONAL,
        )
        return self._success(
            result={"draft": decision.get("summary"), **decision},
            summary="Email draft generated",
            confidence=decision.get("confidence", 0.7),
        )


class MeetingPreparationSkill(BaseSkill):
    metadata = SkillMetadata(
        skill_id="meeting-preparation",
        name="Meeting Preparation",
        description="Prepare agenda, talking points, and background.",
        required_tools=["knowledge_retrieve", "decision_make", "memory"],
        required_models=["reasoning"],
        input_schema={
            "type": "object",
            "properties": {"meeting_topic": {"type": "string"}, "attendees": {"type": "string"}},
            "required": ["meeting_topic"],
        },
        tags=["meetings", "planning"],
    )

    def execute(self, input_data: dict[str, Any]):
        topic = input_data.get("meeting_topic", "")
        memories = search_memory(topic, limit=3)
        ctx = retrieve_knowledge(topic, top_k=8)
        decision = make_decision(
            f"Prepare meeting brief for '{topic}' with attendees: {input_data.get('attendees', 'TBD')}",
            strategy=ReasoningStrategyName.STRATEGIC,
            context=ctx["context"],
        )
        return self._success(
            result={"brief": decision.get("summary"), "memories": memories, **decision},
            summary=decision.get("summary") or "Meeting brief prepared",
            confidence=decision.get("confidence", 0.7),
        )


class TaskPlanningSkill(BaseSkill):
    metadata = SkillMetadata(
        skill_id="task-planning",
        name="Task Planning",
        description="Break down goals into actionable tasks.",
        required_tools=["decision_make", "knowledge_retrieve"],
        required_models=["reasoning"],
        input_schema={
            "type": "object",
            "properties": {"goal": {"type": "string"}},
            "required": ["goal"],
        },
        tags=["planning", "tasks"],
    )

    def execute(self, input_data: dict[str, Any]):
        goal = input_data.get("goal", "")
        ctx = retrieve_knowledge(goal, top_k=5)
        decision = make_decision(
            f"Create an actionable task plan for: {goal}",
            strategy=ReasoningStrategyName.OPERATIONAL,
            context=ctx["context"],
        )
        return self._success(
            result={"plan": decision.get("summary"), **decision},
            summary=decision.get("summary") or "Task plan created",
            confidence=decision.get("confidence", 0.68),
        )


class GitHubRepositoryAnalysisSkill(BaseSkill):
    metadata = SkillMetadata(
        skill_id="github-repository-analysis",
        name="GitHub Repository Analysis",
        description="Analyse a GitHub repository structure and health.",
        required_tools=["http_request", "knowledge_retrieve"],
        required_models=["coding"],
        input_schema={
            "type": "object",
            "properties": {"repo": {"type": "string", "description": "owner/repo"}},
            "required": ["repo"],
        },
        tags=["github", "code"],
    )

    def execute(self, input_data: dict[str, Any]):
        repo = input_data.get("repo", "")
        if not repo:
            return self._failure("repo is required")
        ctx = retrieve_knowledge(f"github repository {repo}", top_k=6)
        decision = make_decision(
            f"Analyse GitHub repository {repo}: structure, health, and recommendations",
            strategy=ReasoningStrategyName.ANALYTICAL,
            context=ctx["context"],
        )
        return self._success(
            result={"analysis": decision.get("summary"), "repo": repo, **decision},
            summary=f"Analysis for {repo}",
            confidence=decision.get("confidence", 0.6),
        )


class CodeReviewSkill(BaseSkill):
    metadata = SkillMetadata(
        skill_id="code-review",
        name="Code Review",
        description="Review code changes or files.",
        required_tools=["filesystem_read", "decision_make"],
        required_models=["coding"],
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}, "focus": {"type": "string"}},
            "required": ["path"],
        },
        tags=["code", "review"],
    )

    def execute(self, input_data: dict[str, Any]):
        path = Path(str(input_data.get("path", ""))).expanduser()
        if not path.exists():
            return self._failure(f"File not found: {path}")
        code = path.read_text(encoding="utf-8")[:10000]
        focus = input_data.get("focus", "bugs, security, and style")
        decision = make_decision(
            f"Review this code with focus on {focus}:\n{code}",
            strategy=ReasoningStrategyName.ANALYTICAL,
        )
        return self._success(
            result={"review": decision.get("summary"), "path": str(path), **decision},
            summary=decision.get("summary") or "Code review complete",
            confidence=decision.get("confidence", 0.65),
        )


class DecisionBriefGenerationSkill(BaseSkill):
    metadata = SkillMetadata(
        skill_id="decision-brief-generation",
        name="Decision Brief Generation",
        description="Generate a structured decision brief with evidence.",
        required_tools=["knowledge_retrieve", "decision_make"],
        required_models=["reasoning"],
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "strategy": {"type": "string", "default": "analytical"},
            },
            "required": ["question"],
        },
        tags=["decision", "brief"],
    )

    def execute(self, input_data: dict[str, Any]):
        question = input_data.get("question", "")
        strategy_name = input_data.get("strategy", "analytical")
        try:
            strategy = ReasoningStrategyName(strategy_name)
        except ValueError:
            return self._failure(f"Unknown strategy: {strategy_name}")
        ctx = retrieve_knowledge(question, top_k=10)
        decision = make_decision(question, strategy=strategy, context=ctx["context"])
        return self._success(
            result={"brief": decision.get("summary"), "evidence_chunks": ctx["chunk_count"], **decision},
            summary=decision.get("summary") or "Decision brief generated",
            confidence=decision.get("confidence", 0.75),
        )


class FinancialComparisonSkill(BaseSkill):
    metadata = SkillMetadata(
        skill_id="financial-comparison",
        name="Financial Comparison",
        description="Compare financial options with structured analysis.",
        required_tools=["knowledge_retrieve", "decision_make"],
        required_models=["reasoning"],
        input_schema={
            "type": "object",
            "properties": {"options": {"type": "string"}, "criteria": {"type": "string"}},
            "required": ["options"],
        },
        tags=["finance", "comparison"],
    )

    def execute(self, input_data: dict[str, Any]):
        options = input_data.get("options", "")
        criteria = input_data.get("criteria", "cost, risk, and value")
        decision = make_decision(
            f"Compare these options ({options}) using criteria: {criteria}",
            strategy=ReasoningStrategyName.WEIGHTED_SCORING,
        )
        return self._success(
            result={"comparison": decision.get("summary"), **decision},
            summary=decision.get("summary") or "Comparison complete",
            confidence=decision.get("confidence", 0.7),
        )


def register_builtin_skills() -> None:
    skills: list[BaseSkill] = [
        _research_skill("deep-research", "Deep Research", "In-depth research across knowledge base", ["research"]),
        _research_skill("company-research", "Company Research", "Research a company or organisation", ["research", "company"]),
        _research_skill("product-research", "Product Research", "Research a product or service", ["research", "product"]),
        _research_skill("web-research", "Web Research", "Research a topic using indexed knowledge", ["research", "web"]),
        _research_skill("travel-planning", "Travel Planning", "Research travel destinations and logistics", ["travel"]),
        _research_skill("flight-research", "Flight Research", "Research flight options and routes", ["travel", "flights"]),
        _research_skill("hotel-research", "Hotel Research", "Research accommodation options", ["travel", "hotels"]),
        DocumentSummarisationSkill(),
        SpecificationGenerationSkill(),
        EmailDraftingSkill(),
        MeetingPreparationSkill(),
        TaskPlanningSkill(),
        GitHubRepositoryAnalysisSkill(),
        CodeReviewSkill(),
        DecisionBriefGenerationSkill(),
        FinancialComparisonSkill(),
    ]
    for skill in skills:
        register_skill(skill)
