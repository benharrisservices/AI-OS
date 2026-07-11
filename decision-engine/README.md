# Decision Engine

Structured AI decision-making: versioned prompts, output templates, and (eventually) orchestration logic.

## Purpose

The decision engine answers **how** the system turns context into actions — with repeatable prompts, schema-bound outputs, and traceable behavior.

## Structure

| Path | Role |
|------|------|
| `prompts/` | System and task prompts, named and versioned |
| `templates/` | Output formats, Jinja/Mustache shells, evaluation rubrics |

## Principles

- Prompts are **data**, not buried string literals in code.
- Templates define expected output shape before models run.
- High-risk decisions should support human approval (future orchestration).

## Configuration

See `DECISION_ENGINE_*` variables in [.env.example](../.env.example).

## Related docs

- [docs/architecture/system-overview.md](../docs/architecture/system-overview.md)
