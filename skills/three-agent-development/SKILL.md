---
name: three-agent-development
description: |
  Feature-level orchestration with three independent agents: Planner (design),
  Generator (execution), and Evaluator (quality assessment). Each agent
  delegates to existing superpowers skills internally. Agents communicate
  through files in .claude/agents/. Explicitly triggered by feature-tracker
  or user.
author: superpowers
version: 2.0.0
---

# Three-Agent Development

Three independent agents develop a feature through structured cycles.
Each agent delegates to existing superpowers skills — this skill only
orchestrates the agent dispatch and iteration loop.

```
Planner  → calls writing-plans    → task-plan.md + eval-plan.md
Generator → calls subagent-driven → implementation.md
Evaluator → reads code + reports  → eval-report.md
                  ↕ iteration loop (ITERATE → Planner re-plans)
```

---

## File Structure

All agent communication goes through `.claude/agents/`. Create if missing.

```
.claude/agents/
├── task-plan.md       ← Planner output: implementation plan for Generator
├── eval-plan.md       ← Planner output: evaluation playbook for Evaluator
├── implementation.md  ← Generator output: execution report
└── eval-report.md     ← Evaluator output: assessment + iteration items
```

---

## Step 1: Select Feature

Read the feature from `docs/features.json` (passed by feature-tracker,
or specified by user). Read context: `.claude/mem/memory.md`, `CLAUDE.md`,
relevant spec document.

---

## Step 2: Dispatch Planner

Dispatch using `./planner-prompt.md`. Use most capable model (e.g. Opus).

**Planner does two things internally:**

1. **Implicit requirements discovery** — scans feature for gaps, asks user
   questions one-at-a-time until resolved. (Logic in planner-prompt.md.)

2. **Plan production** — invokes `superpowers:writing-plans` to generate
   the implementation plan. Follows all writing-plans conventions (TDD steps,
   file structure, no placeholders, fallback chain design).

**Planner writes two paired files to `.claude/agents/`:**
- `task-plan.md` — implementation plan (from writing-plans)
- `eval-plan.md` — evaluation playbook: for each task, specifies the evaluation
  method (spec-review / code-review / both), specific criteria, and exact
  verification steps. Also includes feature-level cross-cutting criteria.

**After writing both files, Planner presents a summary to the user.**
The orchestrator waits for user acknowledgment before dispatching Generator.
This ensures the user sees and approves the plan before code is written.

---

## Step 3: Dispatch Generator

Dispatch using `./generator-prompt.md`. Use standard model (e.g. Sonnet).

**Generator does one thing internally:**

Invokes `superpowers:subagent-driven-development` to execute task-plan.md.
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

**Evaluator follows the Planner's eval-plan.md task by task:**
- For each task: uses the specified method (spec-review / code-review / both)
  and follows the exact verification steps
- Does NOT trust Generator's report — reads actual code and runs tests
- After all tasks: evaluates feature-level cross-cutting criteria
- Can adjust criteria if needed (must document why)

**Evaluator writes one file to `.claude/agents/`:**
- `eval-report.md` — verdict + iteration items if needed

---

## Step 5: Handle Verdict

### PASS
1. Update `docs/features.json` — set `passes: true`
2. Update `.claude/mem/memory.md` Current State
3. Commit: `[features]: mark {feature-id} as complete`
4. Return to feature-tracker

### ITERATE
1. Read convergence assessment in eval-report.md
2. **If converging** — dispatch Planner again with eval-report.md as input.
   Planner reads Iteration Items, revises task-plan.md and eval-plan.md.
3. **If diverging** — escalate to REJECT
4. Generator executes revised plan → Evaluator assesses again → loop

### REJECT
1. Stop. Preserve all files in `.claude/agents/`
2. Update `.claude/mem/memory.md` — note rejection and reason
3. Report to user: what was attempted, why it failed, evaluator's assessment

---

## Iteration Divergence Fallback

Track across iterations:
- **Converging:** fewer items, or same items at lower priority
- **Diverging:** more items, new must-fix items, same must-fix persisting 2+ rounds

On divergence → Evaluator sets REJECT with explanation.
All intermediate files preserved for user diagnosis.

---

## Agent Independence

1. Planner never sees implementation.md or eval-report.md (except when
   re-planning after ITERATE — then it reads eval-report.md only)
2. Generator never sees eval-plan.md or eval-report.md
3. Evaluator never sees task-plan.md or the Planner's prompt
4. All communication through `.claude/agents/` files only

---

## Model Selection

| Agent | Model | Why |
|-------|-------|-----|
| Planner | Most capable (Opus) | Design decisions, requirement analysis |
| Generator | Standard (Sonnet) | Execution — plan is already detailed |
| Evaluator | Most capable (Opus) | Independent judgment, quality assessment |
