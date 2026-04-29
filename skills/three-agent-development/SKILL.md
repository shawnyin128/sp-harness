---
name: three-agent-development
description: |
  Feature-level orchestration with three independent agents: Planner (design),
  Generator (execution), and Evaluator (quality assessment). Agents communicate
  through a single shared YAML plan file per feature. User reviews condensed
  terminal output at three touch points: Plan review, per-round Eval review,
  and Optimization review. Explicitly triggered by feature-tracker or user.
author: sp-harness
version: 3.1.0
---

# Three-Agent Development

Three independent agents develop a feature through a shared YAML plan file.
Each agent reads and appends to the same file; the orchestrator drives the
flow and manages user interaction at three touch points.

```
Planner   → writes plan.yaml (problem, steps, decisions)
            → terminal: condensed summary + ask for low-confidence decisions
            → user decides → orchestrator fills user_decision
Generator → reads plan.yaml, implements, appends execution/unplanned/flags
            → NO terminal output (invisible to user)
Evaluator → reads plan.yaml, runs tests, appends eval.rounds[]
            → terminal: closure + tests + blockers-or-optimization
            → user decides → iterate (back to Generator) or merge
```

---

## File Structure

Single shared YAML per feature: `.claude/agents/state/active/<feature-id>.plan.yaml`.
Schema defined in `${CLAUDE_PLUGIN_ROOT}/docs/plan-file-schema.md`.

Active work lives in `active/`. Completed features archive to `archive/<feature-id>/`.

```
.claude/agents/state/
├── active/
│   └── <feature-id>.plan.yaml        ← the shared file
└── archive/
    └── <feature-id>/
        ├── <feature-id>.plan.yaml    ← final plan file
        ├── <feature-id>.iter-<N>.plan.yaml  (if replanned)
        └── supersession.json          (if feature has supersedes)
```

Permanent tests (written by Evaluator) live at `tests/<feature-id>/` and
survive as regression guards after merge.

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
directly without going through feature-tracker, and because
orchestrator output (Plan review, Round verdicts, Optimization review)
goes through the main session.

---

## Step 1: Select Feature

Read the feature from `.claude/features.json` (passed by feature-tracker, or
specified by user). Read context: `CLAUDE.md`, spec document referenced in
CLAUDE.md's Design Docs section (if any). Check `active/` for in-progress
state from a prior interrupted session.

---

## Subagent Dispatch Contract

Every Step 2 / Step 3 / Step 4 dispatch in this orchestrator follows
the same shape: launch a fresh `general-purpose` subagent and instruct
it to invoke the role skill before any other tool call. The canonical
prompt template:

```
You are dispatched as a fresh general-purpose subagent for the
sp-harness three-agent development pipeline. Your role for this turn
is <Planner|Generator|Evaluator>.

Your first action MUST be:

  Skill(sp-harness:sp-<role>-role)

Read that skill end-to-end before any other tool call. Follow its
rules exactly. The plan YAML for this feature is at:

  .claude/agents/state/active/<feature-id>.plan.yaml

Feature id: <feature-id>
<role-specific extras: prior-round eval section, blockers list, etc.>

Do not improvise. Do not skip any HARD-GATE in the role skill.
```

**Retry-with-stronger-prompt protocol.** After the subagent returns,
inspect its tool-use sequence. If `Skill(sp-harness:sp-<role>-role)`
was not the first invocation, the subagent skipped the role skill and
ran free-form. The orchestrator MUST:

1. Retry the dispatch ONCE with a stronger prompt that says: "Your
   previous attempt did not invoke the required role skill before
   acting. That run is rejected. Start over: invoke
   Skill(sp-harness:sp-<role>-role) FIRST, then act."
2. If the second attempt also skips the invocation, mark the phase
   `BLOCKED: dispatch failure` in the plan YAML and surface the
   blocker to the user. Do not run a third attempt automatically.

This dual-pass guard is the only structural defense against the
subagent ignoring the role-skill contract. Keep both halves of the
contract — first action MUST be Skill(...) AND retry-on-skip — across
all three Step dispatches.

---

## Step 2: Dispatch Planner

Dispatch a fresh general-purpose subagent that invokes the Planner role
skill. Use the canonical dispatch contract documented in
"## Subagent Dispatch Contract" below.

```
Agent(
  subagent_type='general-purpose',
  prompt=<canonical dispatch prompt with role='Planner' and
          target skill 'sp-harness:sp-planner-role'>
)
```

The role skill (sp-harness:sp-planner-role) owns Phase 1 (implicit
requirements discovery), Phase 2 (plan YAML production), and Phase 3
(terminal summary). The orchestrator does not duplicate any of that
content.

### Touch Point 1: User reviews Plan

Planner's terminal output ends with one of:

- **Multi-choice ask** (if any decision has `ask_user: true`): user picks
  option for each high-gravity decision.
- **Confirmation** (if all decisions are high-confidence): user says
  yes/no/adjust.

<HARD-GATE>
The orchestrator (YOU — not the Planner subagent) MUST:

1. Wait for user response to Planner's ask.
2. For each `ask_user: true` decision, capture the user's choice.
3. Write the user's choice into `decisions[].user_decision` in the plan
   YAML file. Use `yq` or direct edit (preserve schema).
4. Do NOT dispatch Generator until all `ask_user: true` decisions are
   filled. If user chose "adjust", go back to Step 2 (re-dispatch Planner
   with the user's feedback).
</HARD-GATE>

---

## Step 3: Dispatch Generator

Dispatch a fresh general-purpose subagent that invokes the Generator
role skill. Use the canonical dispatch contract documented in
"## Subagent Dispatch Contract" below.

```
Agent(
  subagent_type='general-purpose',
  prompt=<canonical dispatch prompt with role='Generator' and
          target skill 'sp-harness:sp-generator-role'>
)
```

The role skill (sp-harness:sp-generator-role) owns the per-step TDD
cycle, commit-after-each-step discipline, and the
`execution` / `unplanned_changes` / `flags_for_eval` appends to the
plan YAML. Generator produces no terminal output — there is no Touch
Point between Generator and Evaluator.

After Generator completes, proceed immediately to Evaluator.

---

## Step 4: Dispatch Evaluator

Dispatch a fresh general-purpose subagent that invokes the Evaluator
role skill. Use the canonical dispatch contract documented in
"## Subagent Dispatch Contract" below.

```
Agent(
  subagent_type='general-purpose',
  prompt=<canonical dispatch prompt with role='Evaluator' and
          target skill 'sp-harness:sp-evaluator-role'>
)
```

The role skill (sp-harness:sp-evaluator-role) owns the mandatory
adversarial protocol, Round determination, closure + test design +
execution, the optional Optimization pass, and both per-verdict
terminal summary fences (ITERATE / PASS+optimization). The
orchestrator only routes the user's response.

### Touch Point 2: User reviews Eval

The role skill's terminal verdict block is a decision touch-point per
`${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md`. The role
skill owns the canonical option lines (full-sentence consequences, no
bare labels). After it ends with the user's choice, the orchestrator
reads the latest `eval.rounds[N].verdict` field from the plan YAML and
routes per the user's selection:

- `(a)` on ITERATE → back to Step 3 (Generator fixes, Round N+1 follows)
- `(b)` on ITERATE → force-merge path (see Step 5 PASS)
- `(c)` on ITERATE → replan: archive current plan file to
  `archive/<feature-id>/<feature-id>.iter-<N>.plan.yaml`, go to Step 2
  with `iteration: N+1`
- `(a)` on PASS → merge (Step 5 PASS)
- `(b)` on PASS → Generator iterates on optimization suggestions, then
  back to Step 4 for re-verification

### Max Rounds Safeguard

If Round 6 would be triggered (5 rounds completed without PASS), the
Evaluator writes a blocker "Max rounds exceeded" and forces ITERATE.
Orchestrator escalates to user explicitly:

<!-- lint:disable=R7 -->
```output-template
⚠️ 5 rounds completed and blockers still present. The plan may be
   fundamentally wrong — five attempts have not converged.

→ Your call:
  (a) Try one more iteration — Generator addresses current
      blockers; we may converge or hit the same wall again.
  (b) Replan from scratch — current plan is archived, Planner re-runs
      with full knowledge of the round history (best when blockers
      look like the wrong design, not buggy execution).
  (c) Force-merge as-is — ship with the listed blockers open, you
      own the risk; pick this only if blockers turn out to be
      cosmetic or out-of-scope.
```

---

## Step 5: Handle Final Verdict

### MERGE (user accepted PASS or force-merged)

1. Mark feature passing:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/mutate.py" \
     mark-passing <feature-id>
   ```
2. Archive state files:
   - Create `.claude/agents/state/archive/<feature-id>/` if missing
   - Move `active/<feature-id>.plan.yaml` → `archive/<feature-id>/<feature-id>.plan.yaml`
   - Any prior iteration files already in archive stay put
3. If feature has `supersedes` non-empty: extract the spec's
   `## Supersession Plan` section, save to
   `archive/<feature-id>/supersession.json` (schema below). This is what
   sp-feedback Mode A reads to audit stale artifacts later.

```json
{
  "superseded_features": ["..."],
  "source_paths_removed": ["..."],
  "artifacts_handled": [
    {"path": "...", "action": "DELETE|MIGRATE", "destination": "..."}
  ],
  "verification_patterns": ["grep pattern", "..."]
}
```

4. Commit using the humanized template. Fetch display_name first:
   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" \
     get <feature-id> --format=json
   ```
   Parse `display_name` (fall back to `<feature-id>` if missing). Then:
   `[features]: complete "<display_name>" (<feature-id>)`
   (include features.json + archive/)
5. Return to feature-tracker

### REPLAN (user picked (c) on ITERATE)

1. Move current active plan to
   `archive/<feature-id>/<feature-id>.iter-<N>.plan.yaml`
2. Return to Step 2 with `iteration: N+1`

### REJECT (Evaluator hits diverging pattern or user abandons)

1. Stop. Preserve all files in `.claude/agents/state/active/`.
2. Report to user: what was attempted, why it failed, full Evaluator
   assessment.

---

## Agent Independence

1. Planner never reads `execution` or `eval` sections (except on replan,
   reads prior `eval.rounds[].blockers` to inform redesign).
2. Generator never reads `eval` section.
3. Evaluator reads everything but writes only to `eval`.
4. All communication through the single shared YAML file.
5. Each agent refuses to write outside its owned section (per schema's
   Write Permissions table).

---

## User Touch Points Summary

| Touch | When | Decision |
|---|---|---|
| 1 (Plan) | After Planner writes plan.yaml | Pick options for ask_user decisions, or confirm |
| 2 (Eval Round N) | After each Eval round | Fix / force-merge / replan (on ITERATE); Accept / optimize (on PASS) |
| 2' (Max rounds) | After 5 rounds without PASS | Keep iterating / replan / force-merge |

All touch points are multi-choice questions in terminal, ≤ 3 options.
Typical feature has 2-3 touch points. Each touch costs <1 min of user time.

---

## Role Skills

The three roles dispatched by this orchestrator are skills, not
project-level agent files:

- `skills/sp-planner-role/SKILL.md` — Planner role
- `skills/sp-generator-role/SKILL.md` — Generator role
- `skills/sp-evaluator-role/SKILL.md` — Evaluator role

They are plugin-distributed automatically. There are no
`.claude/agents/sp-*.md` files to manage.

To switch dev_mode (single-agent vs three-agent), use
`sp-harness:switch-dev-mode`.
