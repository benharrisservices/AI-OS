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

## Implemented Architecture (v0.3.x)

```
Knowledge Engine  →  Decision Engine  →  Agent Runtime  →  Automation
                            ↑                    ↑              │
                         Memory System    (via MemoryManager) │
                                                              │
                                         schedules & triggers ┘
```

| Layer | Package | Status |
|-------|---------|--------|
| Knowledge | `src/ai_os/knowledge/` | Complete (v0.1.0) |
| Decision | `src/ai_os/decision/` | Complete (v0.2.0) |
| Agent Runtime | `src/ai_os/agent/` | Complete (v0.3.0) |
| Memory | `src/ai_os/memory/` | Complete (v0.3.0) |
| Automation | `src/ai_os/automation/` | Complete (v0.4.0) |

See [layer-boundaries.md](layer-boundaries.md) for dependency rules and [memory-system.md](memory-system.md) for memory tier design.

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

### Memory Layer (`src/ai_os/memory/`)

The memory layer answers: **What happened before, and what experience persists?**

Memory is **runtime experience**, not canonical knowledge. Four independent types (working, episodic, semantic, procedural) are managed through the `MemoryManager` façade. Agent Runtime accesses memory only via this public API.

**Implemented capabilities:**

- Tiered memory with automatic working-memory expiration
- Staged promotion (Working → Episodic → Semantic)
- Task-scoped retrieval injected into Agent Runtime context
- CLI: `ai-os memory list|search|show|promote|archive|expire`

### Decision Engine (`src/ai_os/decision/`)

The decision layer answers: **What should we do?**

Consumes `ContextBundle` from Knowledge; never performs retrieval itself. Six reasoning strategies, structured `DecisionResult` output, persistence to `memory/decisions/`.

### Agent Runtime (`src/ai_os/agent/`)

The agent layer answers: **How do we execute?**

Orchestrates tools (Knowledge, Decision, filesystem, HTTP, datetime) via YAML workflows. Injects `MemoryBundle` at task creation. Never retrieves facts or reasons directly.

### Automation Layer (`src/ai_os/automation/`)

The automation layer answers: **When should execution happen?**

Schedules and triggers workflow execution via `AutomationService`. Delegates all execution to Agent Runtime. Supports cron, recurring, delayed, and one-time schedules plus filesystem, webhook, startup, and workflow-completion triggers.

**CLI:** `ai-os automation list|run|enable|disable|history|schedule`

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
