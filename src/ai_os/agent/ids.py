"""Agent Runtime identifier generation."""

from ulid import ULID


def new_task_id() -> str:
    return f"task_{ULID()}"


def new_invocation_id() -> str:
    return f"inv_{ULID()}"


def new_agent_id(name: str) -> str:
    slug = name.lower().replace(" ", "-")[:32]
    return f"agt_{slug}"
