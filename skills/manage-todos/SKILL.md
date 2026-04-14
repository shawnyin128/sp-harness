---
name: manage-todos
description: |
  CRUD + state transitions for .claude/todos.json (idea backlog).
  All operations via bundled Python scripts — do NOT parse or write the
  JSON file directly. Invoked by main session and by other skills
  (brainstorming, feature-tracker, sp-feedback) to query or mutate todos.
user-invocable: false
---

# manage-todos

Manage `.claude/todos.json` — the project's idea backlog. Each todo is a
high-level idea/direction that needs brainstorming to scope into concrete
features.

## Why scripts, not direct file access

Two bundled Python scripts enforce schema and state machine:
- `${CLAUDE_PLUGIN_ROOT}/skills/manage-todos/scripts/query.py` — read ops
- `${CLAUDE_PLUGIN_ROOT}/skills/manage-todos/scripts/mutate.py` — write ops

**Do NOT read `.claude/todos.json` directly.** The scripts return only
what the caller needs (e.g., only pending todos). This:
- Saves tokens — caller never sees done/dropped history in-context
- Controls drift — state transitions validated, schema enforced
- Deterministic — same input always produces same output, no agent variation

## Data model

```json
{
  "todos": [
    {
      "id": "kebab-case-unique",
      "description": "One-line description of the idea",
      "category": "feature-idea | tech-debt | investigation | ux-improvement",
      "status": "pending | in_brainstorm | in_feature | done | dropped",
      "notes": "optional free text context",
      "created_at": "ISO 8601 UTC timestamp",
      "linked_feature_ids": [],
      "archived_feature_paths": []
    }
  ]
}
```

## State machine

```
  pending ──(mark-in-brainstorm)──→ in_brainstorm
                                         │
                                         ↓ (link-features auto-transitions)
                                    in_feature
                                         │
                                         ↓ (check-done when all linked pass)
                                       done

  pending | in_brainstorm | in_feature ──(drop)──→ dropped
```

Terminal states: `done`, `dropped`. No transitions from these.

## Operations (query.py)

All read operations. Output goes to stdout.

### list
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-todos/scripts/query.py" list \
  [--status=pending,in_brainstorm,in_feature] \
  [--category=feature-idea|tech-debt|investigation|ux-improvement] \
  [--format=json|table]
```
Default status excludes done/dropped. Default format is table.

### get
```bash
python3 "..." query.py get <id>
```
Prints the full todo entry as JSON. Exits 1 if not found.

### count
```bash
python3 "..." query.py count [--status=pending]
```
Prints just a number.

### pending (shortcut)
```bash
python3 "..." query.py pending
```
Same as `list --status=pending --format=table`.

## Operations (mutate.py)

All write operations. Validate schema + state machine. Return JSON result
to stdout. Exit non-zero on invalid operation.

### add
```bash
python3 "..." mutate.py add "Description here" \
  --category=feature-idea \
  [--notes="optional context"]
```
Creates pending todo with auto-generated slug id. Returns `{"created": "<id>"}`.

### mark-in-brainstorm
```bash
python3 "..." mutate.py mark-in-brainstorm <id>
```
Transitions to in_brainstorm. Fails if current state doesn't allow.

### link-features
```bash
python3 "..." mutate.py link-features <id> <feature_id> [<feature_id> ...]
```
Appends to `linked_feature_ids` (dedup). Auto-transitions in_brainstorm → in_feature.

### check-done
```bash
python3 "..." mutate.py check-done <id>
```
Reads `.claude/features.json`. If ALL linked features have `passes: true`:
transitions to done, sets archived_feature_paths, returns `{"done": true, ...}`.
Otherwise returns `{"done": false, "remaining": [...]}` (does not mutate).

### drop
```bash
python3 "..." mutate.py drop <id> --reason="why dropped"
```
Appends DROPPED note, transitions to dropped. Fails if already done.

### update
```bash
python3 "..." mutate.py update <id> \
  [--description="new"] \
  [--category=...] \
  [--notes="new"]
```
Updates mutable fields. Cannot change id, status, linked_feature_ids.

## Invocation examples

**Main session (user request):**
> User: "Add a todo to investigate prompt caching."
> Main session:
> ```bash
> python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-todos/scripts/mutate.py" add \
>   "Investigate prompt caching impact on latency" \
>   --category=investigation
> ```

**brainstorming Step 0:**
> ```bash
> python3 "..." query.py pending
> ```
> Present results to user. If user picks a todo:
> ```bash
> python3 "..." mutate.py mark-in-brainstorm <chosen-id>
> ```

**brainstorming post-feature-extraction:**
> After features.json is updated with `from_todo: <id>`:
> ```bash
> python3 "..." mutate.py link-features <todo-id> <feat-1> <feat-2> ...
> ```

**feature-tracker Step 5 (PASS):**
> If completed feature has `from_todo`:
> ```bash
> python3 "..." mutate.py check-done <todo-id>
> ```
> If done, include `.claude/todos.json` in the feature commit.

**sp-feedback (new_todo action):**
> For each approved `new_todo` finding:
> ```bash
> python3 "..." mutate.py add "<description>" \
>   --category=<mapped-from-root-cause> \
>   --notes="evidence: <evidence>; suggestion: <suggestion>"
> ```

## Rules

1. NEVER read or write `.claude/todos.json` directly. Always go through scripts.
2. Agent does not need to know the full schema — scripts enforce it.
3. Scripts exit non-zero on error — check exit codes.
4. `${CLAUDE_PLUGIN_ROOT}` resolves to the plugin install path; use it as-is.
5. Output is JSON except `list --format=table` and `pending` (both are tables).

## Python requirement

Scripts use Python 3 stdlib only (argparse, json, datetime, re, pathlib).
No third-party packages. Works on any system with Python 3.7+.
