---
name: three-agent-development
description: |
  Feature-level orchestration with three independent agents: Planner (design),
  Generator (execution via subagent-driven-development), and Evaluator (quality
  assessment). Agents communicate through files in .claude/agents/, maintaining
  independence. Use when executing features from docs/features.json that need
  structured planning, implementation, and evaluation cycles.
author: superpowers
version: 1.0.0
---

# Three-Agent Development

Orchestrate feature implementation through three independent agents that
communicate via files. Each agent has a distinct role and operates with
its own context.

**Architecture:**

```
Feature layer (this skill)
  Planner  → task-plan.md + eval-criteria.md
  Generator → calls subagent-driven-development → implementation.md
  Evaluator → eval-report.md
                    ↕ iteration loop

Task layer (existing subagent-driven-development)
  controller → implementer → spec-reviewer → code-reviewer
```

---

## Agent Roles

### Planner (use most capable model, e.g. Opus)

Reads the feature definition and project context. Produces two files:
- `task-plan.md` — detailed code-level plan for the Generator
- `eval-criteria.md` — evaluation standards for the Evaluator

The Planner is the brain. It makes design decisions, breaks work into tasks,
and defines what "done" looks like.

### Generator (use standard model, e.g. Sonnet)

Reads `task-plan.md` and executes via subagent-driven-development. Produces:
- `implementation.md` — execution report (what changed, test results, issues)

The Generator is the executor. It does not make design decisions — it follows
the plan. If the plan is ambiguous, it reports NEEDS_CONTEXT rather than guessing.

### Evaluator (use most capable model, e.g. Opus)

Reads `eval-criteria.md` and `implementation.md`. Produces:
- `eval-report.md` — standardized assessment with verdict and iteration items

The Evaluator is the judge. It is fully autonomous — it can adjust evaluation
criteria based on its own judgment, but must explain why.

---

## File Structure

All agent communication files live in `.claude/agents/`. Create this directory
if it does not exist.

```
.claude/agents/
├── task-plan.md          ← Planner output: code-level plan
├── eval-criteria.md      ← Planner output: evaluation standards
├── implementation.md     ← Generator output: execution report
└── eval-report.md        ← Evaluator output: assessment + iteration items
```

Files are overwritten each iteration. The orchestrator (this skill) manages
versioning by tracking iteration count.

---

## Step 1: Select Feature

Read `docs/features.json`. Select the target feature (from feature-tracker,
or as specified by the user).

Read context:
- `.claude/mem/memory.md` — current project state
- `CLAUDE.md` — project map
- The relevant spec document (from Project Map)

---

## Step 2: Dispatch Planner

Dispatch a Planner agent (use most capable model) with:
- The feature definition (from features.json)
- Project context (CLAUDE.md, memory.md, relevant spec)
- The divergence risk analysis (from spec, if available)

**The Planner runs in two phases:**

**Phase 1 — Implicit Requirements Discovery:** The Planner scans the feature
for gaps and unspecified details. If found, it asks the user questions one at
a time, shallow to deep, until all gaps are resolved. This prevents the Generator
from making assumptions about unspecified behavior.

**Phase 2 — Plan Production:** Only after all gaps are resolved, the Planner
produces two files:

**Planner produces two files:**

### task-plan.md (EXACT structure — do not add or rename sections)

````markdown
# Task Plan

## Feature: {FILL: feature-id}
## Iteration: {FILL: number}
## Based on: {FILL: spec document path}

### Task 1: {FILL: name}
**Files:** {FILL: create/modify list}
**Steps:**
1. {FILL: concrete step with code}
2. {FILL: concrete step with code}

### Task N: {FILL: repeat as needed}

## Divergence Handling
{FILL: for each risk from spec — detection, recovery, safe stop}
````

### eval-criteria.md (EXACT structure — do not add or rename sections)

````markdown
# Evaluation Criteria

## Feature: {FILL: feature-id}
## Iteration: {FILL: number}

## Functional Criteria
- [ ] {FILL: testable behavior from feature steps}

## Quality Criteria
- [ ] {FILL: code quality / test coverage expectation}

## Divergence Criteria
- [ ] {FILL: fallback logic verification}

## Acceptance Threshold
{FILL: e.g. "All functional must pass. Quality/divergence: at least 3/4."}
````

---

## Step 3: Dispatch Generator

Dispatch a Generator agent (use standard model) with:
- `task-plan.md` as the implementation plan
- Working directory context

The Generator **invokes subagent-driven-development** to execute the plan.
This reuses the existing task-level machinery (implementer, spec-reviewer,
code-quality-reviewer).

**Generator produces:**

### implementation.md

Implementation report (EXACT structure — do not add or rename sections):

````markdown
# Implementation Report

## Feature: {FILL}
## Iteration: {FILL}

## Tasks Completed
### Task 1: {FILL}
- Status: {DONE | DONE_WITH_CONCERNS | BLOCKED}
- Files changed: {FILL}
- Tests: {FILL: X passing, Y failing}
- Commits: {FILL: SHA list}

## Summary
- Total tasks: {FILL}
- Completed: {FILL}
- Blocked: {FILL}
- Test results: {FILL}
````

---

## Step 4: Dispatch Evaluator

Dispatch an Evaluator agent (use most capable model) with:
- `eval-criteria.md` — the evaluation standards
- `implementation.md` — the execution report
- Access to the codebase (to read actual code changes)

**Evaluator produces:**

Eval report (EXACT structure — do not add or rename sections):

````markdown
# Evaluation Report

## Feature: {FILL}
## Iteration: {FILL}
## Verdict: {PASS | ITERATE | REJECT}

## Criteria Assessment
### Functional Criteria
- [x] {criterion} — {how verified}
- [ ] {criterion} — FAIL: {reason}

### Quality Criteria
- [x] {criterion} — {evidence}
- [ ] {criterion} — FAIL: {reason}

### Divergence Criteria
- [x] {criterion} — {evidence}
- [ ] {criterion} — FAIL: {reason}

## Iteration Items
### Item 1
- **Location:** {task/file}
- **Problem:** {specific issue}
- **Suggestion:** {direction}
- **Priority:** {must-fix | should-fix}

## Criteria Adjustments
{FILL: what changed and why, or "None"}

## Convergence Assessment
{FILL: "First iteration" or "Converging/Diverging — evidence"}
````

---

## Step 5: Handle Verdict

### PASS
1. Update `docs/features.json` — set `passes: true`
2. Update `.claude/mem/memory.md` — Current State reflects completion
3. Commit: `[features]: mark [feature-id] as complete`
4. Clean up `.claude/agents/` files (or archive to `.claude/agents/history/`)
5. Return to feature-tracker for next feature

### ITERATE
1. Check convergence assessment in eval-report.md
2. **If converging** — dispatch Planner with eval-report.md to produce revised
   task-plan.md (iteration N+1). Planner reads Iteration Items and adjusts plan.
3. **If diverging** — this is the iteration fallback:
   - If 3+ iterations and still diverging → escalate to REJECT
   - If new issues keep appearing → the feature may need redesign, escalate
4. Dispatch Generator with revised plan → Evaluator again → loop

### REJECT
1. Stop all agent work
2. Preserve all files in `.claude/agents/` (do not clean up)
3. Update `.claude/mem/memory.md` — note the rejection and reason
4. Report to user with full context:
   - What was attempted
   - Why it was rejected
   - Evaluator's assessment
   - Recommendation: redesign feature, break into smaller features, or manual intervention

---

## Iteration Divergence Fallback

The iteration loop itself is a divergence source. Apply the standard framework:

**Detection:** Track two signals across iterations:
- Item count: are Iteration Items decreasing?
- Item identity: are the same issues recurring, or are new ones appearing?

**Convergence = safe to continue:**
- Fewer items than previous iteration, OR
- Same items but lower priority (must-fix → should-fix)

**Divergence = escalate:**
- More items than previous iteration
- New must-fix items appearing that weren't in previous iteration
- Same must-fix items persisting after 2 iterations (fix attempts failing)

**Recovery:** On divergence detection, the Evaluator automatically sets
verdict to REJECT with a note explaining the divergence pattern.

**Safe stop:** All intermediate files preserved. User gets full iteration
history to diagnose the root cause.

---

## Agent Independence Rules

1. **No shared context:** Each agent is dispatched with only its designated
   input files. The Planner never sees implementation.md. The Generator
   never sees eval-report.md. The Evaluator never sees the Planner's prompt.

2. **File-only communication:** Agents do not pass information through
   prompts or context. Everything goes through the files in `.claude/agents/`.

3. **No cross-role decisions:** The Generator does not evaluate. The Evaluator
   does not plan. The Planner does not implement. If an agent needs to cross
   roles, it reports back and the orchestrator re-dispatches the right agent.

4. **Model separation:** Planner and Evaluator use the most capable model.
   Generator uses a standard model. This reflects the nature of each role:
   design and judgment need capability, execution needs efficiency.

---

## Integration with Existing Skills

This skill is the **upper layer** that orchestrates feature-level development.
It delegates to existing skills:

- **feature-tracker** → selects which feature to work on
- **subagent-driven-development** → Generator uses this for task execution
- **writing-plans** → Planner may reference plan format conventions
- **update-mem** → after each feature completes
- **git-convention** → all commits follow `[module]: description`
