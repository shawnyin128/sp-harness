---
name: three-agent-development
description: |
  Feature-level orchestration with three independent agents: Planner (design),
  Generator (execution), and Evaluator (quality assessment). Each agent
  delegates to existing sp-harness skills internally. Agents communicate
  through files in .claude/agents/state/. Explicitly triggered by feature-tracker
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

Agent communication goes through `.claude/agents/state/`. Active work lives
in `active/`; completed features archive to `archive/<feature-id>/`.

```
.claude/agents/state/
├── active/                            ← current feature's work-in-progress
│   ├── task-plan.json                 ← Planner output
│   ├── eval-plan.json                 ← Planner output
│   ├── implementation.md              ← Generator output
│   └── eval-report.json               ← Evaluator output
└── archive/
    └── <feature-id>/
        ├── iter-1-task-plan.json
        ├── iter-1-eval-plan.json
        ├── iter-1-implementation.md
        ├── iter-1-eval-report.json
        ├── iter-2-* (if multi-iteration)
        └── final-eval-report.json     ← last iteration's report (sp-feedback reads these)
```

Create these directories if missing.

---

## Step 1: Select Feature

Read the feature from `.claude/features.json` (passed by feature-tracker,
or specified by user). Read context: `CLAUDE.md`, spec document referenced
in CLAUDE.md's Design Docs section (if any). Check `active/` for any
in-progress state from a prior interrupted session.

---

## Step 2: Dispatch Planner

Dispatch the `sp-planner` subagent (`@agent sp-planner`). It runs as Opus
with writing-plans pre-loaded and project memory enabled.

**Planner does two things internally:**

1. **Implicit requirements discovery** — scans feature for gaps, asks user
   questions one-at-a-time until resolved.

2. **Plan production** — invokes `sp-harness:writing-plans` to generate
   the implementation plan. Follows all writing-plans conventions (TDD steps,
   file structure, no placeholders, fallback chain design).

**Planner writes two JSON files to `.claude/agents/state/`:**
- `task-plan.json` — implementation plan (from writing-plans, serialized as JSON)
- `eval-plan.json` — evaluation playbook: for each task, specifies method
  (spec-review / code-review / both), quantifiable criteria, and verify commands.

**After Planner completes**, the orchestrator (YOU — not the Planner subagent)
MUST do the following before dispatching Generator:

<HARD-GATE>
1. Read `.claude/agents/state/active/task-plan.json` and `.claude/agents/state/active/eval-plan.json`
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

Dispatch the `sp-generator` subagent (`@agent sp-generator`). It runs as
Sonnet in an isolated worktree with subagent-driven-development and TDD
pre-loaded.

**Generator does one thing internally:**

Invokes `sp-harness:subagent-driven-development` to execute task-plan.json.
This runs the full existing task-level machinery:
- Fresh implementer subagent per task
- Spec compliance review after each task
- Code quality review after each task
- TDD cycle for each step

**Generator writes one file to `.claude/agents/state/`:**
- `implementation.md` — execution report

---

## Step 4: Dispatch Evaluator

Dispatch the `sp-evaluator` subagent (`@agent sp-evaluator`). It runs as
Opus with read-only + Bash tools and project memory enabled.

**Evaluator parses eval-plan.json and follows it task by task:**
- For each `task_evaluations` entry: uses the specified `method`, checks
  each `criteria` item, runs `verify_commands`
- Does NOT trust Generator's report — reads actual code and runs tests
- After all tasks: evaluates `feature_level_criteria`
- Checks against `acceptance_threshold`
- Can adjust criteria if needed (must document why)

**Evaluator writes one JSON file to `.claude/agents/state/`:**
- `eval-report.json` — structured report with per-task `criteria_results[]`,
  `verify_results[]`, `iteration_items[]`, and `convergence` status.
  Planner reads this JSON to decide whether and how to iterate.

---

## Step 5: Print Evaluation Results and Handle Verdict

**MUST: Before handling the verdict, print the evaluation summary to the user.**

Read `.claude/agents/state/active/eval-report.json` and print:

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

### PASS
1. Mark feature passing via script:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/mutate.py" \
     mark-passing <feature-id>
   ```
   Do NOT edit features.json directly.
2. **Archive state files:**
   - Create `.claude/agents/state/archive/<feature-id>/` if missing
   - Move `active/task-plan.json` → `archive/<feature-id>/iter-<N>-task-plan.json`
   - Move `active/eval-plan.json` → `archive/<feature-id>/iter-<N>-eval-plan.json`
   - Move `active/implementation.md` → `archive/<feature-id>/iter-<N>-implementation.md`
   - Move `active/eval-report.json` → `archive/<feature-id>/iter-<N>-eval-report.json`
   - Copy final iteration's eval-report to `archive/<feature-id>/final-eval-report.json`
   - `active/` directory ends empty
3. Commit: `[features]: mark {feature-id} as complete` (include features.json + archive/)
4. Return to feature-tracker

### ITERATE
1. Check `convergence.status` from the printed results
2. **If diverging** — escalate to REJECT
3. **If converging:**
   a. Archive the current iteration's files to `archive/<feature-id>/iter-<N>-*`
      (Planner will produce iter N+1 files fresh in `active/`)
   b. GO BACK TO STEP 2. Planner reads eval-report.json from `archive/<feature-id>/iter-<N>-eval-report.json` to inform re-planning.
   **ITERATE is not a shortcut. It is a full cycle through Steps 2-5.**

### REJECT
1. Stop. Preserve all files in `.claude/agents/state/active/` and any archived iterations.
2. Report to user: what was attempted, why it failed, full evaluator assessment.
   Main session may add a todo.md entry for follow-up investigation.

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
4. All communication through `.claude/agents/state/` files only

---

## Subagent Definitions

All agents are **project-level**, generated by init-project from templates
at `${CLAUDE_PLUGIN_ROOT}/agent-templates/`:

- `.claude/agents/sp-planner.md` — Opus, writing-plans preloaded, project memory
- `.claude/agents/sp-generator.md` — Sonnet, TDD + subagent-driven-dev + git-convention preloaded, worktree isolation
- `.claude/agents/sp-evaluator.md` — Opus, read-only + Bash, project memory

Templates include `{PROJECT_CONTEXT}` slots filled during init-project with
project-specific stack, modules, and invariants. No plugin-level defaults
for these three — they are always project-adapted.

To regenerate or reconfigure after init: use `sp-harness:switch-dev-mode`.
