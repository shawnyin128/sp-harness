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

### Short-term Memory (v0.4.3+)

- [ ] `.claude/memory.md` exists
- [ ] memory.md has `## Observations` and `## In-flight` sections
- [ ] memory.md is under 30 lines (warn if bloated — user should triage)

### Source overlap check (HARD RULE: each concern has one home)

For each entry in `.claude/memory.md` Observations:
- [ ] Does the entry's referenced file/module also appear in a pending `.claude/todos.json` entry? → warn: duplicate, triage
- [ ] Does it match a `.claude/features.json` fix_feature? → warn: duplicate, triage
- [ ] Does recent git log show the referenced file resolved? → warn: stale, triage

Report overlaps but do NOT auto-delete. Agent/user must triage.

### Legacy files (warn, do not auto-delete)

- [ ] `.claude/mem/memory.md` does NOT exist (old scope deprecated in v0.3.0, tightened scope reintroduced at root in v0.4.3)
- [ ] `.claude/mem/todo.md` does NOT exist (deprecated in v0.4.0; replaced by `.claude/todos.json`)
- [ ] `.claude/mem/checklist.md` does NOT exist (old format)
- [ ] If `.claude/mem/` exists but is empty, suggest removing it

### Agent State

- [ ] `.claude/agents/state/active/` directory exists (may be empty)
- [ ] `.claude/agents/state/archive/` directory exists (may be empty)

### Hooks

- [ ] `.claude/hooks/update-todo-reminder.sh` exists and is executable
- [ ] `.claude/settings.json` has Stop + UserPromptSubmit hooks

### Features (skip if no spec docs exist)

Run the validator script:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" validate
```

The script checks: valid JSON, unique ids, required fields, dangling
depends_on refs, circular dependencies, dangling supersedes refs, no
self-supersession. Exit 1 with errors listed in JSON output if any found.

**Supersession archive integrity:**
- [ ] For each feature with non-empty `supersedes` and `passes=true`,
      `.claude/agents/state/archive/<feature-id>/supersession.json` exists
      and is valid JSON. Missing → warn, the feature completed without
      cleanup audit trail.

### Harness Config

- [ ] `.claude/sp-harness.json` exists
- [ ] Has `dev_mode` field (`"three-agent"` or `"single-agent"`)
- [ ] Has `last_hygiene_at_completed` field (number)
- [ ] Has `external_codebase` field (boolean)
- [ ] If `external_codebase: true`, `.claude/codebase-context.md` exists
- [ ] If `external_codebase: false` (or absent), `.claude/codebase-context.md` should NOT exist (warn if found — flag mismatch)

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

### Legacy .claude/mem/memory.md (old scope) present
→ Old memory.md had Current State / Key Decisions / Findings (deprecated v0.3.0).
The new memory.md (v0.4.3+) lives at `.claude/memory.md` with tighter scope
(short-term pre-triage observations only). Print old content, suggest:
- Design decisions → `docs/design-docs/`
- Decided ideas → `.claude/todos.json` via manage-todos
- Decided fixes → `.claude/features.json` via manage-features (fix_feature)
- Recurring patterns → agent-memory accumulates via sp-feedback routing
→ User deletes old file after migration. Old location is `.claude/mem/`.

### Legacy .claude/mem/todo.md present
→ Replaced by `.claude/todos.json` in v0.4.0. Print and suggest migrating
ideas via manage-todos. User deletes after migration.

### Missing .claude/todos.json
→ Create with `{"todos": []}` (empty backlog).

### Missing .claude/memory.md (v0.4.3+)
→ Create with the init-project template (scope comment + empty sections).

### Source overlap detected
→ Entry in memory.md duplicates content in todos.json or features.json.
Print overlapping pair. Ask user to decide which is authoritative and
remove the other.

### Legacy checklist.md present
→ Delete it (old format, no migration needed).

### Hooks missing
→ Create hook script + configure settings.json (same as init-project).

### Features.json invalid
→ Report errors. Do not auto-create.

### sp-harness.json missing or incomplete
→ Create with defaults: `{"dev_mode": "three-agent", "last_hygiene_at_completed": 0, "external_codebase": false}`
→ If exists but missing fields, add defaults for missing fields only.
→ If `external_codebase: true` but `codebase-context.md` missing, suggest re-running init-project to scan and save it.

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
