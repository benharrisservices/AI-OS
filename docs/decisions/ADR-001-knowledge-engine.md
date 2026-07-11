# ADR-001. Knowledge Engine Architecture

Date: 2026-07-11  
Status: accepted

## Context

AI-OS Phase 0 established repository structure: `knowledge/raw/` → `knowledge/processed/` → `knowledge/index/`, with environment variables for embeddings and vector stores documented in `.env.example`. Phase 1 must define how knowledge ingestion, indexing, and retrieval work before any implementation begins.

We need a design that:

- Supports Markdown, PDF, TXT, DOCX, HTML, and URLs
- Runs fully on a local machine without cloud services
- Can adopt cloud embedding APIs and hosted vector stores without redesign
- Produces auditable, citeable chunks for future RAG and decision-engine integration
- Handles incremental updates without full re-indexing on every change

## Decision

We adopt a **staged filesystem pipeline** with **canonical Markdown intermediates**, **hierarchical structure-aware chunking**, **hybrid search (vector + keyword)**, and **pluggable embedding and vector-store backends** behind fixed interfaces.

### 1. Three-stage filesystem pipeline

| Stage | Path | Role |
|-------|------|------|
| Raw | `knowledge/raw/` | Immutable snapshots of sources |
| Processed | `knowledge/processed/` | Normalized markdown, JSONL manifests, chunks |
| Index | `knowledge/index/` | Embeddings cache, vector store, keyword index, manifests |

**Rationale:** Filesystem stages are debuggable, align with the existing repo layout, and work offline. They double as the integration contract for future object-storage sync without changing processing logic.

### 2. Canonical intermediate format: Markdown with YAML front matter

All extractors (PDF, DOCX, HTML, URL, TXT) normalize to Markdown. Structured metadata lives in front matter; body text is chunkable Markdown.

**Rationale:** One chunking and metadata path for all formats. Markdown is human-readable and matches how operators already write notes.

**Trade-off:** Some layout-heavy PDFs lose visual fidelity. We accept this for a text-first knowledge system; degraded extractions are flagged in metadata.

### 3. Stable, content-addressed identifiers

- `source_id` — assigned at intake; stable across renames if fingerprint matches
- `doc_id` — derived from `source_id` and document boundary (usually 1:1)
- `chunk_id` — hash of `doc_id`, heading path, and content hash

**Rationale:** Idempotent pipelines. Unchanged content skips re-embedding and re-indexing.

### 4. Hierarchical chunking (parent + child)

- **Parent chunks** align to heading sections (target ≤ 2,048 tokens)
- **Child chunks** split parents for embedding (default 512 tokens, 64 overlap)

**Rationale:** Child chunks improve retrieval precision; parent expansion improves RAG context coherence. This is a well-understood pattern that avoids both tiny fragments and oversized embed units.

**Alternatives rejected:**

- *Fixed-size-only chunking* — ignores document structure; splits code and lists awkwardly
- *Semantic chunking via LLM* — expensive, non-deterministic, poor fit for local-first defaults

### 5. Hybrid search with reciprocal rank fusion (RRF)

Semantic (vector) and lexical (BM25) searches run in parallel; results merge via RRF. Optional reranking is feature-flagged off by default.

**Rationale:** Personal knowledge bases mix prose with identifiers, config keys, and rare terms. Hybrid search covers both without labeled training data.

**Alternatives rejected:**

- *Vector-only* — misses exact tokens
- *Keyword-only* — misses paraphrases
- *Learned fusion weights* — overkill for Phase 1; may revisit in experiments

### 6. Pluggable backends via environment configuration

| Concern | Default (local-first) | Cloud option |
|---------|----------------------|--------------|
| Embeddings | `ollama` / `local` | `openai`, etc. |
| Vector store | `local` | `pinecone`, `qdrant`, `pgvector` |
| Keyword index | On-disk BM25 | Co-located with vector store |

**Rationale:** Matches `.env.example` and the “local-first, cloud-optional” principle in `system-overview.md`. Interfaces (`EmbeddingProvider`, `VectorStore`) hide provider SDKs.

### 7. JSONL as the processed interchange format

`document.jsonl`, `chunks.jsonl`, and `embeddings.jsonl` are append-friendly, streamable, and line-oriented for partial reprocessing.

**Rationale:** Easier to debug than a single monolithic JSON file; works with standard Unix tooling; scales to personal corpora without a database requirement.

### 8. Retrieval contract: ContextBundle with citations

Retrieval returns a `ContextBundle` — ranked chunks, token estimate, and numbered citations — not a raw prompt string. The decision engine owns prompt assembly.

**Rationale:** Separates knowledge retrieval from prompt engineering. Citations are mandatory for auditability.

### 9. Incremental indexing via source registry and fingerprints

Each source has a content fingerprint (hash of raw bytes or normalized text). Changed fingerprints trigger reprocess; removed sources tombstone and delete index entries.

**Rationale:** Avoids full rebuilds when one file changes.

### 10. Format support scope for Phase 1

| Supported | Notes |
|-----------|-------|
| Markdown, TXT, HTML, URL | Native text pipelines |
| DOCX | OOXML only |
| PDF | Text-based extraction; OCR out of scope for Phase 1 |

Legacy `.doc`, password-protected files, and scanned PDFs without OCR are explicitly rejected with error codes.

## Consequences

### Positive

- Clear separation between ingestion, processing, indexing, search, and retrieval
- Operators can inspect every stage on disk
- Local-only operation is the default path
- Cloud services are configuration swaps, not architectural forks
- RAG integration in Phase 3–4 has a stable `ContextBundle` contract
- ADRs and schemas document decisions before code accretes

### Negative

- Filesystem pipeline may need object-storage indirection for very large raw corpora
- Markdown normalization loses rich layout from some PDFs and HTML pages
- Maintaining two chunk levels (parent/child) adds storage and indexing complexity
- Hybrid search requires operating two indexes (vector + keyword)
- Embedding model changes force re-embedding and index rebuild

### Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Embedding dimension mismatch after model change | Index manifest validates model + dimensions at startup |
| Disk growth from caches | Document retention policy; gitignore; optional S3 for raw |
| URL content drift | Store fetch snapshot in raw; record `fetched_at` and `final_url` |
| Extractor quality variance | `quality: degraded` metadata; operator can re-ingest after OCR tools land |

## Alternatives considered

### Single SQLite database for all stages

**Rejected.** Collapses debuggability and couples backup/restore to one file. A future SQLite *catalog* for the source registry is still possible without replacing filesystem artifacts.

### GraphRAG / knowledge graphs as primary index

**Rejected for Phase 1.** High complexity and cost for a personal corpus. May experiment in `experiments/` later.

### Embed at chunk time during preprocessing

**Rejected.** Couples CPU-heavy extraction with network-bound embedding. Separate embedding stage allows skip-on-cache and independent retries.

### Store only vectors; discard processed text

**Rejected.** Rebuilds and citation excerpts require retained chunk text in processed storage.

## References

- [docs/architecture/knowledge-engine.md](../architecture/knowledge-engine.md)
- [knowledge/pipeline.md](../../knowledge/pipeline.md)
- [knowledge/schema.md](../../knowledge/schema.md)
- [knowledge/metadata-schema.md](../../knowledge/metadata-schema.md)
- [docs/architecture/system-overview.md](../architecture/system-overview.md)

## Supersedes

None. This is the first ADR for AI-OS.
