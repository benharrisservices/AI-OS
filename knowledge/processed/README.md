# Knowledge — Processed

Normalized, structured artifacts derived from `../raw/`.

## Intended contents

- Chunked text with stable IDs
- Extracted metadata (title, source, date, tags)
- Intermediate formats (markdown, JSON Lines) ready for indexing

## Rules

- Generated files are **gitignored** — reproducible from raw + processing version.
- Document schemas in `docs/architecture/` when Phase 1 begins.
- Promote only curated, non-sensitive summaries to version control if explicitly needed.

## Next step

Indexers write embeddings and search structures to `../index/`.
