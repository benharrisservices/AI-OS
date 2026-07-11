# Memory System — Architecture

Phase 3.5 implementation. Memory answers **what happened before** — distinct from Knowledge (what is true).

## Four Memory Types

| Type | Lifespan | Created by | Examples |
|------|----------|------------|----------|
| **Working** | Auto-expires (TTL) | Agent Runtime during execution | Active workflow state, temp variables |
| **Episodic** | Retained until archived | Workflow completion, explicit events | Executions, decisions, failures |
| **Semantic** | Permanent until archived | Explicit promotion only | Preferences, heuristics, lessons |
| **Procedural** | Version-controlled | Explicit creation | Workflow templates, SOPs |

## Promotion Chain

```
Working Memory
      │
      │  WORKFLOW_COMPLETION or MANUAL_APPROVAL
      ▼
Episodic Memory
      │
      │  MANUAL_APPROVAL only (--approve)
      ▼
Semantic Memory
```

Stages cannot be bypassed. Working memory cannot promote directly to semantic.

## Storage Layout

Runtime data (gitignored):

```
memory/
├── working/      # wmem_*.json
├── episodic/     # emem_*.json
├── semantic/     # smem_*.json
└── procedural/   # pmem_*.json
```

## Public Interface

All external consumers use `MemoryManager` (`ai_os.memory.manager`). See [layer-boundaries.md](layer-boundaries.md) for the full public API and façade rules.

## Agent Runtime Integration

1. **Task creation** — `retrieve_for_task()` loads `MemoryBundle` into `ExecutionContext.relevant_memories`
2. **Workflow start** — `sync_working()` captures active state
3. **Step execution** — Templates may reference `{{memory.summary}}` via bindings
4. **Workflow end** — `create_episodic()` records outcome; `promote_working_for_task()` archives working context

Knowledge retrieval remains a separate tool invocation (`knowledge_retrieve`).
