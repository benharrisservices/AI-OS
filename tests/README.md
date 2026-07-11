# Tests

Automated verification for AI-OS as application code is introduced.

## Purpose

Protect regressions in:

- Knowledge ingestion and indexing
- Memory retention and summarization
- Decision engine prompts and template validation
- Integration flows between layers

## Structure (recommended, future)

```
tests/
  unit/           # Fast, isolated tests
  integration/    # Cross-module with fixtures
  fixtures/       # Golden files, sample chunks
  conftest.py     # Shared pytest setup (if using Python)
```

## Guidelines

- No secrets in fixtures — use synthetic data.
- Golden prompt/output pairs live in `fixtures/` when testing the decision engine.
- CI configuration (future) runs tests on every PR.

## Current state

Foundation phase — no test suite yet. Add tests when Phase 1+ code lands.

## Related

- [CONTRIBUTING.md](../CONTRIBUTING.md) — PR expectations
- [docs/architecture/system-overview.md](../docs/architecture/system-overview.md)
