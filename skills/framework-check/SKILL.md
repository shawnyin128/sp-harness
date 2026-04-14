---
name: framework-check
description: |
  Health check for the sp-harness project framework. Verifies CLAUDE.md
  content format (not just section names), memory system, hooks, docs
  structure, features.json, and git conventions. Detects and migrates
  old framework formats. Auto-fixes by rewriting CLAUDE.md from template.
author: sp-harness
version: 2.0.0
---

# framework-check

Verify the current project follows the sp-harness framework. Detect old
formats and migrate. Auto-fix anything wrong.

---

## Step 1: Run Checks

### CLAUDE.md — Existence and Sections

- [ ] `CLAUDE.md` exists
- [ ] Has EXACTLY three sections: `First-Principles Standards`, `Context Management`, `Project Map`
- [ ] Does NOT have old-format sections: `Language`, `Problem`, `Motivation`, `Method`, `Example`, `Architecture`, `Memory, Todo and Checklist`
- [ ] Total length under 80 lines

### CLAUDE.md — Content Format

- [ ] First-Principles Standards has exactly 4 numbered rules (Clarify, Shortest path, Root causes, Output)
- [ ] Context Management mentions `.claude/todos.json`
- [ ] Context Management has "Session start protocol" listing: CLAUDE.md, .claude/features.json, .claude/sp-harness.json, .claude/todos.json, git log, git status
- [ ] Context Management does NOT mention `memory.md` (deprecated in v0.3.0)
- [ ] Context Management mentions `[module]: description` commit convention
- [ ] Project Map has `### Design Docs` subsection with docs/ tree
- [ ] Project Map has `### Codebase` subsection with directory tree
- [ ] Project Map does NOT use tables (no `|` table syntax)
- [ ] No extra sections beyond the three standard ones

### Documentation Structure

- [ ] `docs/design-docs/` exists
- [ ] `docs/plans/active/` exists
- [ ] `docs/plans/completed/` exists
- [ ] `docs/reports/` exists

### State Sources

- [ ] `.claude/todos.json` exists with valid schema (`{"todos": [...]}`)
- [ ] Every todo has required fields: id, description, category, status, created_at, linked_feature_ids, archived_feature_paths
- [ ] All `linked_feature_ids` reference existing entries in `.claude/features.json`
- [ ] `.claude/features.json` entries with `from_todo` reference existing todo ids
- [ ] No duplicate todo ids

### Legacy files (warn, do not auto-delete)

- [ ] `.claude/mem/memory.md` does NOT exist (deprecated in v0.3.0)
- [ ] `.claude/todos.json` does NOT exist (deprecated in v0.4.0; replaced by `.claude/todos.json`)
- [ ] `.claude/mem/checklist.md` does NOT exist (old format)
- [ ] If `.claude/mem/` exists but is empty, suggest removing it

### Agent State

- [ ] `.claude/agents/state/active/` directory exists (may be empty)
- [ ] `.claude/agents/state/archive/` directory exists (may be empty)

### Hooks

- [ ] `.claude/hooks/update-todo-reminder.sh` exists and is executable
- [ ] `.claude/settings.json` has Stop + UserPromptSubmit hooks

### Features (skip if no spec docs exist)

- [ ] `.claude/features.json` is valid JSON with `features` array
- [ ] Each feature has: id, category, priority, depends_on, description, steps, passes
- [ ] All IDs in `depends_on` arrays reference existing feature IDs (no dangling refs)
- [ ] No circular dependencies in `depends_on` chains

### Harness Config

- [ ] `.claude/sp-harness.json` exists
- [ ] Has `dev_mode` field (`"three-agent"` or `"single-agent"`)
- [ ] Has `last_hygiene_at_completed` field (number)

### Project-level Agents

- [ ] `.claude/agents/sp-feedback.md` exists (required regardless of dev_mode)
- [ ] If `dev_mode` is `"three-agent"`: `.claude/agents/sp-planner.md`, `sp-generator.md`, `sp-evaluator.md` all exist
- [ ] No plugin-level `agents/sp-planner.md`, `sp-generator.md`, `sp-evaluator.md` in plugin source (legacy — all dev agents are project-level now)

### Git Conventions

- [ ] Last 10 commits follow `[module]: description` format (warn only)

---

## Step 2: Report

```
Framework Health Check
======================

CLAUDE.md Structure
  ✓/✗ each check above

CLAUDE.md Content
  ✓/✗ each check above

Documentation / Memory / Hooks / Features / Git
  ✓/✗ each check above

Result: X/Y passed. Z items need fixing.
```

---

## Step 3: Auto-Fix

### CLAUDE.md missing entirely
→ Invoke `init-project` skill.

### CLAUDE.md has old format (Language/Problem/Architecture/table-style map)
→ **Rewrite CLAUDE.md from scratch using init-project template.**

This is the critical fix. Do NOT try to patch the old format. Instead:
1. Read the old CLAUDE.md to extract project name only
2. Run init-project's scan logic (Step 1) to get docs tree and codebase tree
3. Generate a new CLAUDE.md using the EXACT init-project template
4. Write the new CLAUDE.md, replacing the old one entirely
5. Do NOT carry over Language preferences, Problem/Motivation sections,
   or any other old-format content. Only the project name transfers.

The old format cannot be incrementally fixed — it has wrong sections,
wrong structure, and wrong content. A clean rewrite is the only reliable fix.

### Documentation structure missing
→ Create missing directories.

### Legacy memory.md present
→ memory.md was deprecated in v0.3.0. Do NOT auto-migrate or delete.
Print the file and suggest:
- Design decisions → move to appropriate `docs/design-docs/` file
- Ideas / directional thoughts → add to `.claude/todos.json` via manage-todos
- Recurring patterns → agent-memory accumulates naturally
→ User deletes memory.md after migration.

### Legacy todo.md present
→ todo.md was replaced by `.claude/todos.json` in v0.4.0. Do NOT auto-migrate.
Print the file and suggest:
- Markdown todos that represent ideas → add as new todos via manage-todos
- Markdown todos that represent session-level notes → inspect git status;
  if stale, discard
→ User deletes todo.md after migration.

### Missing .claude/todos.json
→ Create with `{"todos": []}` (empty backlog).

### Legacy checklist.md present
→ Delete it (old format, no migration needed).

### Hooks missing
→ Create hook script + configure settings.json (same as init-project).

### Features.json invalid
→ Report errors. Do not auto-create.

### sp-harness.json missing or incomplete
→ Create with defaults: `{"dev_mode": "three-agent", "last_hygiene_at_completed": 0}`
→ If exists but missing fields, add defaults for missing fields only.

### Project-level agents missing
→ Read templates from `${CLAUDE_PLUGIN_ROOT}/agent-templates/{name}.md`, fill
  `{PROJECT_NAME}` and `{PROJECT_CONTEXT}`, write to `.claude/agents/{name}.md`.
→ Always generate `sp-feedback.md`.
→ If `dev_mode` is three-agent, also generate sp-planner, sp-generator, sp-evaluator.

### Git conventions
→ Warn only. Do not rewrite history.

---

## Step 4: Re-check

Re-run ALL checks after fixes. Report final result.

If any still fail, report and stop.

---

## Step 5: Commit

Commit:
```
[framework]: migrate to new framework format
```

---

## Rules

1. Old-format CLAUDE.md = full rewrite. Only project name transfers.
2. Delete checklist.md if found (old format)
3. Do not create features.json — that is brainstorming's job
4. Idempotent — running twice produces no changes if already correct
