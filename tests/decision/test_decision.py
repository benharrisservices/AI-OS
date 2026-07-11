"""Decision Engine tests."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_os.decision.config import DecisionSettings
from ai_os.decision.models import (
    DecisionRequest,
    DecisionStatus,
    ReasoningStrategyName,
)
from ai_os.decision.pipeline import DecisionPipeline
from ai_os.decision.store import DecisionStore
from ai_os.decision.strategies import get_strategy, list_strategies
from ai_os.knowledge.models import (
    Citation,
    ContextBundle,
    RetrievedChunk,
    RetrievalMetadata,
)


@pytest.fixture
def decision_settings(tmp_path: Path) -> DecisionSettings:
    return DecisionSettings(
        DECISION_ENGINE_DECISIONS_DIR=tmp_path / "decisions",
        DECISION_ENGINE_USE_LLM=False,
    )


def _sample_bundle() -> ContextBundle:
    return ContextBundle(
        query="Barbados expansion",
        chunks=[
            RetrievedChunk(
                chunk_id="chk_1",
                doc_id="doc_1",
                text="Barbados solar initiatives support infrastructure development.",
                score=0.85,
                heading_path="overview",
                source_uri="file:///docs/barbados.md",
            )
        ],
        citations=[
            Citation(
                cite_key="[1]",
                chunk_id="chk_1",
                title="Barbados Solar Project",
                source_uri="file:///docs/barbados.md",
                excerpt="Barbados solar initiatives support infrastructure development.",
            )
        ],
        token_estimate=20,
        retrieval_metadata=RetrievalMetadata(search_mode="hybrid", latency_ms=10),
    )


class TestContracts:
    def test_decision_request_defaults(self) -> None:
        req = DecisionRequest(question="Should we expand?")
        assert req.strategy == ReasoningStrategyName.ANALYTICAL
        assert req.require_knowledge is True

    def test_all_strategies_registered(self) -> None:
        registered = list_strategies()
        assert ReasoningStrategyName.ANALYTICAL in registered
        assert ReasoningStrategyName.WEIGHTED_SCORING in registered
        assert len(registered) == 6


class TestPipeline:
    @patch("ai_os.decision.pipeline.KnowledgeRetrieval")
    def test_pipeline_completes_all_stages(self, mock_retrieval_cls, decision_settings) -> None:
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = _sample_bundle()
        mock_retrieval_cls.return_value = mock_retrieval

        pipeline = DecisionPipeline(decision_settings)
        request = DecisionRequest(question="Should we expand into Barbados?")
        result = pipeline.decide(request)

        assert result.status == DecisionStatus.COMPLETED
        assert len(result.reasoning_trace) == 10
        assert result.reasoning_trace[0].stage == "understand_request"
        assert result.reasoning_trace[1].stage == "retrieve_knowledge"
        assert result.evidence
        assert result.options
        assert result.recommendation is not None
        assert 0.0 <= result.confidence <= 1.0

    @patch("ai_os.decision.pipeline.KnowledgeRetrieval")
    def test_pipeline_consumes_context_bundle_not_raw_prompt(
        self, mock_retrieval_cls, decision_settings
    ) -> None:
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = _sample_bundle()
        mock_retrieval_cls.return_value = mock_retrieval

        pipeline = DecisionPipeline(decision_settings)
        pipeline.decide(DecisionRequest(question="Test question"))

        mock_retrieval.retrieve.assert_called_once()
        call_args = mock_retrieval.retrieve.call_args[0][0]
        assert call_args.query == "Test question"

    @patch("ai_os.decision.pipeline.KnowledgeRetrieval")
    def test_evidence_maps_from_bundle(self, mock_retrieval_cls, decision_settings) -> None:
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = _sample_bundle()
        mock_retrieval_cls.return_value = mock_retrieval

        result = DecisionPipeline(decision_settings).decide(
            DecisionRequest(question="Barbados infrastructure")
        )
        assert result.evidence[0].cite_key == "[1]"
        assert result.evidence[0].chunk_id == "chk_1"
        assert "Barbados" in result.evidence[0].content

    @patch("ai_os.decision.pipeline.KnowledgeRetrieval")
    def test_evidence_increases_confidence(self, mock_retrieval_cls, decision_settings) -> None:
        mock_retrieval = MagicMock()
        mock_retrieval.retrieve.return_value = _sample_bundle()
        mock_retrieval_cls.return_value = mock_retrieval

        with_evidence = DecisionPipeline(decision_settings).decide(
            DecisionRequest(question="Should we proceed?")
        )

        mock_retrieval.retrieve.return_value = ContextBundle(
            query="test",
            retrieval_metadata=RetrievalMetadata(search_mode="hybrid"),
        )
        without_evidence = DecisionPipeline(decision_settings).decide(
            DecisionRequest(question="Should we proceed?")
        )
        assert with_evidence.confidence > without_evidence.confidence


class TestStrategies:
    @patch("ai_os.decision.pipeline.KnowledgeRetrieval")
    def test_analytical_strategy(self, mock_cls, decision_settings) -> None:
        mock_cls.return_value.retrieve.return_value = _sample_bundle()
        result = DecisionPipeline(decision_settings).decide(
            DecisionRequest(
                question="Which platform?",
                strategy=ReasoningStrategyName.ANALYTICAL,
            )
        )
        assert result.strategy == ReasoningStrategyName.ANALYTICAL

    @patch("ai_os.decision.pipeline.KnowledgeRetrieval")
    def test_weighted_scoring_strategy(self, mock_cls, decision_settings) -> None:
        mock_cls.return_value.retrieve.return_value = _sample_bundle()
        result = DecisionPipeline(decision_settings).decide(
            DecisionRequest(
                question="Which hosting platform?",
                strategy=ReasoningStrategyName.WEIGHTED_SCORING,
                option_hints=["AWS", "Self-hosted"],
            )
        )
        assert result.strategy == ReasoningStrategyName.WEIGHTED_SCORING
        assert all(o.score is not None for o in result.options)

    def test_strategy_generates_options_from_hints(self) -> None:
        strategy = get_strategy(ReasoningStrategyName.OPERATIONAL)
        from ai_os.decision.models import Evidence

        options = strategy.generate_options(
            DecisionRequest(
                question="Choose a database",
                option_hints=["PostgreSQL", "SQLite"],
            ),
            evidence=[],
            constraints=[],
        )
        assert len(options) == 2
        assert "PostgreSQL" in options[0].title


class TestLogging:
    @patch("ai_os.decision.pipeline.KnowledgeRetrieval")
    def test_decision_persisted(self, mock_cls, decision_settings) -> None:
        mock_cls.return_value.retrieve.return_value = _sample_bundle()
        pipeline = DecisionPipeline(decision_settings)
        result = pipeline.decide(DecisionRequest(question="Test persistence"))

        stored = DecisionStore(decision_settings).get(result.decision_id)
        assert stored is not None
        assert stored.decision_id == result.decision_id
        assert stored.recommendation is not None

    @patch("ai_os.decision.pipeline.KnowledgeRetrieval")
    def test_list_decisions(self, mock_cls, decision_settings) -> None:
        mock_cls.return_value.retrieve.return_value = _sample_bundle()
        pipeline = DecisionPipeline(decision_settings)
        pipeline.decide(DecisionRequest(question="First"))
        pipeline.decide(DecisionRequest(question="Second"))

        records = DecisionStore(decision_settings).list_all()
        assert len(records) == 2

    @patch("ai_os.decision.pipeline.KnowledgeRetrieval")
    def test_outcome_field_reserved(self, mock_cls, decision_settings) -> None:
        mock_cls.return_value.retrieve.return_value = _sample_bundle()
        result = DecisionPipeline(decision_settings).decide(
            DecisionRequest(question="Future outcome test")
        )
        assert result.outcome is None
