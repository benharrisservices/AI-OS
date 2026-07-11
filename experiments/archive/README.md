# Experiments — Archive

Completed, abandoned, or superseded experiments kept for historical reference.

## Purpose

Preserves context on what was tried, what worked, and what was rejected — without leaving active sandboxes in the main experiments tree.

## When to archive

- Experiment reached a conclusion (success or failure)
- Approach was superseded by a newer experiment or core implementation
- Scope was merged into the main codebase per an ADR

## Archive README template

Each archived folder should retain or add:

```markdown
# Experiment: <name>
Status: archived
Dates: YYYY-MM-DD → YYYY-MM-DD
Outcome: succeeded | failed | superseded
Summary: One paragraph on results and next steps.
ADR: Link if promoted to core.
```

## Rules

- Do not delete archived experiments without team agreement — they inform future ADRs.
- Strip secrets and large artifacts before archiving; keep documentation only if needed.
