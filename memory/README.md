# Memory

Runtime memory for AI-OS: session context, working state, and long-term recall that should **not** live in git.

## Purpose

Memory answers **what context persists across interactions** — distinct from canonical knowledge in `knowledge/`.

Typical contents (all local, gitignored):

- Conversation and task history
- Compacted summaries of long sessions
- User preferences and ephemeral working notes
- SQLite/Redis files backing the memory store

## Privacy and security

- This directory is **gitignored** except this README and `.gitkeep`.
- Never commit API keys, tokens, or unredacted PII.
- Use `ENCRYPTION_KEY` in `.env` when encryption at rest is implemented.
- Promote durable facts to `knowledge/processed/` only through an explicit process.

## Configuration

See `MEMORY_*` and `DATABASE_URL` in [.env.example](../.env.example).

## Related docs

- [docs/architecture/system-overview.md](../docs/architecture/system-overview.md) — memory layer design
