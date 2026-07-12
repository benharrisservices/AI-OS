# Workflows

Executable daily workflows for AI-OS. Each workflow accepts JSON input and runs a sequence of agent tools.

## Running a workflow

```bash
# List available workflows
ai-os workflow list

# Run with example input
ai-os workflow run morning-briefing --input-file config/workflows/examples/morning-briefing.json

# Run with inline JSON
ai-os workflow run daily-review --input '{"focus_areas": ["work"], "period": "today"}'
```

## First-party workflows

| Workflow | Purpose | Example input |
|----------|---------|---------------|
| `morning-briefing` | Daily morning context and priorities | `examples/morning-briefing.json` |
| `daily-review` | End-of-day reflection | `examples/daily-review.json` |
| `weekly-review` | Weekly retrospective | `examples/weekly-review.json` |
| `research-pipeline` | Deep research on a topic | `examples/research-pipeline.json` |
| `meeting-preparation` | Prep notes for upcoming meetings | `examples/meeting-preparation.json` |
| `travel-planning` | Trip planning and checklist | `examples/travel-planning.json` |
| `repo-health` | Repository health check | `examples/repo-health.json` |
| `knowledge-digest` | Summarise recent knowledge | `examples/knowledge-digest.json` |

## Input variables

Workflow steps use `{{input.field}}` for user input and `{{steps.step_id.field}}` for step outputs.
Use realistic defaults from the `examples/` directory when running manually.
