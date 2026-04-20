# Plan File Schema

The shared communication file for Planner, Generator, and Evaluator.

**Location:** `.claude/agents/state/active/<feature-id>.plan.yaml`

Each agent appends to this single file. Fields are scoped to agent ownership
— no agent modifies another agent's section. This is the source of truth
across the entire development cycle.

**User never reads this file directly.** Each agent is responsible for
producing a condensed human-readable terminal summary for user review.
The YAML file is for machine-to-machine communication.

---

## Full Schema

```yaml
plan_id: <feature-id>                # required, matches features.json id
iteration: <integer>                  # starts at 1, increments on replan
based_on: <spec-doc-path>             # e.g. docs/design-docs/2026-04-20-auto-archive-design.md

# ============================================================
# PLANNER section — written once, locked after Planner done
# ============================================================

problem: |
  <1-2 sentences in natural language, STAR-informed but not labeled>
  <planner's own paraphrase, not copied from user request>

steps:
  - id: S1                            # sequential: S1, S2, S3, ...
    desc: <short name, ~5 words>
    approach: |
      <natural language, how this step solves its goal>
    files:
      create: [<path>, ...]
      modify: [<path>, ...]
      test:   [<path>, ...]
    test_plan:                        # high-level test strategy (Evaluator細化)
      - <scenario 1>
      - <scenario 2>
    coverage_min: <0-100>             # per-step minimum % for Eval to accept

decisions:
  - id: D1                            # sequential: D1, D2, D3, ...
    question: <what needs deciding>
    planner_view: <chosen option>
    confidence: <0-100>               # planner's subjective confidence
    rationale: <why this choice>
    alternatives:
      - option: <name>
        rejected_because: <reason>
    ask_user: <bool>                  # true if confidence < 70, or forced by gravity
    user_decision: null               # populated by orchestrator after user answers

# ============================================================
# GENERATOR section — appended after Planner done + user answers
# ============================================================

execution:
  S1:
    status: done | skipped | blocked
    confidence: <0-100>               # generator's post-hoc confidence
    notes: <natural language>
    commits: [<sha>, ...]             # git commits made during this step
  S2:
    ...

unplanned_changes:
  - loc: <file path>
    what: <description>
    reason: <why done outside plan>
    confidence: <0-100>

flags_for_eval:
  - <concern to verify>               # free text, generator points eval at hot spots

# ============================================================
# EVALUATOR section — appended per round
# ============================================================

eval:
  rounds:
    - round: <integer>                # starts at 1
      closure_check:
        user_decisions_honored:
          - id: D1
            verified: <bool>
            evidence: <what was checked>
        missing_plan_items: [<step id>, ...]
        confidence_mismatches:
          - step: <id>
            claimed: <0-100>
            actual: <description>
        unplanned_accepted: [<change id or description>]
        unplanned_rejected: []
      
      tests:
        <step-id>:
          pass: <int>
          fail: <int>
          coverage: <0-100>
          tests_file: tests/<feature-id>/<test_file>.py
          failures:                   # detailed, user doesn't read this
            - name: <test name>
              input: <description>
              expect: <expected>
              actual: <observed>
      
      blockers:                       # human-readable descriptions
        - <blocker 1>
      
      regressions:                    # Round 2+ only
        - step: <id>
          was_passing: true
          now_failing: <description>
      
      verdict: ITERATE | PASS
  
  optimization:                       # only if any round verdict == PASS
    suggestions:
      - loc: <file>
        what: <improvement>
    final_verdict: MERGE_READY | USER_WANTS_OPTIMIZATION
```

---

## Agent Write Permissions

| Section | Planner | User (via orch) | Generator | Evaluator |
|---------|---------|-----------------|-----------|-----------|
| `plan_id`, `iteration`, `based_on` | write | — | — | — |
| `problem`, `steps` | write | — | — | — |
| `decisions[].question/view/confidence/rationale/alternatives/ask_user` | write | — | — | — |
| `decisions[].user_decision` | — | write | — | — |
| `execution`, `unplanned_changes`, `flags_for_eval` | — | — | write | — |
| `eval.rounds[]`, `eval.optimization` | — | — | — | write (append) |

Violations of this table are schema errors — agents must refuse to write
outside their section.

---

## Round vs Iteration

- **Round** = one Evaluator cycle (after Generator's first implementation
  or after a bug-fix). Rounds accumulate in `eval.rounds[]`.
- **Iteration** = full replan (new `plan_id.plan.yaml` or increment `iteration`
  field). Triggered only when user chooses "replan" — Generator can't
  satisfy the plan after multiple rounds.

Max rounds per iteration = 5. Beyond that, orchestrator MUST escalate to
user with 3 choices: keep iterating / replan / force-merge.

---

## File Lifecycle

1. **Planner** creates the file at `.claude/agents/state/active/<feature-id>.plan.yaml`.
2. **Orchestrator** fills `decisions[].user_decision` based on user answers to
   Planner's terminal asks.
3. **Generator** reads the file, implements, appends `execution`,
   `unplanned_changes`, `flags_for_eval`.
4. **Evaluator** reads the file, runs tests, appends a new `eval.rounds[]` entry.
5. If ITERATE and user picks "fix": Generator updates its sections
   (by appending a new round within same execution or resetting step status).
   Evaluator appends a new round. Repeat.
6. On PASS: Evaluator runs optimization phase, appends `eval.optimization`.
7. On merge: file is archived to `archive/<feature-id>/<feature-id>.plan.yaml`.
8. On replan: file moves to `archive/<feature-id>/<feature-id>.iter-<N>.plan.yaml`,
   fresh file created with `iteration: N+1`.

---

## Terminal Output Conventions

Each agent produces a human-readable summary to terminal (NOT by dumping this
file). Schema-conformant agent templates define exactly what the terminal
should contain. The file is for agents; the terminal is for the user.

Design principles for terminal output:
1. **Never dump raw YAML** — user reads natural language + multi-choice
   decisions only.
2. **Ask only what must be asked** — decisions with `ask_user: false` are
   shown as FYI, not as questions.
3. **One decision per touch point** — never more than one multi-choice per
   terminal output.
4. **Details in the file, signals in the terminal** — test failure input/output
   goes to file; user sees failure names or high-level description.

---

## Examples

See `docs/design-docs/` for working examples (none yet — this schema is new
as of 2026-04).
