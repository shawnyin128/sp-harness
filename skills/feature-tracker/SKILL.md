---
name: feature-tracker
description: |
  Incremental feature development orchestrator. Reads .claude/features.json,
  picks the highest-priority unfinished feature, and drives it through
  the configured development mode (three-agent or single-agent). Loops
  automatically: after each feature completes, picks the next one.
  Use when starting or resuming feature development.
author: sp-harness
version: 3.0.0
---

# feature-tracker

Orchestrate incremental development by working through features one at a time.

<EXTREMELY-IMPORTANT>
Every feature follows the SAME path: Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → back to Step 2.
This is a LOOP. After completing a feature, you MUST return to Step 2 and pick the next one.
You do NOT stop after one feature unless ALL features pass or the user tells you to stop.
</EXTREMELY-IMPORTANT>

---

## Step 1: Read context, validate config, validate hygiene counter

Read these in order:

1. `.claude/features.json` — the feature list and status
2. `.claude/sp-harness.json` — harness configuration (dev_mode, hygiene counter)
3. `.claude/todos.json` — idea backlog (check for pending todos)
4. `git log --oneline -20` — recent commits
5. `git status` — uncommitted work (if any, someone was in the middle of something)

If `.claude/features.json` does not exist, inform the user and suggest running
brainstorming first to create one. STOP.

**MUST: Config validation — do this IMMEDIATELY after reading files.**

1. **If `.claude/sp-harness.json` does not exist:**
   - Create it with default values:
     ```json
     {"dev_mode": "three-agent", "last_hygiene_at_completed": 0}
     ```
   - Report: "Created sp-harness.json with defaults (three-agent mode, hygiene counter 0)"
2. **If it exists:** read `dev_mode` and `last_hygiene_at_completed`
3. **If `dev_mode` is missing:** set to `"three-agent"`, write to disk
4. **If `last_hygiene_at_completed` is missing:** set to `0`, write to disk

**MUST: Hygiene counter validation — ONLY validates. Does NOT trigger cleanup.**

1. Read `last_hygiene_at_completed` from `.claude/sp-harness.json`
2. Count features with `"passes": true` → `completed_count`
3. Compute `delta = completed_count - last_hygiene_at_completed`
4. **Validate:** `delta` MUST be < 3. If `delta >= 3`, something went wrong
   (Step 5 should have cleaned up). Report warning:
   "Hygiene counter invalid: delta={delta}, expected < 3. Will clean in Step 5."

---

## Step 2: Show progress summary

Present a brief status to the user:

```
Feature Progress: X/Y completed
Dev Mode: {dev_mode}
Hygiene: last at {last_hygiene_at_completed}, next at {last_hygiene_at_completed + 3}

Remaining (by priority):
  [high]   feature-id — description
  [medium] feature-id — description
  [low]    feature-id — description
```

---

## Step 3: Pick next feature

**Selection algorithm (topological order first, then priority):**

1. Filter: `passes: false`
2. Filter: all IDs in `depends_on` have `passes: true` (dependencies satisfied)
3. Sort candidates: high → medium → low priority
4. Within same priority: array order
5. Pick first candidate

If no candidate is available (all remaining features have unsatisfied dependencies),
report a **dependency deadlock** and print the blocked features with their unmet
dependencies. STOP and ask user to resolve.

Present the selected feature to the user:

```
Next: [feature-id] — description
Priority: high
Depends on: [list of depends_on IDs, or "none"]
From todo: [todo-id, if any]
Steps:
  1. step one
  2. step two
  ...
```

Ask: "Ready to start this feature, or do you want to pick a different one?"

Wait for user confirmation before proceeding.

---

## Step 4: Invoke development skill

Read `dev_mode` from `.claude/sp-harness.json` and dispatch accordingly:

**If `dev_mode` is `"three-agent"`:**
Invoke `sp-harness:three-agent-development` with the selected feature.

This skill will:
1. Dispatch sp-planner subagent → produces task-plan.json + eval-plan.json
2. **Print plan summary table to you and wait for your confirmation**
3. Dispatch sp-generator subagent → executes via subagent-driven-development
4. Dispatch sp-evaluator subagent → produces eval-report.json
5. Handle PASS/ITERATE/REJECT

**If `dev_mode` is `"single-agent"`:**
Invoke `sp-harness:single-agent-development` with the selected feature.

Same pipeline (Plan → Implement → Evaluate) but all phases run in the
main session without subagent dispatch. See single-agent-development for details.

---

You will see the plan and approve it before any code is written.

When the development skill returns PASS, feature-tracker proceeds to Step 5.
If REJECT, feature-tracker stops and reports to user.

---

## Step 5: Commit, hygiene cleanup, LOOP BACK

The dev skill (three-agent or single-agent) already archived state files
to `.claude/agents/state/archive/<feature-id>/` on PASS.

**MUST: Check originating todo completion.**

Read the completed feature from `.claude/features.json`. If it has a
non-null `from_todo` field:
1. Invoke `sp-harness:manage-todos` **Check done** operation with the todo id
   and the current `features.json` contents.
2. If the operation returns `done=true`, the todo was automatically transitioned
   to `status: done` (manage-todos handles it). Include `.claude/todos.json`
   in the upcoming commit.
3. If `done=false`, remaining features are listed — no action beyond noting
   the remaining list for context.

**MUST: Commit feature completion — do NOT skip:**
```
git add .claude/features.json .claude/sp-harness.json \
        .claude/agents/state/archive/ .claude/todos.json
git commit -m "[features]: mark {feature-id} as complete"
```
This commit is how new sessions know which features are done via `git log`.
Without it, the session start protocol's git log step is useless.

**MUST: Hygiene cleanup — AUTOMATIC, do NOT ask the user for permission.**

a. Read `last_hygiene_at_completed` from `.claude/sp-harness.json`
b. Count features with `"passes": true` → `completed_count`
c. Compute `delta = completed_count - last_hygiene_at_completed`
d. **If delta >= 3:**
   a. Print: "Hygiene threshold reached (delta={delta}). Running code-hygiene now."
   b. Invoke `sp-harness:code-hygiene` IMMEDIATELY. Do NOT ask "should I run
      hygiene?" or "would you like me to clean up?". This is automatic. Just do it.
   c. Read `.claude/agents/state/active/hygiene-result.json`
   d. **If file exists AND `status` is `"complete"`:**
      - Set `last_hygiene_at_completed` to `completed_count` in `.claude/sp-harness.json`
      - Write sp-harness.json to disk
      - Delete `.claude/agents/state/active/hygiene-result.json`
      - Report: "Hygiene complete. Counter updated to {completed_count}."
   e. **If file missing OR status is NOT `"complete"`:**
      - Do NOT update the counter
      - Warn: "Hygiene did not complete. Counter not updated. Will retry next loop."
e. **If delta < 3:** continue

3. **Check if ALL features pass:**
   - **NO (features remain)** → GO BACK TO STEP 2 NOW.
   - **YES (all pass)** →
     ```
     All features complete. .claude/features.json shows X/X passing.
     Dispatching sp-feedback (Mode A) for system-level review.
     ```
     Dispatch `@agent sp-feedback` with `"mode": "A"`. This is the only exit
     from the loop. sp-feedback runs the structured checklist, writes
     `.claude/agents/state/active/feedback-actions.json`, and presents findings
     grouped by action type. You (orchestrator) then handle per-batch
     user confirmation and action execution (see sp-feedback's definition
     for the protocol).

     **If sp-feedback results in new_todo or fix_feature actions** that
     the user approves → append to features.json and re-enter the loop
     at Step 2 to develop them.

---

## Rules

1. One feature per cycle — do not batch multiple features
2. Verification is handled by the development skill's Evaluator — do not
   mark passes: true without Evaluator PASS verdict
3. Never skip the user confirmation in Step 3
4. If a feature turns out to be too large during implementation, pause and
   split it into sub-features in features.json before continuing
5. If implementation reveals a new feature that is needed, add it to
   features.json with appropriate priority — do not scope-creep the current feature
6. Step 1 VALIDATES the hygiene counter (exists, value is sane).
   Step 5 TRIGGERS cleanup (invokes code-hygiene, updates counter).
   Never skip either step.
7. To switch dev_mode, use `sp-harness:switch-dev-mode` skill.
