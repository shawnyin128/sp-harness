---
name: feature-tracker
description: |
  Incremental feature development orchestrator. Reads docs/features.json,
  picks the highest-priority unfinished feature, and drives it through
  three-agent-development (Planner → Generator → Evaluator). Loops
  automatically: after each feature completes, picks the next one.
  Use when starting or resuming feature development.
author: sp-harness
version: 2.2.0
---

# feature-tracker

Orchestrate incremental development by working through features one at a time.

<EXTREMELY-IMPORTANT>
Every feature follows the SAME path: Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → back to Step 2.
This is a LOOP. After completing a feature, you MUST return to Step 2 and pick the next one.
You do NOT stop after one feature unless ALL features pass or the user tells you to stop.
</EXTREMELY-IMPORTANT>

---

## Step 1: Read context and validate hygiene counter

Read these in order:

1. `.claude/mem/memory.md` — current state, what was last worked on
2. `.claude/mem/todo.md` — open problems
3. `git log --oneline -20` — recent commits
4. `docs/features.json` — the feature list

If `docs/features.json` does not exist, inform the user and suggest running
brainstorming first to create one. STOP.

<HARD-GATE>
**Hygiene counter validation — do this IMMEDIATELY after reading features.json.
This step ONLY validates. It does NOT trigger cleanup.**

1. Check if `last_hygiene_at_completed` field exists in features.json
2. **If it does NOT exist:**
   - Add `"last_hygiene_at_completed": 0` to the top level
   - Write features.json to disk NOW
   - Report: "Added hygiene counter (was missing, set to 0)"
3. **If it exists:** read its value
4. Count features with `"passes": true` → `completed_count`
5. Compute `delta = completed_count - last_hygiene_at_completed`
6. **Validate:** `delta` MUST be < 3. If `delta >= 3`, something went wrong
   (Step 5 should have cleaned up). Report warning:
   "Hygiene counter invalid: delta={delta}, expected < 3. Will clean in Step 5."
</HARD-GATE>

---

## Step 2: Show progress summary

Present a brief status to the user:

```
Feature Progress: X/Y completed
Hygiene: last at {last_hygiene_at_completed}, next at {last_hygiene_at_completed + 3}

Remaining (by priority):
  [high]   feature-id — description
  [medium] feature-id — description
  [low]    feature-id — description
```

---

## Step 3: Pick next feature

Select the highest-priority feature where `passes: false`.

Priority order: high → medium → low. Within the same priority, use array order.

Present the selected feature to the user:

```
Next: [feature-id] — description
Priority: high
Steps:
  1. step one
  2. step two
  ...
```

Ask: "Ready to start this feature, or do you want to pick a different one?"

Wait for user confirmation before proceeding.

---

## Step 4: Invoke three-agent-development

Invoke `sp-harness:three-agent-development` with the selected feature.

This skill will:
1. Dispatch Planner → produces task-plan.json + eval-plan.json
2. **Print plan summary table to you and wait for your confirmation**
3. Dispatch Generator → executes via subagent-driven-development
4. Dispatch Evaluator → produces eval-report.json
5. Handle PASS/ITERATE/REJECT

You will see the plan and approve it before any code is written.

When three-agent-development returns PASS, feature-tracker proceeds to Step 5.
If REJECT, feature-tracker stops and reports to user.

---

## Step 5: Update memory, commit, hygiene cleanup, LOOP BACK

1. Update `.claude/mem/memory.md` Current State to reflect completion.

<HARD-GATE>
**2. Commit feature completion — MANDATORY, do NOT skip:**
```
git add docs/features.json .claude/mem/memory.md
git commit -m "[features]: mark {feature-id} as complete"
```
This commit is how new sessions know which features are done via `git log`.
Without it, the session start protocol's git log step is useless.
</HARD-GATE>

<HARD-GATE>
**Hygiene cleanup — AUTOMATIC, do NOT ask the user for permission.**

2. Read `last_hygiene_at_completed` from features.json
3. Count features with `"passes": true` → `completed_count`
4. Compute `delta = completed_count - last_hygiene_at_completed`
5. **If delta >= 3:**
   a. Print: "Hygiene threshold reached (delta={delta}). Running code-hygiene now."
   b. Invoke `sp-harness:code-hygiene` IMMEDIATELY. Do NOT ask "should I run
      hygiene?" or "would you like me to clean up?". This is automatic. Just do it.
   c. Read `.claude/agents/state/hygiene-result.json`
   d. **If file exists AND `status` is `"complete"`:**
      - Set `last_hygiene_at_completed` to `completed_count` in features.json
      - Write features.json to disk
      - Delete `.claude/agents/state/hygiene-result.json`
      - Report: "Hygiene complete. Counter updated to {completed_count}."
   e. **If file missing OR status is NOT `"complete"`:**
      - Do NOT update the counter
      - Warn: "Hygiene did not complete. Counter not updated. Will retry next loop."
6. **If delta < 3:** continue
</HARD-GATE>

7. **Check if ALL features pass:**
   - **NO (features remain)** → GO BACK TO STEP 2 NOW.
   - **YES (all pass)** →
     ```
     All features complete. docs/features.json shows X/X passing.
     Invoking system-feedback for optimization review.
     ```
     Invoke **system-feedback** skill. This is the only exit from the loop.

---

## Rules

1. One feature per cycle — do not batch multiple features
2. Verification is handled by three-agent-development's Evaluator — do not
   mark passes: true without Evaluator PASS verdict
3. Never skip the user confirmation in Step 3
4. If a feature turns out to be too large during implementation, pause and
   split it into sub-features in features.json before continuing
5. If implementation reveals a new feature that is needed, add it to
   features.json with appropriate priority — do not scope-creep the current feature
6. Step 1 VALIDATES the hygiene counter (exists, value is sane).
   Step 5 TRIGGERS cleanup (invokes code-hygiene, updates counter).
   Never skip either step.
