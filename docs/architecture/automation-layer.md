# Automation Layer — Architecture

Phase 4 implementation. Automation answers **when should execution happen** — nothing more.

## Responsibility

Automation determines **when** workflows run. It does not:

- Retrieve knowledge (Knowledge Engine)
- Make decisions (Decision Engine)
- Execute workflow steps (Agent Runtime)
- Store experience (Memory System)

It schedules, triggers, and records execution history while delegating all work to `ExecutionEngine.run_workflow()`.

## Components

| Module | Role |
|--------|------|
| `models.py` | Automation, ScheduleSpec, TriggerSpec, Policy, ExecutionRecord |
| `scheduler.py` | One-time, recurring, cron, delayed next-run computation |
| `service.py` | `AutomationService` — public façade |
| `store.py` | Execution history and runtime state persistence |
| `loader.py` | YAML automation definitions from `config/automations/` |
| `cli.py` | `ai-os automation` commands |

## Trigger Types

| Trigger | Description |
|---------|-------------|
| `manual` | CLI `automation run` |
| `schedule` | Cron, recurring, one-time, or delayed via `tick()` |
| `filesystem` | File change matching watch path/pattern |
| `workflow_completion` | Fires when a source workflow completes |
| `webhook` | Token-validated external trigger |
| `startup` | Once per process on `on_startup()` |

## Policies

Each automation has a policy controlling:

- `max_retries` — re-attempts on failure
- `concurrency_limit` — max simultaneous runs
- `timeout_seconds` — workflow timeout budget
- `backoff_seconds` — delay between retries
- `pause_on_failure` — auto-pause after exhausting retries

## Integration

```
AutomationService
       │
       ▼
ExecutionEngine.run_workflow()  ←── only execution path
       │
       ▼ (on completion, via Protocol)
AutomationService.on_workflow_completed()
```

Agent Runtime notifies automation through `WorkflowCompletionNotifier` protocol — no circular imports.

## Configuration

```yaml
# config/automations/morning-review.yaml
automation_id: morning-review
workflow_id: daily-review
schedule:
  schedule_type: cron
  cron_expression: "0 9 * * *"
trigger:
  trigger_type: schedule
policy:
  max_retries: 2
  concurrency_limit: 1
```

## CLI

```bash
ai-os automation list
ai-os automation run morning-review
ai-os automation enable morning-review
ai-os automation disable morning-review
ai-os automation history morning-review
ai-os automation schedule morning-review --cron "0 9 * * *"
```
