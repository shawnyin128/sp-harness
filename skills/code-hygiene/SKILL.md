---
name: code-hygiene
description: |
  Lightweight periodic cleanup. Scans recently changed files for drift,
  dead code, and small debts. Auto-fixes unambiguous issues, escalates
  ambiguous ones. Triggered by feature-tracker every 3 features.
author: sp-harness
version: 1.2.0
user-invocable: false
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
<!-- lint:disable=R7 -->
```output-template
Hygiene complete (N files): auto-fixed X, escalated Y, skipped Z
```

Write `.claude/agents/state/active/hygiene-result.json`:
```json
{"status": "complete", "auto_fixed": N, "escalated": N, "skipped": N, "next_action": "continue_step_5d_d"}
```

The `next_action` field is REQUIRED. It is the machine-readable half of
the return-of-control contract: it tells whatever orchestrator dispatched
this skill (typically feature-tracker) which step to resume on. Always
emit `"continue_step_5d_d"` when status is `"complete"` — do not omit,
do not abbreviate, do not localize.

Do NOT write this file if hygiene fails or is interrupted.

Recurring patterns are not your concern — leave them for sp-feedback (Mode A)
to detect from archived eval-reports and your hygiene-result.json history.

---

## Step 5: Return control to caller

After Step 4 emits the report and writes the state file with
`next_action`, this skill is finished — but the WORK is not. Hygiene was
dispatched from the middle of feature-tracker Step 5, and the caller
still has counter updates, the Feature Brief, and a loop-back to do.

To prevent the orchestrator from treating hygiene's commit + report as
the terminal step of the whole feature cycle, print this exact line as
the LAST output of this skill:

<!-- lint:disable=R7 -->
```output-template
CONTROL RETURNS TO feature-tracker Step 5d.d — orchestrator must continue, this skill is not the terminal step
```

Then stop. Do not summarize. Do not propose next features. Do not loop.
Do not commit anything else. The orchestrator (still in feature-tracker
Step 5d) reads this line + the `next_action` field and proceeds to 5d.d
counter update, then 5e Feature Brief, then loops back to Step 2.

This dual-signal contract (terminal sentinel + JSON `next_action`) is
the only thing fighting silent chain breaks at this interface — both
halves are required.

---

## Rules

1. Run tests after every auto-fix. Revert all if tests fail.
2. Only scan recently changed files. Never refactor out-of-scope code.
3. Ambiguous fix = escalate, never guess.
4. Keep runs fast (minutes, not hours).
5. Same issue appearing across runs → sp-feedback (Mode A) detects this pattern from history; you don't need to track it.
