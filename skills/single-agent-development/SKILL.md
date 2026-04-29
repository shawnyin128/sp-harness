---
name: single-agent-development
description: |
  Feature development with a single agent playing all three roles (Planner,
  Generator, Evaluator) sequentially. Same pipeline as three-agent-development
  but without subagent dispatch — all phases run in the main session.
  Use when subagent overhead is unnecessary or for simpler projects.
author: sp-harness
version: 2.1.0
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
Schema defined in `${CLAUDE_PLUGIN_ROOT}/docs/plan-file-schema.md`.

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

## Step 0: Declare session language

**MUST run this before Step 1.** Read `.claude/sp-harness.json` and
extract the `language` field (default `match-input` if missing).
Print `Session language: <code>` as the first line of your reply for
this session. Then follow the rule for the remainder of the session:

- `match-input` (default) — reply in the user's input language each
  turn.
- Any specific code (`en`, `zh`, `ja`, ...) — pin replies to that
  language regardless of input.

In either mode, no code-mixing within a single message. Identifiers
(file paths, command names, field names, product names, IDs) stay in
their original form. Files / commits / docs / plan YAML always
English regardless of chat language.

This rule mirrors the one in feature-tracker Step 1 and the subagent
templates; it lives here because this SKILL is sometimes invoked
directly without going through feature-tracker.

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
Write `<feature-id>.plan.yaml` per `${CLAUDE_PLUGIN_ROOT}/docs/plan-file-schema.md`. Include
`problem`, `steps[]` (with `test_plan` and `coverage_min` each), and
`decisions[]` (with `confidence` and `ask_user`).

**Phase 3: Print terminal summary.**

<HARD-GATE>
Print a condensed terminal summary. Structure decides shape, self-check decides density — no global line cap. Use the canonical fence below; let the brief grow only as far as the decisions and steps demand.

This output is a **decision touch-point** and MUST follow
`${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md`. The fence
below is the authoritative format. Do NOT improvise headers, do NOT
collapse `Goal:` and `Approach:` into one line, do NOT use bare spec
IDs in place of plain-language labels. The same fence is the canonical
source in `agent-templates/sp-planner.md` Phase 3 — both copies MUST
stay byte-identical (regression test in
`tests/canonical-plan-summary-parity/`).

```output-template
📋 Plan: <display_name> (<feature-id|format>)

**Problem**
  <problem field, in plain prose — not spec vocabulary>

Plan (<N> steps):
  1. <desc>
     Goal: <what success looks like, plain language>
     Approach: <high-level approach in plain language>

  2. <desc>
     ...

**Key decisions**
  ⚠️ <one-sentence question in plain language>
    Background: <code/behavior state that triggered this — describe
                 the situation, not the spec section>
    What it controls: <observable behavior that changes by choice>
    My pick: (<x>) <option label> — <reason>, <confidence>%
    **Options**
      (a) <one-sentence consequence in plain language>
      (b) <one-sentence consequence in plain language>
      (c) <one-sentence consequence in plain language>

  ✓ <one-sentence question>
    → <planner pick in plain language> (<confidence>%)
  (⚠️ for ask_user: true; ✓ for decisions the planner already made)

→ Your call on the ⚠️ decisions above:
  (Same letters as the Options list above. If multiple ⚠️ decisions,
   prefix with the decision label, e.g. "D1 (a)". Translate any decision
   ID into a 3-6 word plain-language label the first time it appears.)
```

If no `ask_user: true` decisions, replace the final block with:

```
→ All decisions are high-confidence. Plan summary above.
  Proceed? (yes / no / adjust)
  · "no" stops here without writing code.
  · "adjust" lets you push back on any step or decision before Generator runs.
```

**Self-check before print:** re-read your draft against ALL of these.
If ANY check fails, rewrite before emitting.

  1. Section headers are literally `**Problem**`, `Plan (<N> steps):`,
     and `**Key decisions**`. NOT improvised variants like
     `Approach (3 steps)` or `Decisions (...)`.
  2. Every step has BOTH a `Goal:` line and an `Approach:` line.
  3. No bare `S\d+` / `D\d+` / `F\d+` token outside a parenthesized
     gloss. First mention gets a 3-6 word plain-language label inline,
     e.g. `D1 (file open mode default)`.
  4. No code-mixing across the chat language. Per Step 0, prose is
     pinned to ONE language. Identifiers (file paths, command names,
     field names, product names) stay in their original form;
     everything else follows the pinned language. English content
     words (verbs, nouns, adjectives) embedded in non-English prose,
     or vice versa, FAIL this check.
  5. No fancy/curly quotes (U+201C, U+201D, U+2018, U+2019). Use
     ASCII `"` and `'`. macOS smart-quote autocorrect is the typical
     leak source — reverse it before emitting.
  6. Apply the runtime self-check from `using-sp-harness/SKILL.md`
     "Output prose self-check": every first-occurrence short code is
     glossed inline.

End with the multi-choice ask for any `ask_user: true` decisions, or
the confirmation prompt above if all decisions are high-confidence.

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

**Self-check before print:** re-read each option line aloud as if to a
colleague unfamiliar with the project. If you would stumble on any
phrase or they would ask "what does that mean," rewrite it before
emitting. Also apply the specific-pattern self-check from
`using-sp-harness/SKILL.md` "Output prose self-check"
(project-internal short codes each glossed inline).

**Print terminal summary** per sp-evaluator template. Both blocks
below are decision touch-points per
`${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md` — option lines are full
plain-language consequences, never bare labels. Blockers above must
read in plain language with no bare spec IDs.

For ITERATE:
```output-template
→ Your call:
  (a) Switch back to Generator role and fix the <N> blocker(s) above —
      address each, then another evaluation runs.
  (b) Force-merge anyway — ship as-is, listed blockers stay open;
      you own the risk and the followup.
  (c) Replan from scratch — current plan is archived, Planner role
      re-runs and may produce different steps.
```

For PASS + optimization:
```output-template
→ Your call:
  (a) Accept and merge — feature ships now, optimization suggestions
      stay as ideas in the plan YAML for later.
  (b) Switch back to Generator role and apply optimizations first —
      a final evaluation verifies, then ship.
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

**Self-check before print:** even on this rare escalation path, apply
the runtime self-check from `using-sp-harness/SKILL.md` "Output prose
self-check" — every first-occurrence short code is glossed inline,
language pin honored, no fancy quotes. Option lines are full sentences
of consequence, never bare labels.

```output-template
⚠️ 5 rounds completed and blockers still present. The plan may be
   fundamentally wrong — five attempts have not converged.

→ Your call:
  (a) Try one more iteration — Generator role addresses current
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

**Default recommendation:** single-agent for most projects (faster, lower
token cost, simpler dispatch). Switch to three-agent when correctness
matters enough to pay for adversarial review by an isolated evaluator —
e.g. complex refactors, security-sensitive code, or projects where
subtle regressions are costly.

To switch: use `sp-harness:switch-dev-mode`.
