# Layer Boundaries — AI-OS

This document defines the **approved dependency direction** between AI-OS layers and the rules future contributors must follow when extending the system.

## Layer Questions

| Layer | Question | Package |
|-------|----------|---------|
| Knowledge | What is true? | `ai_os.knowledge` |
| Memory | What happened before? | `ai_os.memory` |
| Decision | What should we do? | `ai_os.decision` |
| Agent Runtime | How do we execute? | `ai_os.agent` |
| Automation | When should execution happen? | `ai_os.automation` |

Knowledge stores **facts**. Memory stores **experience**. These must never be merged.

## Approved Dependency Graph

```
                    ┌──────────────┐
                    │  automation  │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │    agent     │
                    └──────┬───────┘
           ┌───────────────┼───────────────┐
           │               │               │
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐
    │  decision  │  │   memory   │
    └─────┬──────┘  └────────────┘
          │
          ▼
    ┌────────────┐
    │ knowledge  │
    └────────────┘
```

**Allowed imports:**

| From | May import |
|------|------------|
| `knowledge` | Standard library, third-party libs only |
| `decision` | `knowledge` (retrieval contracts) |
| `memory` | Standard library, third-party libs only |
| `agent` | `knowledge`, `decision`, `memory` **public APIs only** |
| `automation` | `agent` (`ExecutionEngine`) **public API only** |

**Forbidden:**

- `knowledge` → `decision`, `memory`, `agent`, or `automation`
- `memory` → `knowledge`, `decision`, `agent`, or `automation`
- `decision` → `memory`, `agent`, or `automation`
- `agent` → `automation` (notification uses Protocol, not import)
- Any circular import between layers
- Any consumer reaching into another layer's internal modules (`store.py`, `retrieval.py`, etc.)

## MemoryManager Façade

The Agent Runtime must interact with Memory **only** through `MemoryManager` in `ai_os.memory.manager`.

### Public API (approved for consumers)

| Method | Purpose |
|--------|---------|
| `create_working` | Short-lived execution context |
| `create_episodic` | Record historical events |
| `create_semantic` | Store promoted abstractions |
| `create_procedural` | Version-controlled procedures |
| `update` | Modify an existing record |
| `get` | Fetch by ID |
| `search` | Query memories |
| `retrieve_for_task` | Load relevant memories for Agent Runtime |
| `list_by_type` | List memories by tier |
| `list_all` | List all memories |
| `archive` | Archive a record |
| `expire_working` | Expire overdue working memories |
| `promote` | Staged promotion (Working → Episodic → Semantic) |
| `promote_working_to_episodic` | Promote a specific working record |
| `promote_working_for_task` | Promote working memory by task ID |
| `sync_working` | Create or update working memory for a task |

### Internal modules (not for external import)

| Module | Role |
|--------|------|
| `memory/store.py` | JSON persistence |
| `memory/retrieval.py` | Search and bundle assembly |
| `memory/promotion.py` | Promotion rule enforcement |

### Why the façade exists

1. **Encapsulation** — Persistence and retrieval strategies can change without touching Agent Runtime.
2. **Boundary enforcement** — Prevents hidden coupling between orchestration and storage.
3. **Testability** — Agent tests inject `MemoryManager` with isolated settings without mocking internals.
4. **Evolution** — Backends (file, SQLite, Redis) swap behind the manager without layer violations.

### Why Agent Runtime cannot access internals

The Agent Runtime orchestrates execution. If it imports `MemoryStore` or `MemoryRetrieval` directly:

- Promotion rules could be bypassed
- Storage format leaks into workflow logic
- Refactoring memory internals breaks the execution layer
- The dependency graph becomes ambiguous

**Correct:**

```python
from ai_os.memory.manager import MemoryManager

bundle = memory.retrieve_for_task(task_id=task.task_id, agent_id=agent_id)
memory.promote_working_for_task(task.task_id, policy=PromotionPolicy.WORKFLOW_COMPLETION)
```

**Incorrect:**

```python
from ai_os.memory.store import MemoryStore
from ai_os.memory.retrieval import MemoryRetrieval

memory.store.list_by_type(...)       # layer violation
memory.retrieval.retrieve_for_task(...)  # layer violation
```

## Agent Runtime Integration

Agent Runtime reaches Knowledge and Decision through **registered tools** (`knowledge_retrieve`, `decision_make`), not direct pipeline imports in orchestration code. Tool implementations are the sanctioned integration point.

Memory is injected at task creation via `MemoryManager.retrieve_for_task()` and written back through `create_episodic`, `sync_working`, and `promote_working_for_task`.

## AutomationService Façade

Automation interacts with execution **only** through `ExecutionEngine.run_workflow()`. Agent Runtime notifies automation of workflow completion via the `WorkflowCompletionNotifier` protocol — avoiding circular imports between `agent` and `automation` packages.

### Public API

| Method | Purpose |
|--------|---------|
| `list_automations` | List all automation definitions |
| `run` | Execute immediately |
| `enable` / `disable` / `pause` | Policy state |
| `schedule` | Configure cron, recurring, delayed, or one-time |
| `tick` | Process due scheduled automations |
| `history` | Execution history |
| `on_startup` | Fire startup triggers |
| `on_workflow_completed` | Fire workflow-completion triggers |
| `on_filesystem_event` | Fire filesystem triggers |
| `trigger_webhook` | Validate token and run |

## Extension Rules

1. **New memory backends** — Implement behind `MemoryStore`; expose only via `MemoryManager`.
2. **New agent capabilities** — Add tools to the tool registry; do not import Knowledge or Decision pipelines in `engine.py`.
3. **New decision strategies** — Register in `decision/strategies/`; consume Knowledge via `KnowledgeRetrieval` only.
4. **New knowledge extractors** — Register in `knowledge/extractors/`; no upstream dependencies.
5. **Cross-layer data** — Pass contracts (`ContextBundle`, `MemoryBundle`, `DecisionResult`), not internal store records.
6. **New automations** — YAML in `config/automations/`; execution only via `AutomationService` → `ExecutionEngine`.

## Verification

Run the dependency audit before merging boundary changes:

```bash
python3 -c "
import ast
from pathlib import Path

layers = ['knowledge', 'decision', 'memory', 'agent', 'automation']
ROOT = Path('src/ai_os')
for layer in layers:
    deps = set()
    for path in (ROOT / layer).rglob('*.py'):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                for other in layers:
                    if other != layer and node.module.startswith(f'ai_os.{other}'):
                        deps.add(node.module)
    print(f'{layer}: {sorted(deps)}')
"
```

Agent imports of `ai_os.memory.models` (contracts) and `ai_os.memory.manager` (façade) are approved. Agent imports of `ai_os.memory.store`, `ai_os.memory.retrieval`, or `ai_os.memory.promotion` are violations.
