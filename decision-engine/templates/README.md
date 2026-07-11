# Decision Engine — Templates

Output schemas and structural templates for model responses.

## Intended contents

- JSON Schema or similar definitions for structured outputs
- Jinja2 / Mustache templates for assembling final messages
- Rubrics for self-evaluation or judge models

## Guidelines

- Pair each template with the prompt(s) that use it.
- Validate outputs against schema in tests when application code exists.
- Keep templates deterministic where possible; reserve stochastic behavior for prompts.

## Example layout (future)

```
templates/
  task-router.output.schema.json
  daily-summary.md.j2
  code-review.rubric.yaml
```
