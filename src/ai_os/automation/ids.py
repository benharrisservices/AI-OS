"""Automation identifier generation."""

from ulid import ULID


def new_automation_id(name: str = "") -> str:
    if name:
        slug = name.lower().replace(" ", "-")[:32]
        return f"auto_{slug}"
    return f"auto_{ULID()}"


def new_execution_id() -> str:
    return f"aexec_{ULID()}"
