# Personal AI-OS Configuration

Guides and templates for configuring AI-OS around your daily life. No secrets belong in this directory — copy templates to `.env` and `config/personal/` locally.

| Document | Purpose |
|----------|---------|
| [provider-configuration.md](./provider-configuration.md) | Credentials, setup steps, and `.env` values for all nine providers |
| [knowledge-import-plan.md](./knowledge-import-plan.md) | Ordered import plan for your information categories |
| [../roadmap/v1.2-roadmap.md](../roadmap/v1.2-roadmap.md) | Prioritized improvements (not yet implemented) |

## Workflow templates

Edit JSON files in `config/personal/workflows/` then run:

```bash
ai-os workflow run morning-briefing --input-file config/personal/workflows/morning-briefing.json
```

## Quick validation

```bash
cp config/personal/providers.env.example .env   # merge into your existing .env
# Fill in credentials (see provider-configuration.md)
ai-os doctor --full
ai-os provider health
```
