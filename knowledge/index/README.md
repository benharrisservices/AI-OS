# Knowledge — Index

Search and retrieval layer: embeddings, vector indexes, and lookup tables.

## Intended contents

- Local vector store files (Chroma, LanceDB, FAISS, etc.)
- Embedding caches and manifest files listing indexed document IDs

## Rules

- **Gitignored** — indexes are rebuilt from `../processed/`.
- Configure backend via `VECTOR_STORE` and related variables in `.env`.
- Never commit proprietary model weights; reference models by name/path in config.

## Related configuration

See `VECTOR_STORE_*`, `EMBEDDING_*`, and `KNOWLEDGE_INDEX_DIR` in [.env.example](../../.env.example).
