# Knowledge — Raw

Unprocessed source material before normalization or chunking.

## Examples

- PDFs, markdown exports, HTML saves
- Meeting transcripts, chat exports
- API JSON dumps, CSV datasets
- Code repository snapshots (where licensed)

## Rules

- Content here is **gitignored** by default — keep large files local or in object storage.
- Do not store secrets or credentials in raw files.
- Prefer descriptive filenames: `2026-07-project-kickoff-transcript.md`.

## Next step

Ingestion jobs (future: `scripts/` or dedicated modules) move normalized output to `../processed/`.
