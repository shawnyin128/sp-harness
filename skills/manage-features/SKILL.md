---
name: manage-features
description: |
  CRUD + selection algorithm for .claude/features.json (feature list).
  All operations via bundled Python scripts — do NOT parse or write the
  JSON file directly. Invoked by feature-tracker (next/mark-passing),
  brainstorming (add per extracted feature), sp-feedback/feedback skill
  (add for fix_feature), and framework-check (validate).
user-invocable: false
---

# manage-features

Manage `.claude/features.json` — the project's decided requirements list.
Each feature has id, category, priority, depends_on, from_todo, description,
steps, passes.

## Why scripts, not direct file access

Two bundled Python scripts:
- `${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py` — read ops
- `${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/mutate.py` — write ops

**Do NOT read or write `.claude/features.json` directly.** The scripts
encapsulate:
- Topological + priority selection algorithm (`next`)
- Dangling-reference validation
- Circular dependency detection
- Schema enforcement

Agents that hand-implement the selection algorithm drift. The script is
deterministic and tested.

## Data model

```json
{
  "features": [
    {
      "id": "kebab-case-unique",
      "category": "functional | ui | infrastructure | testing",
      "priority": "high | medium | low",
      "depends_on": ["other-feature-id"],
      "from_todo": "todo-id or null",
      "description": "One-line description",
      "steps": ["Implementation step 1", "step 2"],
      "passes": false
    }
  ]
}
```

## Operations (query.py)

### list
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" list \
  [--passes=true|false|all] [--format=json|table]
```

### get
```bash
python3 "..." query.py get <id> [--format=json|table]
```

### next — THE selection algorithm
```bash
python3 "..." query.py next [--format=json|table]
```
Returns the feature feature-tracker should pick next:
1. Filter `passes: false`
2. Filter all `depends_on` satisfied (recursively all passing)
3. Sort by priority (high→medium→low)
4. Array order tiebreaker
5. Return first

Exit behavior:
- Normal feature returned → exit 0
- `{"all_done": true}` → exit 0 (feature-tracker moves to sp-feedback)
- `{"deadlock": true, "blocked_features": [...]}` → exit 1 (feature-tracker stops and reports to user)

### deps
```bash
python3 "..." query.py deps <id>
```
Shows each dep and whether it's satisfied. Useful for deadlock explanation.

### stats
```bash
python3 "..." query.py stats
```
Returns `{total, passed, remaining, remaining_by_priority}`.

### validate
```bash
python3 "..." query.py validate
```
Checks: duplicate ids, dangling depends_on refs, circular dependencies,
required fields. Exit 1 if errors.

## Operations (mutate.py)

### add
```bash
python3 "..." mutate.py add \
  --id=kebab-case \
  --category=functional|ui|infrastructure|testing \
  --priority=high|medium|low \
  --description="One-line description" \
  --steps="step 1;;step 2;;step 3" \
  [--depends-on=id1,id2] \
  [--from-todo=todo-id]
```
Steps separated by `;;` (double semicolon — `;` too common in shell).
Validates category/priority, depends_on existence, no cycles, unique id.
from_todo validated against `.claude/todos.json` if present.

### mark-passing
```bash
python3 "..." mutate.py mark-passing <id>
```
Sets `passes: true`. Idempotent.

### update
```bash
python3 "..." mutate.py update <id> \
  [--description=...] [--priority=...] [--steps=...] \
  [--depends-on=...]
```
Cannot change id, category, from_todo, passes (use dedicated ops for passes).
depends_on update re-validates for cycles.

## Invocation examples

**feature-tracker Step 3 (pick next):**
```bash
python3 "..." query.py next --format=table
```
Prints formatted feature for user confirmation. Exit 1 means deadlock.
Exit 0 with `{"all_done": true}` means move to sp-feedback.

**feature-tracker Step 5 (on PASS):**
```bash
python3 "..." mutate.py mark-passing <feature-id>
```

**brainstorming Feature List step:**
For each feature extracted:
```bash
python3 "..." mutate.py add --id=... --category=... --priority=... \
  --description=... --steps=... [--depends-on=...] --from-todo=<id>
```

**feedback skill (fix_feature):**
```bash
python3 "..." mutate.py add --id=... --category=... --priority=... \
  --description="<from finding>" --steps="<from suggestion>" \
  [--from-todo=null]
```
(from_todo can be omitted — fix features don't need todo origin)

**framework-check:**
```bash
python3 "..." query.py validate
```
Exit 1 with errors → framework-check reports integrity issues.

## Rules

1. NEVER read or write `.claude/features.json` directly. Always via scripts.
2. The selection algorithm lives ONLY in `query.py next`. Do not reimplement it.
3. Scripts exit non-zero on validation errors — check exit codes.
4. `${CLAUDE_PLUGIN_ROOT}` resolves to the plugin install path; use it as-is.
5. Output is JSON except formatted tables (`list` default, `next --format=table`, `get --format=table`).

## Python requirement

Scripts use Python 3 stdlib only. Python 3.7+.
