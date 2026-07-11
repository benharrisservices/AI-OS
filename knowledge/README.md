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
- **Processed** output uses the schemas in [schema.md](schema.md) and [metadata-schema.md](metadata-schema.md).
- **Index** artifacts are generated; never commit model weights or full databases.

## Phase 1 design docs

| Document | Contents |
|----------|----------|
| [pipeline.md](pipeline.md) | Stage-by-stage ingestion and indexing jobs |
| [schema.md](schema.md) | On-disk layouts and JSON record shapes |
| [metadata-schema.md](metadata-schema.md) | Field semantics, filters, and citations |

## Configuration

See [.env.example](../.env.example) variables prefixed with `KNOWLEDGE_` and `VECTOR_STORE_*`.

## Related docs

- [docs/architecture/knowledge-engine.md](../docs/architecture/knowledge-engine.md)
- [docs/architecture/system-overview.md](../docs/architecture/system-overview.md)
- [docs/decisions/ADR-001-knowledge-engine.md](../docs/decisions/ADR-001-knowledge-engine.md)
