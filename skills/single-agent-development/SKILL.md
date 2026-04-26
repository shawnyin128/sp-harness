---
name: single-agent-development
description: |
  Feature development with a single agent playing all three roles (Planner,
  Generator, Evaluator) sequentially. Same pipeline as three-agent-development
  but without subagent dispatch — all phases run in the main session.
  Use when subagent overhead is unnecessary or for simpler projects.
author: sp-harness
version: 2.0.0
---

# Single-Agent Development

One agent develops a feature by switching between three roles sequentially.
The pipeline is IDENTICAL to three-agent-development — same shared YAML
plan file, same schemas, same terminal output conventions. The only
difference: roles switch in one session instead of dispatching three
subagents.

```
[Planner role]   → writes <feature-id>.plan.yaml (problem, steps, decisions)
                   → terminal: condensed summary + ask low-confidence decisions
[Generator role] → reads plan.yaml, implements, appends execution sections
                   → NO terminal output
[Evaluator role] → reads plan.yaml, runs tests, appends eval.rounds[]
                   → terminal: closure + tests + blockers-or-optimization
                   → iterate (loop back to Generator) or merge
```

---

## File Structure

Single shared YAML per feature: `.claude/agents/state/active/<feature-id>.plan.yaml`.
Schema defined in `docs/plan-file-schema.md`.

```
.claude/agents/state/
├── active/
│   └── <feature-id>.plan.yaml
└── archive/
    └── <feature-id>/
        ├── <feature-id>.plan.yaml
        ├── <feature-id>.iter-<N>.plan.yaml  (if replanned)
        └── supersession.json                 (if feature has supersedes)
```

Permanent tests at `tests/<feature-id>/` — written by Evaluator role,
survive merge as regression guards.

---

## Step 1: Select Feature

Read the feature from `.claude/features.json`. Read context: `CLAUDE.md`,
spec document referenced in CLAUDE.md. Check `active/` for interrupted state.

---

## Step 2: Planner Role

<EXTREMELY-IMPORTANT>
Switch to Planner mindset. You are designing, NOT implementing. Do not
write any code. Produce plans only.
</EXTREMELY-IMPORTANT>

**Phase 1: Implicit requirements discovery.**
If spec has `## Codebase Context`, use as ground truth. Scan feature for
gaps — surface them as `decisions[]` rather than interrupting with
questions.

**Phase 2: Write plan YAML.**
Write `<feature-id>.plan.yaml` per `docs/plan-file-schema.md`. Include
`problem`, `steps[]` (with `test_plan` and `coverage_min` each), and
`decisions[]` (with `confidence` and `ask_user`).

**Phase 3: Print terminal summary.**

<HARD-GATE>
Print a condensed terminal summary (≤ 30 lines). See sp-planner template
for exact format. End with multi-choice ask for any `ask_user: true`
decisions, or a confirmation prompt if all decisions are high-confidence.

WAIT for user response. For each `ask_user: true` decision, fill
`decisions[].user_decision` in the YAML file with the user's choice.
Do NOT proceed to Step 3 until all user_decision fields are populated.
</HARD-GATE>

---

## Step 3: Generator Role

<EXTREMELY-IMPORTANT>
Switch to Generator mindset. You are implementing, NOT designing. Follow
the plan. Do not redesign. If the plan seems wrong, mark the step
BLOCKED — do not fix the plan yourself.
</EXTREMELY-IMPORTANT>

Read `<feature-id>.plan.yaml` (Planner section + user_decisions). For
each step:
- Follow `approach` as guidance
- TDD cycle: test first, verify fail, implement, verify pass
- Commit after each step using `[module]: description`

Append to the same YAML file:
- `execution` — status/confidence/notes/commits per step
- `unplanned_changes` — any code change not mapped to a step
- `flags_for_eval` — concerns for Evaluator to focus on

**No terminal output from Generator role.** Proceed directly to Step 4.

---

## Step 4: Evaluator Role

<EXTREMELY-IMPORTANT>
Switch to Evaluator mindset. You are a RED TEAM. Your job is to FIND
PROBLEMS in code YOU JUST WROTE. This is the hardest part — you must
actively fight the urge to approve your own work.

**Self-persuasion is your enemy.** RESIST.
</EXTREMELY-IMPORTANT>

**Mandatory adversarial protocol for single-agent mode:**

1. Re-read Self-Persuasion Traps (in sp-evaluator template).
2. **Cool-down:** Re-read spec and plan YAML from scratch. Do NOT rely
   on memory of what you implemented.
3. **Zero-issue rule:** Zero issues first pass → mandatory second pass
   hunting edge cases, error paths, hardcoded values, race conditions.

**Round determination:** Check `eval.rounds[]` in the plan file. If
absent, this is Round 1. Otherwise Round N+1. Max rounds = 5.

**Round 1 — Initial evaluation:**
- Closure check (user_decisions honored, missing items, confidence mismatches,
  unplanned_changes review)
- Test design + execution: per step, design tests from `test_plan`,
  write to `tests/<feature-id>/`, run, record coverage
- Verdict: PASS iff all clean; ITERATE otherwise with concrete blockers

**Round 2+ — Replay and regression:**
- Replay prior-round failing tests
- Full rerun to detect regressions
- Verdict: PASS iff clean and no regressions; ITERATE otherwise

**After PASS — Optimization pass:**
- Append `eval.optimization` with non-blocking suggestions

Append `eval.rounds[N]` (and optionally `eval.optimization`) to the YAML.

**Print terminal summary** per sp-evaluator template. Both blocks
below are decision touch-points per
`docs/decision-touchpoint-protocol.md` — option lines are full
plain-language consequences, never bare labels. Blockers above must
read in plain language with no bare spec IDs.

For ITERATE:
```
→ Your call:
  (a) Switch back to Generator role and fix the <N> blocker(s) above —
      address each, then a new Round runs.
  (b) Force-merge anyway — ship as-is, listed blockers stay open;
      you own the risk and the followup.
  (c) Replan from scratch — current plan is archived, Planner role
      re-runs and may produce different steps.
```

For PASS + optimization:
```
→ Your call:
  (a) Accept and merge — feature ships now, optimization suggestions
      stay as ideas in the plan YAML for later.
  (b) Switch back to Generator role and apply optimizations first —
      a final Round verifies, then ship.
```

---

## Step 5: Handle Verdict

### (a) on ITERATE — fix and re-eval
Switch back to Generator role (Step 3). Address blockers. After Generator
re-runs, switch to Evaluator role (Step 4, Round N+1).

### (b) on ITERATE — force-merge
Skip remaining rounds, go to MERGE path below.

### (c) on ITERATE — replan
Archive current plan file to `archive/<feature-id>/<feature-id>.iter-<N>.plan.yaml`.
Return to Step 2 with `iteration: N+1`.

### (a) on PASS — merge
1. Mark feature passing:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/mutate.py" \
     mark-passing <feature-id>
   ```
2. Move `active/<feature-id>.plan.yaml` → `archive/<feature-id>/<feature-id>.plan.yaml`
3. If `supersedes` non-empty: extract spec's Supersession Plan, save to
   `archive/<feature-id>/supersession.json`
4. Commit using the humanized template. Fetch display_name first:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" \
     get <feature-id> --format=json
   ```
   Parse `display_name` (fall back to `<feature-id>` if missing). Then:
   `[features]: complete "<display_name>" (<feature-id>)`
5. Return to feature-tracker

### (b) on PASS — optimize
Switch back to Generator role, apply optimization suggestions. Then back
to Evaluator (Round N+1 for verification).

### Max Rounds Escalation

If Round 6 would trigger, write blocker "Max rounds exceeded", ITERATE
verdict, and print:

```
⚠️ 5 rounds completed and blockers still present. The plan may be
   fundamentally wrong — five attempts have not converged.

→ Your call:
  (a) Keep iterating into Round 6 — Generator role addresses current
      blockers; we may converge or hit the same wall again.
  (b) Replan from scratch — current plan is archived, Planner role
      re-runs with full knowledge of the round history (best when
      blockers look like the wrong design, not buggy execution).
  (c) Force-merge as-is — ship with the listed blockers open, you
      own the risk; pick this only if blockers turn out to be
      cosmetic or out-of-scope.
```

---

## When to Use Single-Agent vs Three-Agent

| Factor | Single-Agent | Three-Agent |
|--------|-------------|-------------|
| Project complexity | Simple to moderate | Complex |
| Context sharing | Roles share context (pro: continuity; con: self-persuasion) | Isolated (pro: independence; con: context loss) |
| Token cost | Lower (one session) | Higher (3 subagents) |
| Evaluation rigor | Weaker (self-assessment bias) | Stronger (independent evaluator) |
| Speed | Faster (no dispatch overhead) | Slower (subagent startup) |

**Default recommendation:** three-agent for new projects; single-agent
for quick fixes, prototypes, or constrained token budget.

To switch: use `sp-harness:switch-dev-mode`.
