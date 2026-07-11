"""Resolve template references in workflow step inputs."""

from __future__ import annotations

import re
from typing import Any

_TEMPLATE_RE = re.compile(r"\{\{([^}]+)\}\}")


def resolve_value(template: Any, bindings: dict[str, Any]) -> Any:
    if isinstance(template, str):
        if _TEMPLATE_RE.fullmatch(template.strip()):
            key = _TEMPLATE_RE.fullmatch(template.strip()).group(1).strip()
            return _lookup(key, bindings)
        return _TEMPLATE_RE.sub(lambda m: str(_lookup(m.group(1).strip(), bindings)), template)
    if isinstance(template, dict):
        return {k: resolve_value(v, bindings) for k, v in template.items()}
    if isinstance(template, list):
        return [resolve_value(item, bindings) for item in template]
    return template


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
) -> dict[str, Any]:
    return {
        "input": task_input,
        "steps": step_outputs,
        "vars": variables,
    }
