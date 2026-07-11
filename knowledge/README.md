# Knowledge

The knowledge pipeline stores **what the system knows** in three stages: raw inputs, processed artifacts, and searchable indexes.

## Pipeline

```
raw/  →  processed/  →  index/
```

| Stage | Directory | Description |
|-------|-----------|-------------|
| Ingest | `raw/` | Original sources: documents, exports, transcripts, API dumps |
| Transform | `processed/` | Normalized, chunked, metadata-enriched content |
| Retrieve | `index/` | Embeddings, vector stores, and search indexes |

## Guidelines

- **Raw** material may be large or sensitive — it is gitignored except this README and `.gitkeep`.
- **Processed** output should use documented schemas (to be defined in Phase 1).
- **Index** artifacts are generated; never commit model weights or full databases.

## Configuration

See [.env.example](../.env.example) variables prefixed with `KNOWLEDGE_` and `VECTOR_STORE_*`.

## Related docs

- [docs/architecture/system-overview.md](../docs/architecture/system-overview.md)
