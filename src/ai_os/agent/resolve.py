"""Resolve template references in workflow step inputs."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

_TEMPLATE_RE = re.compile(r"\{\{([^}]+)\}\}")


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", str(text).lower()).strip("-")
    return slug[:60] or "item"


def init_workflow_variables(task_input: dict[str, Any]) -> dict[str, Any]:
    """Runtime variables available as {{vars.date}}, {{vars.iso}}, etc."""
    now = datetime.now(timezone.utc)
    variables: dict[str, Any] = {
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "timestamp": now.timestamp(),
    }
    for key, value in task_input.items():
        if isinstance(value, str) and value:
            variables[f"{key}_slug"] = slugify(value)
    return variables


def resolve_value(template: Any, bindings: dict[str, Any]) -> Any:
    if isinstance(template, str):
        result = _resolve_string(template, bindings)
        return _resolve_string(result, bindings) if isinstance(result, str) and "{{" in result else result
    if isinstance(template, dict):
        return {k: resolve_value(v, bindings) for k, v in template.items()}
    if isinstance(template, list):
        return [resolve_value(item, bindings) for item in template]
    return template


def _resolve_string(template: str, bindings: dict[str, Any]) -> Any:
    stripped = template.strip()
    match = _TEMPLATE_RE.fullmatch(stripped)
    if match:
        return _lookup(match.group(1).strip(), bindings)
    return _TEMPLATE_RE.sub(lambda m: str(_lookup(m.group(1).strip(), bindings)), template)


def _lookup(key: str, bindings: dict[str, Any]) -> Any:
    parts = key.split(".")
    root = parts[0]
    value = bindings.get(root)
    if value is None:
        return f"{{{{MISSING:{key}}}}}"
    for part in parts[1:]:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return f"{{{{MISSING:{key}}}}}"
        if value is None:
            return f"{{{{MISSING:{key}}}}}"
    return value


def build_bindings(
    *,
    task_input: dict[str, Any],
    step_outputs: dict[str, dict[str, Any]],
    variables: dict[str, Any],
    memory: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bindings: dict[str, Any] = {
        "input": task_input,
        "steps": step_outputs,
        "vars": variables,
        "memory": memory or {},
    }
    # Convenience aliases: {{date}}, {{iso}}, {{topic_slug}}, etc.
    bindings.update(variables)
    for key, value in task_input.items():
        if isinstance(value, str) and value:
            bindings[f"{key}_slug"] = slugify(value)
    return bindings
