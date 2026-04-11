---
name: code-hygiene
description: |
  Lightweight periodic cleanup. Scans recently changed files for drift,
  dead code, and small debts. Auto-fixes unambiguous issues, escalates
  ambiguous ones. Triggered by feature-tracker every 3 features.
author: sp-harness
version: 1.1.0
---

# code-hygiene

Scan recently changed code for drift and debt. Fix or escalate.

<EXTREMELY-IMPORTANT>
Your job is finding dirt, not confirming cleanliness. Agent code always
has drift. Zero issues on first pass = scan again harder. If you think
"minor, not worth fixing" — flag it anyway.
</EXTREMELY-IMPORTANT>

---

## Step 1: Scope

```bash
git diff --name-only HEAD~[N] HEAD -- '*.py' '*.ts' '*.js' '*.go' '*.rs' '*.java'
```

First run: scan files changed since first feature passed in features.json.

If >20 files, prioritize: most changed → new files → core/shared modules.

---

## Step 2: Scan

Check each file for:

**Pattern drift:**
- Duplicated blocks (>5 lines, >80% structural match with code elsewhere)
- Naming inconsistency (camelCase in snake_case project, mixed in same file)
- Style inconsistency with surrounding code

**Dead weight:**
- Unused imports/variables/functions
- Commented-out code (git has history)
- Debug leftovers (console.log, print, TODO from implementation)

**Small debts:**
- Magic numbers/strings → should be constants
- Functions >50 lines → should be split
- Repeated error handling → should be shared utility

---

## Step 3: Triage

**Auto-fix** (unambiguous, no user confirmation):
- Remove unused imports, commented-out code, debug leftovers
- Fix naming to match surrounding code
- Extract obvious magic numbers to constants

Run tests after auto-fixes. If tests fail, revert ALL auto-fixes and escalate.

**Escalate** (ambiguous, ask user):
- Duplicate extraction (changes interfaces)
- Function decomposition (design judgment needed)
- Multi-file pattern changes

Format: `[file:line] issue → suggested fix`

**Skip** (cosmetic, module-internal consistency): don't report.

---

## Step 4: Commit, Report, Signal

Commit: `[hygiene]: remove dead code, fix naming, extract constants`

Report:
```
Hygiene complete (N files): auto-fixed X, escalated Y, skipped Z
```

Write `.claude/agents/state/hygiene-result.json`:
```json
{"status": "complete", "auto_fixed": N, "escalated": N, "skipped": N}
```

Do NOT write this file if hygiene fails or is interrupted.

Update memory.md if recurring patterns found (signals systemic issue).

---

## Rules

1. Run tests after every auto-fix. Revert all if tests fail.
2. Only scan recently changed files. Never refactor out-of-scope code.
3. Ambiguous fix = escalate, never guess.
4. Keep runs fast (minutes, not hours).
5. Same issue appearing across runs → note in memory.md for system-feedback.
