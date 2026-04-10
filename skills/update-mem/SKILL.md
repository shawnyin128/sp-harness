---
name: update-mem
description: |
  Update .claude/mem/ after non-trivial tasks. memory.md is a state snapshot
  (not a log). todo.md tracks open problems. Use when: design decision made,
  bug root cause found, assumption proven wrong, or todo item changed.
author: sp-harness
version: 2.1.0
---

# update-mem

Update `.claude/mem/memory.md` and `.claude/mem/todo.md` after non-trivial tasks.

Skip for trivial changes (typos, formatting, single-line edits).

---

## memory.md

State snapshot. Rewrite in place each update. Never append. Under 40 lines.

### Structure (EXACT — do not add or rename sections)

```markdown
# Project Memory

## Current State
{1-3 sentences, ~50 words max. What was done, what is in progress, what is blocked.}

## Key Decisions
- {decision} — {reason}

## Findings
- {finding relevant to future work}
```

### Rules

- **Current State**: rewrite entirely each time. Answer: "What does a new agent need to continue?"
- **Key Decisions**: add, update, or remove. Always keep the "why".
- **Findings**: add or remove. Drop findings that won't affect next steps.
- **Over 40 lines**: merge related decisions, drop stale findings. Never lose a decision's "why".
- **No extra sections**. Everything goes into one of the three above.

---

## todo.md

```markdown
# Todo

- [ ] {open problem}
- [x] {resolved} — {one-line resolution}
```

- Add new problems as discovered
- Mark resolved with `[x]` + brief resolution
- Keep max 5 resolved items; remove older ones unless resolution is a useful reference
- Never remove open `[ ]` items without resolving them
