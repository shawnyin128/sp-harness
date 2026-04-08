---
name: feature-tracker
description: |
  Incremental feature development orchestrator. Reads docs/features.json,
  picks the highest-priority unfinished feature, and drives it through
  the brainstorming → writing-plans → executing-plans pipeline. Updates
  feature status and memory.md after completion. Use when starting a
  development session or when the current feature is done and you need
  to pick the next one.
author: superpowers
version: 1.0.0
---

# feature-tracker

Orchestrate incremental development by working through features one at a time.

---

## Step 1: Read context

Read these in order:

1. `.claude/mem/memory.md` — current state, what was last worked on
2. `.claude/mem/todo.md` — open problems
3. `git log --oneline -20` — recent commits
4. `docs/features.json` — the feature list

If `docs/features.json` does not exist, inform the user and suggest running
brainstorming first to create one.

---

## Step 2: Show progress summary

Present a brief status to the user:

```
Feature Progress: X/Y completed

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

Invoke `superpowers:three-agent-development` with the selected feature.

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

## Step 5: Update memory, hygiene check, pick next

Update `.claude/mem/memory.md` Current State to reflect completion.

**Hygiene check:** Count how many features have completed since the last
code-hygiene run. If the count reaches 3 (or user-configured interval),
invoke the **code-hygiene** skill before picking the next feature.

Then return to Step 2 to show updated progress and pick the next feature.

If all features pass:
```
All features complete. docs/features.json shows X/X passing.
Invoking system-feedback for optimization review.
```
Then invoke the **system-feedback** skill for a comprehensive system-level review.

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
