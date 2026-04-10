---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** This should be run in a dedicated worktree (created by brainstorming skill).

**Save plans to:** `docs/plans/active/YYYY-MM-DD-<feature-name>.md`
- (User preferences for plan location override this default)

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use sp-harness:subagent-driven-development (recommended) or sp-harness:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself — not a subagent dispatch.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

## Hybrid Boundary Awareness

If the spec contains a `## Hybrid Boundary` section, apply these rules:

**Task labeling:** Each task header MUST include its layer: `[code]`, `[agent]`, or `[interface]`.
- `[code]` — deterministic logic, tested with standard assertions
- `[agent]` — non-deterministic agent behavior, tested with behavioral checks
- `[interface]` — the boundary between code and agent, tested with contract validation

**Interface tasks come first.** Define the contract (schema, protocol, error types) before implementing either side. This prevents the most common hybrid bug: both sides assuming the other handles edge cases.

**Fallback scope:** Fallback chains for `[agent]` tasks must address the failure asymmetry defined in the spec's Hybrid Boundary section. The code layer's response to agent failure (retry / degrade / stop) must appear as concrete code in the relevant `[interface]` task.

If the spec has no `## Hybrid Boundary` section, skip this entirely.

## Fallback Chain Design

If the spec contains a `## Divergence Risk Analysis` section, you MUST design
fallback logic for every risk rated medium or above.

**Do not use a template library.** Each fallback is derived from the specific
divergence tree in the spec. For each risk, answer these four questions in order:

**1. Consequence** — what is the user-visible impact if this divergence occurs?
(The divergence tree in the spec already shows the propagation path.)

**2. Detection** — can you detect the divergence at the point it happens?
What signal tells you something went wrong? (e.g., schema validation failure,
timeout, unexpected return type, empty response)

**3. Recovery** — once detected, what is the minimum-cost way to recover?
Think from cheapest to most expensive: retry < fallback value < degraded mode
< pause and notify. Pick the cheapest that actually solves the problem.

**4. Safe stop** — if recovery fails, how does the system stop safely without
corrupting state or leaving the user confused? (e.g., roll back transaction,
return explicit error, preserve partial progress)

**Incorporate into tasks:** For each divergence point, the fallback logic must
appear as concrete code steps in the relevant task — not as a separate "error
handling" task. The fallback is part of the implementation, not an afterthought.

Example in a task:
```
- [ ] **Step 3: Add LLM response validation and fallback**
[code that validates LLM output against expected schema]
[if validation fails: retry with simplified prompt]
[if retry fails: return cached/default response + log warning]
```

**No placeholders.** "Add error handling for LLM response" is a plan failure.
Show the actual detection logic, recovery code, and safe-stop behavior.

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `docs/plans/active/<filename>.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use sp-harness:subagent-driven-development
- Fresh subagent per task + two-stage review

**If Inline Execution chosen:**
- **REQUIRED SUB-SKILL:** Use sp-harness:executing-plans
- Batch execution with checkpoints for review
