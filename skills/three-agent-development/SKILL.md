---
name: three-agent-development
description: |
  Feature-level orchestration with three independent agents: Planner (design),
  Generator (execution), and Evaluator (quality assessment). Each agent
  delegates to existing sp-harness skills internally. Agents communicate
  through files in .claude/agents/. Explicitly triggered by feature-tracker
  or user.
author: sp-harness
version: 2.0.0
---

# Three-Agent Development

Three independent agents develop a feature through structured cycles.
Each agent delegates to existing sp-harness skills — this skill only
orchestrates the agent dispatch and iteration loop.

```
Planner  → calls writing-plans    → task-plan.json + eval-plan.json
Generator → calls subagent-driven → implementation.md
Evaluator → reads code + reports  → eval-report.json
                  ↕ iteration loop (ITERATE → Planner re-plans)
```

---

## File Structure

All agent communication goes through `.claude/agents/`. Create if missing.

```
.claude/agents/
├── task-plan.json     ← Planner output: implementation plan (Generator reads)
├── eval-plan.json     ← Planner output: evaluation playbook (Evaluator reads)
├── implementation.md  ← Generator output: execution report
└── eval-report.json   ← Evaluator output: structured assessment (JSON)
```

---

## Step 1: Select Feature

Read the feature from `docs/features.json` (passed by feature-tracker,
or specified by user). Read context: `.claude/mem/memory.md`, `CLAUDE.md`,
spec document referenced in CLAUDE.md's Design Docs section (if any).

---

## Step 2: Dispatch Planner

Dispatch using `./planner-prompt.md`. Use most capable model (e.g. Opus).

**Planner does two things internally:**

1. **Implicit requirements discovery** — scans feature for gaps, asks user
   questions one-at-a-time until resolved. (Logic in planner-prompt.md.)

2. **Plan production** — invokes `sp-harness:writing-plans` to generate
   the implementation plan. Follows all writing-plans conventions (TDD steps,
   file structure, no placeholders, fallback chain design).

**Planner writes two JSON files to `.claude/agents/`:**
- `task-plan.json` — implementation plan (from writing-plans, serialized as JSON)
- `eval-plan.json` — evaluation playbook: for each task, specifies method
  (spec-review / code-review / both), quantifiable criteria, and verify commands.

**After Planner completes**, the orchestrator (YOU — not the Planner subagent)
MUST do the following before dispatching Generator:

<HARD-GATE>
1. Read `.claude/agents/task-plan.json` and `.claude/agents/eval-plan.json`
2. Print a merged summary table to the user:

```
Feature: {feature-id} (iteration {N})

| Task | Description | Eval Method | Criteria |
|------|-------------|-------------|----------|
| 1. {name} | {desc} | {method} | {criteria} |
| 2. {name} | {desc} | {method} | {criteria} |

Feature-level: {feature_level_criteria}
Threshold: {acceptance_threshold}
```

3. Ask: "Plans ready. Review and confirm before I start implementation?"
4. WAIT for user confirmation. Do NOT dispatch Generator until user says yes.
</HARD-GATE>

---

## Step 3: Dispatch Generator

Dispatch using `./generator-prompt.md`. Use standard model (e.g. Sonnet).

**Generator does one thing internally:**

Invokes `sp-harness:subagent-driven-development` to execute task-plan.json.
This runs the full existing task-level machinery:
- Fresh implementer subagent per task (using implementer-prompt.md)
- Spec compliance review after each task (using spec-reviewer-prompt.md)
- Code quality review after each task (using code-quality-reviewer-prompt.md)
- TDD cycle for each step

**Generator writes one file to `.claude/agents/`:**
- `implementation.md` — execution report

---

## Step 4: Dispatch Evaluator

Dispatch using `./evaluator-prompt.md`. Use most capable model (e.g. Opus).

**Evaluator parses eval-plan.json and follows it task by task:**
- For each `task_evaluations` entry: uses the specified `method`, checks
  each `criteria` item, runs `verify_commands`
- Does NOT trust Generator's report — reads actual code and runs tests
- After all tasks: evaluates `feature_level_criteria`
- Checks against `acceptance_threshold`
- Can adjust criteria if needed (must document why)

**Evaluator writes one JSON file to `.claude/agents/`:**
- `eval-report.json` — structured report with per-task `criteria_results[]`,
  `verify_results[]`, `iteration_items[]`, and `convergence` status.
  Planner reads this JSON to decide whether and how to iterate.

---

## Step 5: Print Evaluation Results and Handle Verdict

<HARD-GATE>
**Before handling the verdict, you MUST print the evaluation summary to the user.**

Read `.claude/agents/eval-report.json` and print:

```
Evaluation Results (iteration {N}): {VERDICT}

Task Results:
  Task 1: {name} — {PASS/FAIL}
    Failed: {list failed criteria with reasons}
    Weakest: {weakest_point for passed criteria}
  Task 2: {name} — {PASS/FAIL}
    ...

Feature-Level:
  {each criterion — PASS/FAIL with evidence/reason}

Iteration Items:
  [{priority}] {location}: {problem} → {suggestion}

Convergence: {status} — {evidence}
```

Do NOT summarize or skip details. Print every failed criterion with its
reason and location. The user needs this to understand what is happening.
</HARD-GATE>

### PASS
1. Update `docs/features.json` — set `passes: true`
2. Update `.claude/mem/memory.md` Current State
3. Commit: `[features]: mark {feature-id} as complete`
4. Return to feature-tracker

### ITERATE
1. Check `convergence.status` from the printed results
2. **If diverging** — escalate to REJECT
3. **If converging** — GO BACK TO STEP 2. The only difference from the
   first run is that Planner now also reads eval-report.json as input.
   Everything else is identical: Planner produces plans → orchestrator
   prints table → user confirms → Generator executes → Evaluator
   assesses → orchestrator prints results → handle verdict.
   **ITERATE is not a shortcut. It is a full cycle through Steps 2-5.**

### REJECT
1. Stop. Preserve all files in `.claude/agents/`
2. Update `.claude/mem/memory.md` — note rejection and reason
3. Report to user: what was attempted, why it failed, full evaluator assessment

---

## Iteration Divergence Fallback

Track across iterations:
- **Converging:** fewer items, or same items at lower priority
- **Diverging:** more items, new must-fix items, same must-fix persisting 2+ rounds

On divergence → Evaluator sets REJECT with explanation.
All intermediate files preserved for user diagnosis.

---

## Agent Independence

1. Planner never sees implementation.md or eval-report.json (except when
   re-planning after ITERATE — then it reads eval-report.json only)
2. Generator never sees eval-plan.json or eval-report.json
3. Evaluator never sees task-plan.json or the Planner's prompt
4. All communication through `.claude/agents/` files only

---

## Models

Planner + Evaluator: most capable (Opus). Generator: standard (Sonnet).
