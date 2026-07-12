# Production Readiness

AI-OS v1.1+ focuses on validation, integration, and daily usability without architectural changes.

## System validation

```bash
uv run ai-os doctor --full
```

Validates Python, dependencies, knowledge engine, decision engine, memory, agent runtime, automation, capabilities, integrations, model router, and configuration paths.

## Provider integrations

Priority providers with real HTTP adapters:

| Provider | Env vars | Health check |
|----------|----------|--------------|
| GitHub | `GITHUB_TOKEN` | `/user` API |
| Gmail | `GOOGLE_ACCESS_TOKEN` (+ OAuth client IDs) | Gmail profile |
| Google Calendar | `GOOGLE_ACCESS_TOKEN` | Calendar list |
| Google Drive | `GOOGLE_ACCESS_TOKEN` | Drive about |
| Ollama | `OLLAMA_HOST` | `/api/tags` |
| OpenAI | `OPENAI_API_KEY` | `/models` |
| Anthropic | `ANTHROPIC_API_KEY` | `/models` |
| Gemini | `GOOGLE_API_KEY` | `/models` |
| OpenRouter | `OPENROUTER_API_KEY` | `/models` |

```bash
uv run ai-os provider health
uv run ai-os provider list
```

## Knowledge import

```bash
# Markdown folder
uv run ai-os import ./docs --type folder --tag docs

# PDF or DOCX file
uv run ai-os import report.pdf --type pdf

# GitHub README
uv run ai-os import owner/repo --type github

# Chat export
uv run ai-os import chats/export.json --type chats

# Clone and import
uv run ai-os import https://github.com/org/repo --clone
```

Duplicate detection uses content fingerprints — unchanged files are skipped.

## Workflows

Example inputs live in `config/workflows/examples/`. See [config/workflows/README.md](../../config/workflows/README.md).

## Installation and updates

```bash
./scripts/install.sh
uv run ai-os update          # sync dependencies
uv run ai-os update --check  # verify without syncing
```

## Backup and restore

```bash
uv run ai-os backup
uv run ai-os maintenance run
```
