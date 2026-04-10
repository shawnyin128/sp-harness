---
name: system-feedback
description: |
  System-level optimization review after all features complete. Analyzes
  performance, UX, code quality, architecture. File-level report.
  Triggered by feature-tracker when all features pass.
author: sp-harness
version: 1.1.0
---

# system-feedback

All features pass. Now find what's wrong underneath: performance, UX,
code quality, architecture.

<EXTREMELY-IMPORTANT>
Adversarial stance. Find problems the development process missed.
Fewer than 3 total issues across 4 dimensions = scan again harder.
Zero-issue dimensions must explain what was checked and why nothing found.
If you think "minor" or "good enough" — report it anyway.
</EXTREMELY-IMPORTANT>

---

## Step 1: Context

Read: `docs/features.json`, `.claude/mem/memory.md`, `CLAUDE.md`, spec docs,
`git log --oneline -30`. List all changed source files from git.

---

## Step 2: Fixed Checks

Report findings at file:function level.

### Performance
- [ ] Nested loops that could use dict/set lookup instead
- [ ] Same calculation repeated (cache/memoize candidate)
- [ ] DB/API calls inside loops (N+1)
- [ ] Sync I/O on hot paths where async available
- [ ] Oversized imports or unused dependencies
- [ ] Unbounded growing collections

### User Experience
- [ ] Error paths show raw exception instead of meaningful message
- [ ] Empty/zero-data states not handled
- [ ] Long operations without progress feedback
- [ ] Input validation missing or unclear error messages
- [ ] Boundary values unhandled (empty string, max length, concurrent access)

### Code Quality (cross-feature patterns code-hygiene missed)
- [ ] Duplicated blocks >5 lines across files (same threshold as code-hygiene, but cross-feature scope)
- [ ] Functions >50 lines or >3 nesting levels
- [ ] Naming inconsistency (camelCase/snake_case mix) across module boundaries
- [ ] Dead code from removed/changed features (not just per-file — cross-feature)
- [ ] Circular or unused dependencies

### Architecture
- [ ] File/module with multiple responsibilities
- [ ] Components leaking internals to each other
- [ ] Public APIs easy to misuse
- [ ] Implementation drifted from spec design

---

## Step 3: Deep Analysis

For each dimension, one question:
- **Performance**: If load doubles, what breaks first?
- **UX**: Walk primary flow end-to-end — where does user think or wait?
- **Code Quality**: Which file would you fear modifying? Why?
- **Architecture**: Is there a simpler way with fewer moving parts?

---

## Step 4: Report

Write `docs/reports/optimization-report.md`:

````markdown
# System Optimization Report

## Date: {FILL}
## Scope: {FILL}

## Summary
{1-3 sentences: health + priorities}

## Performance
- [{P1}] {file:function} — {issue} — {suggestion}
- Deep: {2-3 sentences}

## User Experience
- [{UX1}] {file:component} — {issue} — {suggestion}
- Deep: {2-3 sentences}

## Code Quality
- [{CQ1}] {file:function} — {issue} — {suggestion}
- Deep: {2-3 sentences}

## Architecture
- [{AR1}] {file/module} — {issue} — {suggestion}
- Deep: {2-3 sentences}

## Priority
1. {ID} {description}
2. {ID} {description}
3. {ID} {description}
````

---

## Step 5: Commit

Update memory.md. Commit: `[feedback]: system optimization report`

---

## Rules

1. Every issue: specific file + concrete suggestion (not "improve this")
2. Do not recommend changes that break tests or are out of scope
3. Report is advisory — does not trigger automatic changes
