"""Decision Engine identifier generation."""

from ulid import ULID


def new_decision_id() -> str:
    return f"dec_{ULID()}"


def new_option_id(index: int) -> str:
    return f"opt_{index:02d}"


def new_evidence_id(index: int) -> str:
    return f"ev_{index:02d}"


def new_assumption_id(index: int) -> str:
    return f"asm_{index:02d}"


def new_constraint_id(index: int) -> str:
    return f"cst_{index:02d}"


def new_risk_id(index: int) -> str:
    return f"rsk_{index:02d}"


def new_tradeoff_id(index: int) -> str:
    return f"trd_{index:02d}"


def new_recommendation_id() -> str:
    return f"rec_{ULID()}"
