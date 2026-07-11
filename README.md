# AI-OS

A personal AI Operating System — a long-term foundation for orchestrating knowledge, memory, decisions, and experiments into a coherent, production-quality platform.

## What is AI-OS?

AI-OS is not a single application. It is an **operating system for AI-assisted work**: a structured repository and runtime environment where knowledge is ingested and indexed, decisions are made through explicit engines and prompts, memory persists across sessions, and experiments are isolated before promotion to production patterns.

The goal is to move beyond ad-hoc chat and one-off scripts toward a **durable, auditable, extensible** system that you own and evolve over years.

## Vision

| Principle | Description |
|-----------|-------------|
| **Ownership** | Your data, models, and workflows stay under your control. |
| **Composability** | Small, well-defined modules that plug together rather than a monolith. |
| **Observability** | Decisions, prompts, and outcomes are traceable and documented. |
| **Safety by design** | Secrets stay out of the repo; experiments stay isolated until validated. |
| **Longevity** | Architecture and docs are written for maintainers five years from now. |

We are building toward a system where:

- **Knowledge** flows from raw sources → processed artifacts → searchable index.
- **Memory** retains context across tasks without leaking into version control.
- **Decision engines** apply consistent prompts and templates to structured inputs.
- **Experiments** prove ideas in `experiments/` before they graduate to core paths.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI-OS (you)                              │
├─────────────┬─────────────┬──────────────┬────────────────────┤
│  Knowledge  │   Memory    │   Decision   │    Experiments       │
│  pipeline   │   layer     │   engine     │    sandbox           │
├─────────────┴─────────────┴──────────────┴────────────────────┤
│                    Config · Scripts · Tests                      │
└─────────────────────────────────────────────────────────────────┘
```

| Layer | Role |
|-------|------|
| **knowledge/** | Ingest, transform, and index information for retrieval and reasoning. |
| **memory/** | Session and long-term state (gitignored); not committed secrets or PII. |
| **decision-engine/** | Prompts, templates, and orchestration for structured AI decisions. |
| **experiments/** | Time-boxed trials; archive when done. |
| **config/** | Non-secret configuration schemas and defaults. |
| **scripts/** | Operational automation (setup, maintenance, batch jobs). |
| **docs/** | Architecture, roadmap, and architecture decision records (ADRs). |
| **tests/** | Verification as the codebase grows. |

See [docs/architecture/system-overview.md](docs/architecture/system-overview.md) for the full evolution path.

## Folder Structure

```
AI-OS/
├── config/                 # Configuration schemas and environment templates
├── decision-engine/      # Prompts and templates for structured decisions
│   ├── prompts/
│   └── templates/
├── docs/                   # Project documentation
│   ├── architecture/       # System design and overviews
│   ├── decisions/          # Architecture Decision Records (ADRs)
│   └── roadmap/            # Planned milestones and priorities
├── experiments/            # Sandboxed trials
│   └── archive/            # Completed or abandoned experiments
├── knowledge/              # Knowledge pipeline
│   ├── raw/                # Unprocessed inputs
│   ├── processed/          # Normalized artifacts
│   └── index/              # Search / retrieval indexes
├── memory/                 # Runtime memory (local, gitignored)
├── scripts/                # Maintenance and automation scripts
├── tests/                  # Test suites
├── .env.example            # Environment variable reference (no secrets)
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## Roadmap

High-level phases (details in [docs/roadmap/](docs/roadmap/)):

| Phase | Focus | Status |
|-------|--------|--------|
| **0 — Foundation** | Repo structure, docs, config contracts, `.gitignore`, contribution guidelines | **Current** |
| **1 — Knowledge** | Ingestion contracts, processing pipeline, basic indexing | Planned |
| **2 — Memory** | Persistent context model, retention policies, privacy boundaries | Planned |
| **3 — Decision engine** | Prompt registry, template versioning, evaluation harness | Planned |
| **4 — Integration** | Orchestration layer tying knowledge + memory + decisions | Planned |
| **5 — Hardening** | Tests, observability, deployment patterns, security review | Planned |

## Getting Started

### Prerequisites

- Git
- A Unix-like shell (macOS or Linux recommended)
- Python 3.11+ and/or Node.js 20+ (when application code is added)
- API keys for your chosen LLM providers (stored locally, never committed)

### Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/your-org/AI-OS.git
   cd AI-OS
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   # Edit .env with your local values — never commit .env
   ```

3. **Read the docs**

   - [System overview](docs/architecture/system-overview.md)
   - [Contributing](CONTRIBUTING.md)
   - Directory READMEs under each top-level folder

4. **Explore safely**

   - Put experiments under `experiments/`
   - Put raw inputs under `knowledge/raw/`
   - Record significant choices in `docs/decisions/`

### What is intentionally not here yet

This repository is in **foundation phase**. There is no application runtime, package manifest, or installed dependencies. That keeps the architecture honest before code accretes.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We welcome focused PRs that match the current roadmap phase.
