# Personal Workflow Templates

Ready-to-edit JSON inputs for daily workflows. Copy and customize — no personal information is hardcoded.

## Usage

```bash
# Edit the template first
$EDITOR config/personal/workflows/morning-briefing.json

# Run with your values
ai-os workflow run morning-briefing --input-file config/personal/workflows/morning-briefing.json
```

## Templates

| Workflow | Template | Typical cadence |
|----------|----------|-----------------|
| Morning Briefing | `morning-briefing.json` | Weekdays, before work |
| Daily Review | `daily-review.json` | End of day |
| Weekly Review | `weekly-review.json` | Friday or Sunday |
| Travel Planning | `travel-planning.json` | Before trips |
| Research Pipeline | `research-pipeline.json` | Ad hoc |
| Project Review | `project-review.json` | Weekly per active project |

## Path conventions

Outputs write to `./memory/` (gitignored):

| Directory | Contents |
|-----------|----------|
| `memory/briefings/` | Morning briefing outputs |
| `memory/reviews/` | Daily and weekly reviews |
| `memory/travel/` | Travel plans |
| `memory/research/` | Research briefs |
| `memory/projects/` | Project review reports |

Create directories on first run or via `./scripts/install.sh`.

## Automation (optional)

To schedule workflows, copy and edit automation templates:

```bash
cp config/personal/automations/morning-briefing.yaml.example config/automations/my-morning.yaml
# Edit cron schedule and input paths
ai-os automation list
```

See `config/automations/morning-briefing.yaml` for the production automation format.

## Placeholder variables

Templates use descriptive placeholders. Replace before running:

- `{{date}}` — resolved at runtime by the agent engine
- `{{destination_slug}}`, `{{topic_slug}}`, `{{project_slug}}` — derived from input fields

## Recommended daily routine

```bash
# Morning (manual or scheduled)
ai-os workflow run morning-briefing -f config/personal/workflows/morning-briefing.json

# Evening
ai-os workflow run daily-review -f config/personal/workflows/daily-review.json

# Weekly
ai-os workflow run weekly-review -f config/personal/workflows/weekly-review.json
```
