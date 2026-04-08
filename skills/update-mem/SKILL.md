---
name: update-mem
description: |
  Update project memory files (.claude/mem/) after any non-trivial task.
  Maintains a structured state snapshot in memory.md so new sessions can
  recover context quickly. Use when: a design decision was made, an experiment
  produced results, a bug root cause was identified, or a todo item changed.
author: superpowers
version: 2.0.0
---

# update-mem

Update `.claude/mem/memory.md` and `.claude/mem/todo.md` after any non-trivial task.

The goal: any new agent (fresh session or post-clear) reads these two files
and understands the full project context in under 30 seconds.

---

## When to run

After any task where:
- A design decision was made
- An experiment produced a result that affects future work
- A bug root cause was identified
- An assumption was proven wrong
- A todo item was resolved or a new problem was found

Do NOT run for trivial tasks (typo fixes, formatting, single-line edits).

---

## memory.md — structured state snapshot

memory.md is NOT an append-only log. It is a living document that always
reflects the current state of the project. Read it, update it in place,
keep it tight.

### Required structure (EXACT — do not add, remove, or rename sections)

```markdown
# Project Memory

## Current State
{1-3 sentences: what was just done, what is in progress, what is blocked}

## Key Decisions
- {decision} — {reason}

## Findings
- {finding}
```

**Do NOT add extra sections** (no "Open Questions", no "Architecture Notes",
no "History"). Everything goes into one of the three sections above.

### Update rules

**Current State** — rewrite entirely each time. Not a log. Answer:
"What would a new agent need to know to continue this work?"

**Key Decisions** — add, update, or remove. Each entry: what + why.

**Findings** — add or remove. Drop findings no longer relevant to future work.

### Compression

Keep memory.md under ~40 lines. When it grows beyond that:
- Merge related decisions into one entry
- Drop findings that no longer affect future work
- Keep Current State to 1-3 sentences max
- Never lose a decision's "why" — that is the most valuable part

---

## todo.md — open problems and deferred tasks

### Required structure

```markdown
# Todo

- [ ] <open problem or task>
- [ ] <open problem or task>
- [x] <resolved> — <one-line resolution>
```

### Update rules

- Add new problems as they are discovered
- Mark resolved items with `[x]` and a brief resolution
- Remove resolved items once there are more than ~5 (keep only if the
  resolution itself is a useful reference)
- Never remove open `[ ]` items without resolving them

---

## Hard rules

1. memory.md must always be readable as a standalone context briefing
2. After updating, re-read both files and verify a new agent could understand
   the project state without any other context
3. Never let memory.md become a changelog — it is a state snapshot
4. Current State section must be updated on every non-trivial update
5. Do not update for trivial tasks
