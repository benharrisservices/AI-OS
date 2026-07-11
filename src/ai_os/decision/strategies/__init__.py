"""Reasoning strategy protocol and registry."""

from __future__ import annotations

from typing import Protocol

from ai_os.decision.models import (
    Assumption,
    Constraint,
    DecisionOption,
    DecisionRequest,
    Evidence,
    ReasoningStrategyName,
    Risk,
    Tradeoff,
)


class ReasoningStrategy(Protocol):
    """Modular reasoning mode — shapes how the pipeline evaluates options."""

    name: ReasoningStrategyName
    tradeoff_dimensions: list[str]
    default_option_count: int

    def generate_options(
        self,
        request: DecisionRequest,
        evidence: list[Evidence],
        constraints: list[Constraint],
    ) -> list[DecisionOption]: ...

    def identify_assumptions(
        self,
        request: DecisionRequest,
        evidence: list[Evidence],
    ) -> list[Assumption]: ...

    def compare_tradeoffs(
        self,
        options: list[DecisionOption],
        evidence: list[Evidence],
    ) -> list[Tradeoff]: ...

    def evaluate_risks(
        self,
        options: list[DecisionOption],
        evidence: list[Evidence],
    ) -> list[Risk]: ...

    def score_options(
        self,
        options: list[DecisionOption],
        tradeoffs: list[Tradeoff],
        risks: list[Risk],
        evidence: list[Evidence],
    ) -> list[DecisionOption]: ...


_STRATEGIES: dict[ReasoningStrategyName, ReasoningStrategy] = {}


def register_strategy(strategy: ReasoningStrategy) -> None:
    _STRATEGIES[strategy.name] = strategy


def get_strategy(name: ReasoningStrategyName) -> ReasoningStrategy:
    if name not in _STRATEGIES:
        raise ValueError(f"Unknown reasoning strategy: {name}")
    return _STRATEGIES[name]


def list_strategies() -> list[ReasoningStrategyName]:
    return list(_STRATEGIES.keys())


from ai_os.decision.strategies.builtin import register_builtin_strategies as _register_builtin_strategies

_register_builtin_strategies()
