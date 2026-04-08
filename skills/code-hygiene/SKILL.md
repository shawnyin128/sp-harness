---
name: code-hygiene
description: |
  Lightweight periodic code cleanup during feature development. Scans recently
  changed files for code drift, bad patterns, and small debts. Fixes small
  issues directly, escalates large ones to the user. Triggered by feature-tracker
  every N features (default: 3). Like garbage collection — frequent small
  cleanups prevent debt accumulation.
author: superpowers
version: 1.0.0
---

# code-hygiene

Periodic lightweight cleanup of recently changed code. Prevents pattern drift
and technical debt accumulation during active feature development.

**Philosophy:** Technical debt is a high-interest loan. Frequent small repayments
beat painful lump-sum settlements. Agents copy whatever patterns exist in the
codebase — including bad ones. Catch drift early before it propagates.

---

## Step 1: Identify Scope

Only scan files changed since the last hygiene run. Use git:

```bash
# Files changed in last N commits (since last hygiene)
git diff --name-only HEAD~[N] HEAD -- '*.py' '*.ts' '*.js' '*.go' '*.rs' '*.java'
```

If this is the first hygiene run, scan files changed since the first feature
was marked `passes: true` in docs/features.json.

List the files. If more than ~20 files, prioritize by:
1. Files with the most changes (git diff --stat)
2. Files that are new (more likely to have drift)
3. Files in core/shared modules (drift here propagates faster)

---

## Step 2: Quick Scan

For each file, check these specific items. These are fast, mechanical checks.

### Pattern Drift
- **Duplicated code blocks** (>5 lines similar to code elsewhere in the project)
- **Inconsistent naming** (e.g., camelCase in a snake_case project, or mixed
  conventions within the same file)
- **Style inconsistency** with surrounding code (different error handling pattern,
  different import organization)

### Dead Weight
- **Unused imports** or requires
- **Commented-out code** (should be deleted, git has history)
- **Unused variables or functions** (no callers)
- **Debug leftovers** (console.log, print statements, TODO comments from implementation)

### Small Debts
- **Magic numbers/strings** that should be constants
- **Functions over ~50 lines** that could be split
- **Repeated error handling** that could be a shared utility
- **Overly complex conditions** that could be simplified or named

---

## Step 3: Triage and Act

Classify each finding:

### Auto-fix (do it now, no user confirmation needed)
- Remove unused imports
- Remove commented-out code
- Remove debug leftovers (console.log, print)
- Fix naming inconsistencies (match surrounding code)
- Extract obvious magic numbers to named constants

After auto-fixes, run tests to confirm nothing broke. If tests fail,
revert and escalate to user.

### Escalate (show to user, ask before acting)
- Duplicate code extraction (might change interfaces)
- Function decomposition (requires design judgment)
- Pattern changes that affect multiple files
- Anything where the "right" fix is ambiguous

Present escalation items concisely:
```
Code hygiene found 2 items needing your input:

1. [file.py:45] Duplicate validation logic also in [other.py:78]
   → Extract to shared util? Or keep separate?

2. [handler.ts] 85-line function doing auth + validation + response
   → Split into 3 functions? Affects interface.
```

### Skip (not worth fixing now)
- Style preferences that don't affect readability
- Minor naming issues in test files
- Patterns that are consistent within their module even if different from others

---

## Step 4: Commit and Report

Commit auto-fixes:
```
[hygiene]: periodic cleanup — remove dead code, fix naming, extract constants
```

Brief summary to user:
```
Code hygiene complete (scanned N files):
  Auto-fixed: X items (unused imports, debug leftovers, naming)
  Escalated: Y items (see above)
  Skipped: Z items (minor, not worth fixing now)
```

Update `.claude/mem/memory.md` if any significant patterns were found
(e.g., "drift toward inconsistent error handling — watch for this").

---

## Configuration

Feature-tracker triggers this skill based on a configurable interval.

**Default:** Every 3 features completed.

To change, the user can specify when feature-tracker asks. The interval
is not stored in a config file — feature-tracker simply counts completed
features since last hygiene run.

---

## Rules

1. Never break existing tests. Run tests after every auto-fix batch.
2. Never refactor code that is not in the scan scope (recently changed files only)
3. Auto-fix only when the fix is unambiguous. When in doubt, escalate.
4. Keep hygiene runs fast — this should take minutes, not an hour.
5. Do not use this as an opportunity to rewrite or redesign. Only clean.
6. If the same issue keeps appearing across hygiene runs, note it in memory.md
   as a recurring pattern — this signals a systemic problem for system-feedback.
