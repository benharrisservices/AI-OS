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
| **5 — Hardening** | Tests, observability, deployment patterns, security review | **Complete** |
| **6 — Production** | Provider integrations, workflows, import tools, `doctor --full` | **Current** |

## Getting Started

### Prerequisites

- Git
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (recommended)
- API keys for your chosen LLM providers (stored locally, never committed)

### Install

```bash
git clone https://github.com/your-org/AI-OS.git
cd AI-OS
./scripts/install.sh
```

Or manually:

```bash
uv sync
cp .env.example .env   # add your API keys
uv run ai-os doctor --full
```

### Daily commands

```bash
uv run ai-os dashboard              # system overview
uv run ai-os doctor --full          # validate entire installation
uv run ai-os workflow run morning-briefing --input-file config/workflows/examples/morning-briefing.json
uv run ai-os import ./docs --type folder --tag docs
uv run ai-os provider health        # check provider adapters
uv run ai-os update --check         # verify installation
```

See [docs/OPERATING-MANUAL.md](docs/OPERATING-MANUAL.md) for a plain-language guide (no programming experience required).

See [config/workflows/README.md](config/workflows/README.md) for workflow examples and [docs/production-readiness.md](docs/production-readiness.md) for operational guidance.

## License

MIT — see [LICENSE](LICENSE).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). We welcome focused PRs that match the current roadmap phase.
