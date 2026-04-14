---
name: manage-todos
description: |
  CRUD + state transitions for .claude/todos.json (idea backlog).
  Invoked by main session (user "add a todo..." requests) and by other skills
  (brainstorming, feature-tracker, sp-feedback) to update todo state.
  Not for direct user /slash invocation — main session calls on behalf of user.
user-invocable: false
---

# manage-todos

Manage `.claude/todos.json` — the project's idea backlog. Each todo is a
high-level idea/direction that needs brainstorming to scope into concrete
features. This skill handles CRUD and state transitions only; it does NOT
decide whether an idea is worth pursuing.

## Data model

`.claude/todos.json`:

```json
{
  "todos": [
    {
      "id": "kebab-case-unique",
      "description": "One-line description of the idea",
      "category": "feature-idea | tech-debt | investigation | ux-improvement",
      "status": "pending | in_brainstorm | in_feature | done | dropped",
      "notes": "optional free-text context",
      "created_at": "ISO 8601 timestamp",
      "linked_feature_ids": [],
      "archived_feature_paths": []
    }
  ]
}
```

## Status state machine

```
  pending ─(brainstorming picks)→ in_brainstorm
    │                                 │
    │                                 ↓ (brainstorming produces features)
    │                             in_feature
    │                                 │
    │                                 ↓ (all linked features pass)
    └───────────────────────────→ done

  pending | in_brainstorm | in_feature → dropped  (user explicit)
```

## Operations

### 1. Add
**Inputs:** description (required), category, notes (optional).
**Behavior:**
- Generate unique kebab-case `id` from description (append number if collision).
- Set `status = "pending"`, `created_at = now()`, empty arrays for linked fields.
- Append to `todos` array. Write to disk.
**Returns:** the created todo's id.

### 2. List
**Inputs:** optional `status_filter` (default: pending + in_brainstorm + in_feature), optional `category_filter`.
**Behavior:** read `.claude/todos.json`, filter, return matching entries.
**Returns:** array of todos.

### 3. Get
**Inputs:** `id`.
**Returns:** the todo entry, or error if not found.

### 4. Mark in_brainstorm
**Inputs:** `id`.
**Behavior:** set `status = "in_brainstorm"`. Valid source states: pending, in_feature (re-brainstorm).
**Error** if todo is already `done` or `dropped`.

### 5. Link features
**Inputs:** `id`, `feature_ids[]`.
**Behavior:**
- Append feature_ids to `linked_feature_ids` (dedup).
- If status is `in_brainstorm`, transition to `in_feature`.
**Called by:** brainstorming after features extracted.

### 6. Check done
**Inputs:** `id`, current `.claude/features.json` contents.
**Behavior:**
- For each id in `linked_feature_ids`, find the feature in features.json.
- If ALL have `passes: true`:
  - Set `status = "done"`.
  - For each linked feature, set `archived_feature_paths` to `.claude/agents/state/archive/<feature-id>/`.
  - Return `{ "done": true }`.
- Otherwise return `{ "done": false, "remaining": [<feature-ids with passes:false>] }`.
**Called by:** feature-tracker Step 5 after each feature PASS.

### 7. Drop
**Inputs:** `id`, `reason` (required).
**Behavior:** set `status = "dropped"`. Append `reason` to `notes`.
**Error** if already `done`.

### 8. Update
**Inputs:** `id`, fields to update (description, category, notes).
**Behavior:** merge updates. Do NOT allow status / id / linked_feature_ids update via this op (use dedicated ops).

## Invocation examples

**From main session (user request):**
> User: "Add a todo: investigate whether we should add prompt caching."
> Main session: invokes `manage-todos` Add with description=investigate prompt caching, category=investigation.

**From brainstorming (Step 0):**
> brainstorming reads pending todos, offers user choice, on selection invokes
> `manage-todos` Mark in_brainstorm with the chosen id.

**From brainstorming (feature extraction):**
> After features.json updated with new entries carrying `from_todo: <id>`,
> brainstorming invokes `manage-todos` Link features.

**From feature-tracker (Step 5 PASS):**
> After marking a feature passes:true, if the feature has `from_todo`,
> invoke `manage-todos` Check done to see if the originating todo is complete.

**From sp-feedback (new_todo action):**
> feedback-actions.json contains new_todo items. main session / feedback skill
> invokes `manage-todos` Add for each approved new_todo.

## Rules

1. `id` must be unique. On collision, append `-1`, `-2`, etc.
2. State transitions must follow the state machine. Invalid transitions → error.
3. Schema is strict: unknown fields are rejected. Use Update for known fields only.
4. Always write atomically (read full file, mutate, write back). No partial updates.
5. Do NOT delete entries — use `dropped` status. Historical record matters.
6. `.claude/todos.json` absent? Create with `{"todos": []}` on first write.

## Schema validation

On every write:
- `id` unique within the file
- `status` ∈ enum
- `category` ∈ enum
- `linked_feature_ids` references must exist in `.claude/features.json` (warn if not)
- `created_at` is ISO 8601

Invalid → error, do not write.
