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
- [ ] Context Management mentions `.claude/mem/` (NOT `.claude/mem/checklist.md`)
- [ ] Context Management has "Session start protocol" with 4 steps (memory.md, todo.md, git log, features.json)
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

### Memory System

- [ ] `.claude/mem/memory.md` exists with `## Current State`, `## Key Decisions`, `## Findings`
- [ ] `.claude/mem/memory.md` does NOT mention checklist.md
- [ ] `.claude/mem/todo.md` exists
- [ ] `.claude/mem/checklist.md` does NOT exist (old format — remove if found)

### Hooks

- [ ] `.claude/hooks/update-mem-reminder.sh` exists and is executable
- [ ] `.claude/settings.json` has Stop + UserPromptSubmit hooks

### Features (skip if no spec docs exist)

- [ ] `docs/features.json` is valid JSON with `features` array
- [ ] Each feature has: id, category, priority, description, steps, passes

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

### Memory wrong format
→ If memory.md lacks Current State / Key Decisions / Findings structure,
migrate existing content into those three sections.
→ If checklist.md exists, delete it (old format).

### Hooks missing
→ Create hook script + configure settings.json (same as init-project).

### Features.json invalid
→ Report errors. Do not auto-create.

### Git conventions
→ Warn only. Do not rewrite history.

---

## Step 4: Re-check

Re-run ALL checks after fixes. Report final result.

If any still fail, report and stop.

---

## Step 5: Update Memory + Commit

Update `.claude/mem/memory.md` Current State.

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
