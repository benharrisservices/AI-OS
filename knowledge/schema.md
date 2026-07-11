# Knowledge Engine — Schema Reference

**Phase 1 design** · Status: specification only (no implementation)

This document defines on-disk layouts, directory structure, and JSON record shapes for the Knowledge Engine. Field-level semantics for metadata are expanded in [metadata-schema.md](metadata-schema.md).

---

## Directory layout

```
knowledge/
├── raw/
│   ├── .registry/
│   │   └── sources.jsonl          # Source registry (append-only log)
│   └── {source_id}/
│       ├── original.{ext}         # Immutable bytes
│       ├── intake.json            # Intake metadata
│       ├── snapshot.html          # URL/HTML only
│       └── headers.json           # URL fetch headers
│
├── processed/
│   ├── .catalog/
│   │   └── documents.jsonl        # Global document catalog
│   └── documents/
│       └── {doc_id}/
│           ├── document.md        # Canonical markdown + front matter
│           ├── document.meta.json # Document record
│           ├── chunks.jsonl       # One line per chunk
│           └── embeddings.jsonl   # One line per embedding
│
└── index/
    ├── manifest.json              # Index version and stats
    ├── .catalog/
    │   └── chunks.jsonl           # Denormalized chunk index (optional)
    ├── embeddings/
    │   └── cache/
    │       └── {content_hash}.json
    ├── vectors/                   # Backend-specific (local, lancedb, etc.)
    └── keyword/                   # BM25 index files
```

All paths are configurable via `KNOWLEDGE_*_DIR` environment variables.

---

## Versioning and schema evolution

| Field | Location | Purpose |
|-------|----------|---------|
| `schema_version` | Every JSON record | Record shape version |
| `pipeline_version` | Document + manifest | Processing logic semver |

**Rules:**

- Bump `schema_version` on breaking field changes
- Readers must accept `schema_version` ≤ current and reject unknown major versions
- `pipeline_version` change does not auto-invalidate content; operators choose reprocess scope

Current versions (Phase 1 design):

```json
{
  "schema_version": "1.0",
  "pipeline_version": "1.0.0"
}
```

---

## Enumerations

### `Format`

`markdown` | `txt` | `pdf` | `docx` | `html` | `url`

### `SourceStatus`

`pending` | `processing` | `ready` | `failed` | `tombstoned` | `unchanged`

### `ExtractionQuality`

`full` | `degraded` | `failed`

### `ChunkLevel`

`parent` | `child`

---

## Source registry record

**File:** `knowledge/raw/.registry/sources.jsonl` (one JSON object per line)

```json
{
  "schema_version": "1.0",
  "source_id": "src_01JXYZABCDEF",
  "status": "ready",
  "format": "pdf",
  "fingerprint": "sha256:a1b2c3...",
  "fingerprint_algorithm": "sha256",
  "original_filename": "architecture-notes.pdf",
  "original_uri": "file:///Users/me/docs/architecture-notes.pdf",
  "byte_size": 1048576,
  "doc_ids": ["doc_01JXYZABCDEF"],
  "tags": ["architecture", "internal"],
  "intake_channel": "cli",
  "created_at": "2026-07-11T15:00:00Z",
  "updated_at": "2026-07-11T15:05:00Z",
  "last_job_id": "job_01JXYZ...",
  "error": null
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `source_id` | string | yes | Stable source identifier |
| `status` | SourceStatus | yes | Pipeline state |
| `format` | Format | yes | Detected format |
| `fingerprint` | string | yes | Content hash for change detection |
| `doc_ids` | string[] | yes | Documents derived from this source |
| `error` | ErrorRecord \| null | yes | Last failure if `status = failed` |

---

## Intake record

**File:** `knowledge/raw/{source_id}/intake.json`

```json
{
  "schema_version": "1.0",
  "source_id": "src_01JXYZABCDEF",
  "kind": "file",
  "path_or_url": "/Users/me/inbox/architecture-notes.pdf",
  "format": "pdf",
  "fingerprint": "sha256:a1b2c3...",
  "original_filename": "architecture-notes.pdf",
  "mime_type": "application/pdf",
  "byte_size": 1048576,
  "tags": ["architecture"],
  "operator_metadata": {},
  "intake_channel": "cli",
  "intaked_at": "2026-07-11T15:00:00Z"
}
```

For URL intake, additional fields:

```json
{
  "kind": "url",
  "path_or_url": "https://example.com/docs/guide.html",
  "final_url": "https://example.com/docs/guide.html",
  "http_status": 200,
  "fetched_at": "2026-07-11T15:00:00Z",
  "content_type": "text/html; charset=utf-8"
}
```

---

## Document record

**File:** `knowledge/processed/documents/{doc_id}/document.meta.json`  
**Catalog:** append to `knowledge/processed/.catalog/documents.jsonl`

```json
{
  "schema_version": "1.0",
  "pipeline_version": "1.0.0",
  "doc_id": "doc_01JXYZABCDEF",
  "source_id": "src_01JXYZABCDEF",
  "title": "Architecture Notes",
  "language": "en",
  "format": "pdf",
  "extraction_quality": "full",
  "page_count": 12,
  "word_count": 4521,
  "char_count": 28400,
  "heading_count": 8,
  "chunk_count": 24,
  "parent_count": 8,
  "tags": ["architecture", "internal"],
  "created_at": "2026-07-11T15:02:00Z",
  "updated_at": "2026-07-11T15:03:00Z",
  "source_uri": "file:///Users/me/inbox/architecture-notes.pdf",
  "raw_path": "knowledge/raw/src_01JXYZABCDEF/original.pdf",
  "processed_path": "knowledge/processed/documents/doc_01JXYZABCDEF/document.md",
  "custom": {}
}
```

### `document.md` front matter

YAML front matter at the top of `document.md` mirrors key document fields for human editing:

```yaml
---
doc_id: doc_01JXYZABCDEF
source_id: src_01JXYZABCDEF
title: Architecture Notes
language: en
tags:
  - architecture
  - internal
created_at: 2026-07-11T15:02:00Z
---

# Architecture Notes

Body begins here...
```

**Rule:** `document.meta.json` is authoritative for machines; front matter is authoritative for human edits during reprocess. A reconcile step merges them on re-ingest.

---

## Chunk record

**File:** `knowledge/processed/documents/{doc_id}/chunks.jsonl`

```json
{
  "schema_version": "1.0",
  "chunk_id": "chk_01JXYZCHUNK01",
  "doc_id": "doc_01JXYZABCDEF",
  "source_id": "src_01JXYZABCDEF",
  "chunk_level": "child",
  "parent_chunk_id": "chk_01JXYZPARENT1",
  "chunk_index": 3,
  "heading_path": "architecture/ingestion",
  "title": "Architecture Notes",
  "language": "en",
  "token_count": 487,
  "char_count": 2104,
  "content_hash": "sha256:def456...",
  "embed_text": "Document: Architecture Notes > architecture/ingestion\n\nIntake flow begins with...",
  "body_text": "Intake flow begins with...",
  "start_offset": 4200,
  "end_offset": 6304,
  "page_start": 4,
  "page_end": 5,
  "tags": ["architecture", "internal"],
  "created_at": "2026-07-11T15:03:00Z"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `chunk_id` | string | yes | Stable chunk identifier |
| `chunk_level` | ChunkLevel | yes | `parent` or `child` |
| `parent_chunk_id` | string \| null | yes | Null for parent chunks |
| `heading_path` | string | yes | Slash-separated section path |
| `embed_text` | string | yes | Text sent to embedding model |
| `body_text` | string | yes | Raw chunk without context prefix |
| `content_hash` | string | yes | Hash of normalized `embed_text` |
| `start_offset` / `end_offset` | integer | yes | Character offsets in `document.md` body |

---

## Embedding record

**File:** `knowledge/processed/documents/{doc_id}/embeddings.jsonl`

```json
{
  "schema_version": "1.0",
  "chunk_id": "chk_01JXYZCHUNK01",
  "doc_id": "doc_01JXYZABCDEF",
  "content_hash": "sha256:def456...",
  "embedding_model": "text-embedding-3-small",
  "embedding_provider": "openai",
  "embedding_dimensions": 1536,
  "vector": [0.0123, -0.0456, "..."],
  "embedded_at": "2026-07-11T15:04:00Z",
  "cache_hit": false
}
```

**Note:** Vectors may be omitted from JSONL when stored only in the vector backend if `store_vectors_externally: true` in config. Default for local-first is inline JSONL + cache for portability.

### Embedding cache record

**File:** `knowledge/index/embeddings/cache/{content_hash}.json`

```json
{
  "content_hash": "sha256:def456...",
  "embedding_model": "text-embedding-3-small",
  "embedding_dimensions": 1536,
  "vector": [0.0123, -0.0456, "..."],
  "embedded_at": "2026-07-11T15:04:00Z"
}
```

---

## Vector index record

**Logical record** passed to `VectorStore.upsert()` (not necessarily on-disk format):

```json
{
  "chunk_id": "chk_01JXYZCHUNK01",
  "doc_id": "doc_01JXYZABCDEF",
  "source_id": "src_01JXYZABCDEF",
  "vector": [0.0123, -0.0456],
  "filter": {
    "language": "en",
    "tags": ["architecture", "internal"],
    "format": "pdf",
    "heading_path": "architecture/ingestion"
  }
}
```

Filter fields must be a subset of [filterable metadata](metadata-schema.md#filterable-fields).

---

## Index manifest

**File:** `knowledge/index/manifest.json`

```json
{
  "schema_version": "1.0",
  "index_version": "1",
  "pipeline_version": "1.0.0",
  "embedding_provider": "openai",
  "embedding_model": "text-embedding-3-small",
  "embedding_dimensions": 1536,
  "vector_store": "local",
  "vector_store_path": "knowledge/index/vectors",
  "keyword_index_path": "knowledge/index/keyword",
  "source_count": 15,
  "document_count": 15,
  "chunk_count": 318,
  "child_chunk_count": 286,
  "last_full_rebuild_at": null,
  "last_incremental_at": "2026-07-11T15:05:00Z",
  "created_at": "2026-07-10T10:00:00Z",
  "updated_at": "2026-07-11T15:05:00Z"
}
```

---

## Job manifest

**File:** `knowledge/processed/.jobs/{job_id}.json` (transient, gitignored)

```json
{
  "schema_version": "1.0",
  "job_id": "job_01JXYZ...",
  "job_type": "process",
  "source_id": "src_01JXYZABCDEF",
  "doc_id": "doc_01JXYZABCDEF",
  "status": "completed",
  "started_at": "2026-07-11T15:01:00Z",
  "completed_at": "2026-07-11T15:03:00Z",
  "stages_completed": ["detect", "extract", "normalize", "enrich", "persist"],
  "error": null
}
```

---

## Error record

Embedded in registry, job, and intake records:

```json
{
  "code": "EXTRACT_EMPTY",
  "message": "PDF contained no extractable text",
  "stage": "extract",
  "retryable": false,
  "occurred_at": "2026-07-11T15:02:00Z",
  "details": {}
}
```

---

## Search and retrieval API shapes

These are **interface contracts**, not on-disk files.

### SearchQuery

```json
{
  "query": "how does intake validate file size",
  "mode": "hybrid",
  "top_k": 10,
  "filters": {
    "tags": ["architecture"],
    "format": ["pdf", "markdown"],
    "language": "en"
  },
  "include_parents": false
}
```

### SearchHit

```json
{
  "chunk_id": "chk_01JXYZCHUNK01",
  "doc_id": "doc_01JXYZABCDEF",
  "source_id": "src_01JXYZABCDEF",
  "score": 0.842,
  "scores": {
    "fusion": 0.842,
    "vector": 0.791,
    "keyword": 0.654
  },
  "title": "Architecture Notes",
  "heading_path": "architecture/ingestion",
  "excerpt": "Intake flow begins with validation...",
  "source_uri": "file:///Users/me/inbox/architecture-notes.pdf"
}
```

### RetrievalQuery

Extends `SearchQuery`:

```json
{
  "query": "how does intake validate file size",
  "mode": "hybrid",
  "top_k": 8,
  "retrieval_mode": "context",
  "max_tokens": 4000,
  "max_chunks_per_doc": 2,
  "expand_parents": true
}
```

### ContextBundle

```json
{
  "query": "how does intake validate file size",
  "chunks": [
    {
      "chunk_id": "chk_01JXYZCHUNK01",
      "doc_id": "doc_01JXYZABCDEF",
      "text": "Document: Architecture Notes > architecture/ingestion\n\nIntake flow begins with...",
      "score": 0.842,
      "heading_path": "architecture/ingestion",
      "source_uri": "file:///Users/me/inbox/architecture-notes.pdf"
    }
  ],
  "citations": [
    {
      "cite_key": "[1]",
      "chunk_id": "chk_01JXYZCHUNK01",
      "title": "Architecture Notes",
      "source_uri": "file:///Users/me/inbox/architecture-notes.pdf",
      "excerpt": "Intake flow begins with validation..."
    }
  ],
  "token_estimate": 512,
  "retrieval_metadata": {
    "search_mode": "hybrid",
    "rerank_enabled": false,
    "latency_ms": 45
  }
}
```

---

## Identifier conventions

| ID | Prefix | Example | Derivation |
|----|--------|---------|------------|
| `source_id` | `src_` | `src_01JXYZ...` | Assigned at intake (ULID recommended) |
| `doc_id` | `doc_` | `doc_01JXYZ...` | Usually one per source; `hash(source_id + boundary)` if split |
| `chunk_id` | `chk_` | `chk_01JXYZ...` | `hash(doc_id + heading_path + content_hash + chunk_index)` |
| `job_id` | `job_` | `job_01JXYZ...` | Assigned per job run |

Prefixes aid debugging in logs; they are not a substitute for schema validation.

---

## Related documents

- [metadata-schema.md](metadata-schema.md) — field semantics and filter rules
- [pipeline.md](pipeline.md) — when each record is written
- [docs/architecture/knowledge-engine.md](../docs/architecture/knowledge-engine.md) — architecture overview
- [docs/decisions/ADR-001-knowledge-engine.md](../docs/decisions/ADR-001-knowledge-engine.md)
