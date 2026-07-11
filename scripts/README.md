# Scripts

Operational automation for AI-OS: setup, maintenance, batch jobs, and one-off utilities.

## Purpose

As the platform grows, repeatable tasks belong here rather than in ad-hoc shell history:

- Environment validation
- Knowledge ingestion and re-indexing
- Database migrations
- Backup and cleanup of `memory/` and indexes

## Guidelines

- Prefer idempotent scripts where possible.
- Document usage in the script header or a comment block.
- Accept configuration via environment variables (see `.env.example`).
- Do not embed secrets — read from `.env` or secure stores.

## Current state

Foundation phase — no scripts yet. Add them alongside the roadmap phase that needs them.

## Conventions (future)

```
scripts/
  setup.sh           # First-time local setup
  ingest.sh          # Batch raw → processed
  reindex.sh         # Rebuild knowledge/index
  doctor.sh          # Health checks
```
