# Config

Non-secret configuration schemas, defaults, and feature-flag definitions for AI-OS.

## Purpose

Central place for **committed** configuration structure — not runtime secrets.

## Intended contents

- YAML/JSON/TOML schemas for app settings
- Default values safe to share in version control
- Feature flag definitions referenced by `.env` or orchestration
- Example config files (e.g. `settings.example.yaml`)

## What does not belong here

- `.env` or API keys
- User-specific overrides with sensitive data
- Generated indexes or databases

## Relationship to `.env`

| Source | Role |
|--------|------|
| `config/` | Structure, defaults, schemas (committed) |
| `.env` | Secrets and machine-local overrides (gitignored) |
| `.env.example` | Documented variable catalog (committed) |

## Current state

Foundation phase — add schema files as each roadmap phase defines contracts.
