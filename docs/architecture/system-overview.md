# System Overview — AI-OS

This document describes how the AI-OS repository is intended to evolve from a documentation-first foundation into a **personal AI operating system**: a cohesive environment where knowledge, memory, and decision-making work together under explicit governance.

## Purpose

Most AI tooling today is fragmented: chats in one place, notes in another, scripts in a third, and no durable memory or audit trail. AI-OS addresses that by treating AI assistance as **infrastructure** — with clear boundaries, data flows, and extension points — rather than as a collection of disconnected utilities.

## Design Goals

1. **Single source of structural truth** — The repo defines where things live and how they connect.
2. **Separation of concerns** — Knowledge (facts), memory (context), and decisions (actions) are distinct layers.
3. **Progressive disclosure** — Start simple (files and folders); add services only when complexity demands it.
4. **Local-first, cloud-optional** — Run on your machine by default; integrate external APIs and hosted stores when needed.
5. **Auditability** — Prompts, templates, and ADRs are versioned; experiments are isolated and archivable.

## Conceptual Architecture

```
                    ┌──────────────────────────────────────┐
                    │           User / Operator             │
                    └──────────────────┬───────────────────┘
                                       │
                    ┌──────────────────▼───────────────────┐
                    │         Orchestration (future)        │
                    │  routes tasks · enforces policies     │
                    └─┬────────────┬────────────┬──────────┘
                      │            │            │
         ┌────────────▼──┐  ┌──────▼──────┐  ┌──▼─────────────┐
         │   Knowledge    │  │   Memory    │  │ Decision       │
         │   Pipeline     │  │   Layer     │  │ Engine         │
         │                │  │             │  │                │
         │ raw → processed│  │ sessions    │  │ prompts        │
         │ → index        │  │ long-term   │  │ templates      │
         └────────┬───────┘  └──────┬──────┘  └──┬─────────────┘
                  │                 │             │
                  └────────┬────────┴─────────────┘
                           │
              ┌────────────▼────────────┐
              │  Config · Scripts · Tests │
              └─────────────────────────┘
```

## Layer Descriptions

### Knowledge Pipeline (`knowledge/`)

The knowledge layer answers: **What does the system know, and how can it be retrieved?**

| Stage | Location | Role |
|-------|----------|------|
| Ingest | `knowledge/raw/` | Original documents, exports, API dumps, transcripts |
| Transform | `knowledge/processed/` | Normalized markdown, JSON, chunks, metadata |
| Index | `knowledge/index/` | Embeddings, vector stores, search indexes |

**Future capabilities:**

- Pluggable extractors (PDF, web, email, code repos)
- Chunking and metadata schemas
- Incremental re-indexing
- Hybrid search (keyword + semantic)

### Memory Layer (`memory/`)

The memory layer answers: **What context persists across sessions, and under what rules?**

Memory is **runtime state**, not canonical knowledge. It includes conversation history, working summaries, user preferences, and task state. Contents are **gitignored** by default to avoid leaking secrets or PII into version control.

**Future capabilities:**

- Tiered retention (working → session → long-term)
- Summarization and compaction policies
- Encryption at rest (via `ENCRYPTION_KEY` in `.env`)
- Explicit promotion: memory → knowledge when something should be permanent

### Decision Engine (`decision-engine/`)

The decision layer answers: **How does the system choose actions and produce structured outputs?**

| Asset | Location | Role |
|-------|----------|------|
| Prompts | `decision-engine/prompts/` | System and task prompts, versioned by name |
| Templates | `decision-engine/templates/` | Output schemas, Jinja/Mustache shells, evaluation rubrics |

**Future capabilities:**

- Prompt registry with semver or date versioning
- Input/output JSON schemas
- Evaluation harness against golden fixtures
- Human-in-the-loop approval gates for high-risk decisions

### Experiments (`experiments/`)

Experiments answer: **Can we prove this idea before it touches core paths?**

Each experiment is a sandbox with its own README, scope, and success criteria. Completed work moves to `experiments/archive/` with a short retrospective. Nothing in experiments is assumed production-ready until promoted via ADR and roadmap phase.

### Supporting Infrastructure

| Component | Path | Role |
|-----------|------|------|
| Configuration | `config/` | Schemas, defaults, feature flags (no secrets) |
| Automation | `scripts/` | Setup, migrations, batch indexing, maintenance |
| Verification | `tests/` | Unit, integration, and contract tests as code lands |
| Documentation | `docs/` | Architecture, roadmap, ADRs |

## Data Flow (Target State)

```
1. User adds source material        → knowledge/raw/
2. Ingestion job normalizes         → knowledge/processed/
3. Indexer embeds and stores        → knowledge/index/
4. Task starts                      → memory/ (session context)
5. Decision engine loads prompt     → decision-engine/prompts/
6. Engine retrieves relevant chunks → knowledge/index/
7. LLM produces structured output   → memory/ + optional knowledge/processed/
8. User approves promotion          → knowledge/processed/ (durable fact)
```

## Evolution Phases

### Phase 0 — Foundation (current)

- Directory layout, `.gitignore`, `.env.example`
- Documentation and contribution guidelines
- No runtime dependencies or application code

### Phase 1 — Knowledge

- Define formats for `raw/` and `processed/`
- Implement minimal ingestion and chunking (scripts or small modules)
- Local vector index with configurable backend

### Phase 2 — Memory

- Memory store abstraction (SQLite/Redis/file)
- Retention and summarization policies
- Clear boundary: what never leaves `memory/`

### Phase 3 — Decision Engine

- Prompt and template loading
- Schema-validated outputs
- Trace logging (prompt hash, model, latency, token usage)

### Phase 4 — Integration

- Task router connecting knowledge retrieval + memory + decisions
- CLI or API entry point
- Optional web UI behind feature flags

### Phase 5 — Hardening

- Test coverage, CI, security review
- Observability (OpenTelemetry, structured logs)
- Deployment recipes (Docker, single-binary, or managed)

## Non-Goals (for now)

- Multi-tenant SaaS productization
- Replacing general-purpose IDEs or note apps
- Bundling proprietary model weights in the repo
- Implicit auto-commit of all LLM output to git

## Governance

- **Roadmap** — `docs/roadmap/` defines what ships when.
- **ADRs** — `docs/decisions/` records irreversible or expensive choices.
- **CHANGELOG** — User-visible changes at the root.
- **Secrets** — Only in `.env`; `.env.example` stays documentation-only.

## Extension Points

Future contributors and automation should hook in at:

1. **Extractors** — New `knowledge/raw` source types
2. **Stores** — Vector DB and memory backends via env configuration
3. **Providers** — LLM and embedding APIs via unified client interface
4. **Prompts** — Drop-in files under `decision-engine/prompts/`
5. **Policies** — Config-driven retention, rate limits, and feature flags

## Summary

AI-OS grows from **structure and contracts** into **running software** without sacrificing clarity. Each layer has a named home, gitignored runtime state stays out of history, and experiments prove value before promotion. This overview should be updated when phases complete or when ADRs supersede assumptions here.
