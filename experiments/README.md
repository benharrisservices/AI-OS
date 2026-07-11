# Experiments

Sandbox for time-boxed trials before ideas graduate to core AI-OS paths.

## Purpose

Experiments let you test ingestion strategies, prompt patterns, memory models, or integrations **without** polluting production directories or committing unstable code to shared conventions.

## Workflow

1. Create `experiments/<short-name>/` with its own README describing hypothesis, scope, and success criteria.
2. Keep dependencies local to the experiment when possible.
3. On completion:
   - **Success** — propose promotion via ADR + roadmap; move folder to `archive/`.
   - **Failure** — document learnings in README; move to `archive/`.

## Rules

- Do not import from experiments into core modules without an explicit promotion.
- Large outputs go in `output/` or `artifacts/` (gitignored).
- Never commit secrets or production credentials in experiment folders.

## Related

- [archive/](archive/) — completed or abandoned experiments
- [docs/decisions/](../docs/decisions/) — record promotions and major learnings
