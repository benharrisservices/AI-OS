# Knowledge Import Plan

Ordered plan for importing your existing information into AI-OS. Uses `ai-os import` with fingerprint-based duplicate detection — re-running imports is safe.

## Principles

1. **Import stable reference material first** — it improves every later workflow
2. **Tag by category** — enables filtered retrieval (`--tag business`, `--tag university`)
3. **Avoid importing the same content twice** — prefer one canonical source per topic
4. **Legal and sensitive docs last** — review tags and retention before importing

## Recommended import order

| Phase | Category | Priority | Rationale |
|-------|----------|----------|-----------|
| 1 | AI-OS repository | High | Daily development context; repo health workflows |
| 2 | Business projects | High | Core work context for briefings and reviews |
| 3 | Markdown notes | High | Lowest friction; immediate search value |
| 4 | Product designs | Medium | Supports research and project review |
| 5 | University | Medium | Semester-specific; tag by course/year |
| 6 | Exported chats | Medium | Valuable but noisy; import after core docs |
| 7 | PDFs | Medium | Slower to process; import in batches |
| 8 | Travel research | Low | Episodic; tag by trip |
| 9 | Personal documents | Low | Broad category; curate before bulk import |
| 10 | Legal documents | Low | Import selectively; tag `legal` + year |

---

## Phase 1 — AI-OS repository

**Goal:** Make AI-OS self-aware for development and repo health workflows.

```bash
# From AI-OS root — import docs and architecture (not node_modules or .venv)
ai-os import ./docs --type folder --tag ai-os --tag reference
ai-os import ./config/workflows/README.md --type text --tag ai-os
ai-os import ./docs/architecture --type folder --tag ai-os --tag architecture

# GitHub README as quick context
ai-os import your-username/AI-OS --type github --tag ai-os --tag github
```

**Skip:** `knowledge/processed/`, `knowledge/index/`, `.venv/`, `memory/`, `__pycache__/`

**Verify:** `ai-os search "layer boundaries"` → architecture docs appear

---

## Phase 2 — Business projects

**Goal:** Context for morning briefing, project review, and research pipeline.

```bash
# One project per import with distinct tags
ai-os import ~/Projects/client-alpha/docs --type folder --tag business --tag client-alpha
ai-os import ~/Projects/client-alpha/README.md --type text --tag business --tag client-alpha

# Git repos (clone + import supported files)
ai-os import https://github.com/your-org/project-repo --clone --tag business --tag project-name
```

**Structure tip:** Create a folder per client/project; import the folder, not the entire `~/Projects` tree.

---

## Phase 3 — Markdown notes

**Goal:** Personal knowledge base — notes, journals, thinking documents.

```bash
ai-os import ~/Notes --type folder --tag notes --tag personal
ai-os import ~/Obsidian/Vault --type folder --tag notes --tag obsidian
```

**Duplicate note:** If the same file exists in Obsidian and `~/Notes`, import only the canonical location.

---

## Phase 4 — Product designs

**Goal:** Design context for project review and research.

```bash
ai-os import ~/Designs/product-x --type folder --tag design --tag product-x
ai-os import ~/Designs/specs/feature-y.md --type markdown --tag design
```

**Formats:** `.md`, `.pdf`, `.docx` supported. Figma exports → export to PDF or markdown first.

---

## Phase 5 — University

**Goal:** Course materials and assignments for research workflows.

```bash
ai-os import ~/University/2026-Spring --type folder --tag university --tag 2026-spring
ai-os import ~/University/Course-CODE/syllabus.pdf --type pdf --tag university --tag course-code
```

**Tag convention:** `university`, `{year}-{semester}`, `{course-code}`

---

## Phase 6 — Exported chats

**Goal:** Preserve valuable AI conversations without polluting core knowledge.

```bash
# ChatGPT / Claude JSON exports
ai-os import ~/Exports/chatgpt-2026-01.json --type chats --tag chats --tag chatgpt
ai-os import ~/Exports/claude-project.json --type chats --tag chats --tag claude

# Plain text exports
ai-os import ~/Exports/conversation.txt --type chats --tag chats
```

**Tip:** Import chats **after** reference docs so retrieval prioritizes curated material.

---

## Phase 7 — PDFs

**Goal:** Reports, papers, manuals — batch import to avoid long runs.

```bash
# Single files
ai-os import ~/Documents/report-q1.pdf --type pdf --tag business --tag reports

# Folder batch (processes all supported formats)
ai-os import ~/Documents/PDFs --type folder --tag pdf-import
```

**Limit:** Default max file size 50 MB (`KNOWLEDGE_MAX_FILE_SIZE_MB`). Split large PDFs if needed.

---

## Phase 8 — Travel research

**Goal:** Trip-specific context for travel planning workflow.

```bash
ai-os import ~/Travel/tokyo-2026 --type folder --tag travel --tag tokyo-2026
ai-os import ~/Travel/flight-options.pdf --type pdf --tag travel --tag tokyo-2026
```

**Tip:** Tag by destination + year. Archive or skip after trip completes.

---

## Phase 9 — Personal documents

**Goal:** General personal reference (non-legal).

```bash
ai-os import ~/Documents/Personal --type folder --tag personal
```

**Curate first:** Remove duplicates, outdated files, and installers before importing.

---

## Phase 10 — Legal documents

**Goal:** Contracts, agreements — import selectively.

```bash
ai-os import ~/Documents/Legal/contract-2026.pdf --type pdf --tag legal --tag 2026
```

**Security:** Legal docs stay local (gitignored `knowledge/` paths). Never commit `.env` or raw legal files.

---

## Category → tag reference

| Category | Suggested tags | Import type |
|----------|----------------|-------------|
| Business projects | `business`, `{project-name}` | `folder`, `git` clone |
| AI-OS repository | `ai-os`, `reference`, `architecture` | `folder`, `github` |
| University | `university`, `{year-semester}`, `{course}` | `folder`, `pdf` |
| Personal documents | `personal` | `folder` |
| Product designs | `design`, `{product}` | `folder`, `pdf` |
| Travel research | `travel`, `{destination-year}` | `folder`, `pdf` |
| Legal documents | `legal`, `{year}` | `pdf` (selective) |
| PDFs | `{domain-tag}`, `pdf-import` | `pdf`, `folder` |
| Markdown notes | `notes`, `personal` | `folder` |
| Exported chats | `chats`, `{source}` | `chats` |

---

## Post-import checklist

```bash
ai-os status                    # document and chunk counts
ai-os search "your topic"       # spot-check retrieval
ai-os doctor                    # integrity check
ai-os backup                    # snapshot after large import
```

## Ongoing maintenance

| Cadence | Action |
|---------|--------|
| Daily | Drop new files in `knowledge/raw/inbox/` or run `ai-os watch --once` |
| Weekly | Import new chat exports and project docs |
| Monthly | `ai-os maintenance run` + backup |
| Per project | Import at project start; tag consistently |

## What not to import

- Passwords, API keys, credentials (use `.env` only)
- `node_modules/`, `.venv/`, build artifacts
- Duplicate copies of the same document
- Entire home directory (import curated folders)
- Binary media (images, video) — not supported by extractors
