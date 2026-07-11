# Decision Engine — Prompts

Versioned prompt files for the AI-OS decision engine.

## Conventions (recommended)

- One concern per file: `summarize-session.md`, `route-task-v1.md`
- Include YAML front matter when useful:

  ```yaml
  ---
  name: summarize-session
  version: 1.0.0
  model: default
  temperature: 0.2
  ---
  ```

- Document required variables in the file header or companion template.

## Guidelines

- Avoid hardcoding secrets or PII in examples.
- Breaking prompt changes bump version or filename suffix (`-v2`).
- Evaluation fixtures (future: `tests/`) should reference prompt names, not inline copies.
