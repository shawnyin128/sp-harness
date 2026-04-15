---
name: single-agent-development
description: |
  Feature development with a single agent playing all three roles (Planner,
  Generator, Evaluator) sequentially. Same pipeline as three-agent-development
  but without subagent dispatch — all phases run in the main session.
  Use when subagent overhead is unnecessary or for simpler projects.
author: sp-harness
version: 1.0.0
---

# Single-Agent Development

One agent develops a feature by switching between three roles sequentially.
The pipeline is IDENTICAL to three-agent-development — same file structure,
same JSON schemas, same evaluation standards. The only difference is execution:
no subagent dispatch, everything runs in the main session context.

```
[Planner role]  → task-plan.json + eval-plan.json
[Generator role] → implementation.md
[Evaluator role] → eval-report.json
                ↕ iteration loop (ITERATE → Planner role re-plans)
```

---

## File Structure

Same as three-agent-development. Active work in `active/`, completed
features archived to `archive/<feature-id>/`.

```
.claude/agents/state/
├── active/            ← current work
│   ├── task-plan.json
│   ├── eval-plan.json
│   ├── implementation.md
│   └── eval-report.json
└── archive/
    └── <feature-id>/
        ├── iter-<N>-*.*
        └── final-eval-report.json
```

---

## Step 1: Select Feature

Read the feature from `.claude/features.json` (passed by feature-tracker,
or specified by user). Read context: `CLAUDE.md`, spec document referenced
in CLAUDE.md's Design Docs section (if any). Check `active/` for in-progress
state from a prior interrupted session.

---

## Step 2: Planner Role

<EXTREMELY-IMPORTANT>
Switch to Planner mindset. You are designing, NOT implementing.
Do not write any code. Do not make implementation decisions that belong
to the Generator role. Produce plans only.
</EXTREMELY-IMPORTANT>

**Phase 1: Implicit requirements discovery.**
First: if the spec has a `## Codebase Context` section, use it as ground truth.
If no Codebase Context but existing code exists, check the modules this feature
touches for variants (v1/v2, old/new). If found, ask user which to use FIRST.
Then: scan the feature for gaps. Ask user one question at a time until resolved.

**Phase 2: Write implementation plan.**
Follow sp-harness:writing-plans conventions (TDD steps, file structure,
no placeholders, fallback chain design). Save as `.claude/agents/state/active/task-plan.json`
using the same schema as three-agent-development.

**Phase 3: Write evaluation plan.**
For each task, specify method (spec-review / code-review / both), criteria,
and verify_commands. Save as `.claude/agents/state/active/eval-plan.json`
using the same schema as three-agent-development.

**After completing both files**, print the merged summary table:

<HARD-GATE>
```
Feature: {feature-id} (iteration {N})

| Task | Description | Eval Method | Criteria |
|------|-------------|-------------|----------|
| 1. {name} | {desc} | {method} | {criteria} |
| 2. {name} | {desc} | {method} | {criteria} |

Feature-level: {feature_level_criteria}
Threshold: {acceptance_threshold}
```

Ask: "Plans ready. Review and confirm before I start implementation?"
WAIT for user confirmation. Do NOT proceed until user says yes.
</HARD-GATE>

---

## Step 3: Generator Role

<EXTREMELY-IMPORTANT>
Switch to Generator mindset. You are implementing, NOT designing.
Follow the plan EXACTLY. Do not redesign. If the plan seems wrong,
note DONE_WITH_CONCERNS in your report — do not fix the plan yourself.
</EXTREMELY-IMPORTANT>

Read `.claude/agents/state/active/task-plan.json`. For each task:
- Follow the `steps` array in order
- TDD cycle: test first, verify fail, implement, verify pass
- Commit after each task using [module]: description convention

After all tasks, write `.claude/agents/state/active/implementation.md` using the
same schema as three-agent-development.

---

## Step 4: Evaluator Role

<EXTREMELY-IMPORTANT>
Switch to Evaluator mindset. You are a RED TEAM. Your job is to FIND
PROBLEMS in the code YOU JUST WROTE. This is the hardest part of
single-agent mode — you must actively fight the urge to approve your
own work.

**Self-persuasion is your enemy.** You wrote this code minutes ago.
Your brain wants to believe it's correct. RESIST THIS.
</EXTREMELY-IMPORTANT>

**Mandatory adversarial protocol for single-agent mode:**

1. Before starting evaluation, re-read the Self-Persuasion Traps:
   - "Minor issue, not worth flagging" → flag it
   - "Works for the common case" → untested edge cases = failure
   - "Tests pass so it's fine" → tests only cover what was thought of
   - "Probably fine in practice" → "probably" = unverified = FAIL
   - "Good enough" → your job is finding flaws
   - "Would be caught later" → there is no later

2. **Mandatory cool-down:** Before evaluating, re-read the spec document
   and eval-plan.json from scratch. Do NOT rely on your memory of what
   you implemented — read the actual files.

3. **Zero-issue rule:** If you find zero issues on first pass, you MUST
   do a second pass specifically hunting for:
   - Edge cases not tested
   - Error paths not covered
   - Hardcoded values
   - Missing input validation
   - Race conditions

Read `.claude/agents/state/active/eval-plan.json` and `.claude/agents/state/active/implementation.md`.
Run every verify_command. Read every file listed. Write
`.claude/agents/state/active/eval-report.json` using the same schema as three-agent-development.

---

## Step 5: Print Evaluation Results and Handle Verdict

**MUST:** Read `.claude/agents/state/active/eval-report.json` and print the full
evaluation summary (same format as three-agent-development). Do NOT summarize
or skip.

### PASS
1. Mark feature passing via script:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/mutate.py" \
     mark-passing <feature-id>
   ```
   Do NOT edit features.json directly.
2. **Archive state files:**
   - Create `.claude/agents/state/archive/<feature-id>/` if missing
   - Move `active/*` files → `archive/<feature-id>/iter-<N>-*`
   - Copy final iteration's eval-report to `archive/<feature-id>/final-eval-report.json`
   - `active/` ends empty
3. **If feature has `supersedes` non-empty**, save spec's Supersession Plan
   to `archive/<feature-id>/supersession.json` (same structure as three-agent-development's PASS handler).
4. Commit: `[features]: mark {feature-id} as complete`
5. Return to feature-tracker

### ITERATE
1. Check `convergence.status`
2. **If diverging** — escalate to REJECT
3. **If converging:**
   a. Archive current iter's files to `archive/<feature-id>/iter-<N>-*`
   b. GO BACK TO STEP 2 (Planner role reads iter-N eval-report from archive).
   **ITERATE is not a shortcut. It is a full cycle through Steps 2-5.**

### REJECT
1. Stop. Preserve all files in `active/` and archived iterations.
2. Report to user. Main session may add todo.md entry for follow-up.

---

## When to Use Single-Agent vs Three-Agent

| Factor | Single-Agent | Three-Agent |
|--------|-------------|-------------|
| Project complexity | Simple to moderate | Complex |
| Context sharing | Roles share context (pro: continuity; con: self-persuasion) | Isolated contexts (pro: independence; con: context loss) |
| Token cost | Lower (one session) | Higher (3 subagents) |
| Evaluation rigor | Weaker (self-assessment bias) | Stronger (independent evaluator) |
| Speed | Faster (no dispatch overhead) | Slower (subagent startup) |

**Default recommendation:** three-agent for new projects, single-agent for
quick fixes, prototypes, or when token budget is constrained.

To switch modes: use `sp-harness:switch-dev-mode`.
