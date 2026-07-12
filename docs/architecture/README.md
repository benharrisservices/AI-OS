# Architecture Documentation

Technical design artifacts for AI-OS: how components connect, what each layer owns, and how the system scales over time.

## Key documents

- [system-overview.md](system-overview.md) — end-to-end architecture and evolution phases
- [knowledge-engine.md](knowledge-engine.md) — Phase 1 Knowledge Engine design (ingestion, indexing, retrieval)
- [memory-system.md](memory-system.md) — Phase 3.5 Memory System (four tiers, promotion, façade)
- [automation-layer.md](automation-layer.md) — Phase 4 Automation Layer (scheduling, triggers)
- [layer-boundaries.md](layer-boundaries.md) — Approved dependency direction and extension rules

## What belongs here

- System diagrams and data-flow descriptions
- Interface contracts between layers (knowledge, memory, decision engine)
- Deployment and security architecture (as they are defined)
- Performance and reliability considerations

## What does not belong here

- Step-by-step tutorials (future: `docs/guides/` if needed)
- Experiment notes (use `experiments/<name>/`)
- Runtime secrets or environment-specific values
