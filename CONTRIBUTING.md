# Contributing to AI-OS

Thank you for helping build a durable personal AI operating system. This document explains how to contribute effectively while the project is still in its foundation phase.

## Code of Conduct

Be respectful, constructive, and security-conscious. Do not commit secrets, personal data, or large model weights.

## Before You Start

1. Read [README.md](README.md) and [docs/architecture/system-overview.md](docs/architecture/system-overview.md).
2. Check [docs/roadmap/](docs/roadmap/) for the current phase — avoid building ahead of agreed milestones.
3. Search existing [docs/decisions/](docs/decisions/) for prior architectural choices.

## Development Workflow

### Branching

- `main` — stable foundation and approved changes.
- Feature branches: `feature/<short-description>` or `docs/<topic>`.
- Experiments: work in `experiments/<name>/` before promoting to core paths.

### Commits

- Use clear, imperative messages: `Add knowledge ingestion contract`, `Document memory retention policy`.
- One logical change per commit when possible.
- Never commit `.env`, API keys, databases, or model files.

### Pull Requests

1. Fork or branch from `main`.
2. Keep scope focused — foundation PRs should not sneak in application runtime code unless the roadmap phase calls for it.
3. Update [CHANGELOG.md](CHANGELOG.md) under `Unreleased` for user-visible changes.
4. Add or update README files in directories you touch.
5. For architectural changes, add an ADR in `docs/decisions/`.

### PR Description Template

```markdown
## Summary
What changed and why.

## Type
- [ ] Documentation
- [ ] Structure / config
- [ ] Experiment
- [ ] Application code (note roadmap phase)

## Test plan
How you verified the change.

## ADR
Link to docs/decisions/ if applicable.
```

## Directory Guidelines

| Path | Contribution notes |
|------|-------------------|
| `docs/` | Prefer markdown; keep diagrams in architecture docs. |
| `knowledge/` | Raw inputs may be large — use `.gitignore`; document formats in README. |
| `memory/` | **Never commit runtime memory** — local only. |
| `decision-engine/` | Version prompts; document expected inputs/outputs. |
| `experiments/` | Self-contained; archive when done. |
| `config/` | Schemas and examples only — no secrets. |
| `scripts/` | Idempotent when possible; document usage in script header or README. |
| `tests/` | Add tests when application code lands. |

## Architecture Decision Records (ADRs)

Significant choices (storage engine, memory model, orchestration library) get an ADR:

- File: `docs/decisions/NNNN-short-title.md`
- Sections: Context, Decision, Consequences, Alternatives considered

## Security

- Copy [.env.example](.env.example) to `.env` locally — never commit `.env`.
- Redact PII in examples and logs.
- Report security issues privately to maintainers (do not open public issues for active vulnerabilities).

## Style

- Markdown: readable line lengths, tables for comparisons, links over duplication.
- Future Python: PEP 8, type hints where helpful.
- Future TypeScript: strict mode, consistent with project config when added.

## Questions

Open a discussion or issue with the `question` label. For design debates, propose a short ADR draft first.
