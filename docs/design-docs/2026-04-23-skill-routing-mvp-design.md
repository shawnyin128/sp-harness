# Skill Routing Audit MVP — Design Spec

**Date**: 2026-04-23
**Status**: Approved for implementation
**Seed todo**: `build-systematic-skill-boundary-evaluation-methodology-and-a`

## Problem

sp-harness has ~30 skills. Their descriptions compete to match user
messages, and we currently have no repeatable way to detect:

- **Description overlap** — two skills plausibly trigger on the same prompt
- **Incorrect triggering** — skill triggers when it shouldn't, or fails to trigger when it should
- **Regressions** — a description edit silently breaks previously-correct routing

The v0.8.0 ad-hoc audit (42-scenario pilot across Phase 1 and Phase 2)
found real boundary bugs (e.g., `dispatching-parallel-agents` vs
`subagent-driven-development` overlap) but was manual, one-shot, and not
reusable. v0.8.x is dedicated to building the reusable framework. **This
spec defines the MVP only**; advanced features (CI, baseline diff,
metrics) are explicitly deferred to follow-up iterations.

## Architecture Type

**Hybrid** — deterministic code orchestrates, non-deterministic agent
judges a single scenario's routing.

## Hybrid Boundary

### Component ownership

| Layer | Responsibility |
|---|---|
| Code (bash + Python, in `tests/skill-routing/`) | corpus loading, runner loop, voting aggregation, terminal report |
| Agent (headless `claude --print`, blank session each call) | given one scenario + full skill index + routing rules, output one JSON with chosen skill |

Agent components start from blank session each run. No CC subagent
definitions, no persistent memory, no skill-loading mechanism — the agent
receives everything it needs in the prompt itself.

### Interface contract

**Code → Agent**: the runner constructs a prompt by substituting the
scenario body into `prompt-template.txt` and piping it to
`claude --print --max-turns 1` via stdin.

**Agent → Code**: the response text must contain a single fenced JSON block:

```json
{
  "primary_skill": "<skill-name or 'none'>",
  "rationale": "<1-2 sentence explanation>"
}
```

Anything else in the response is ignored. The first fenced block matching
this schema is taken as the answer.

### Orchestrator

Code drives. For each scenario, code spawns 3 parallel CLI subprocesses,
collects outputs, runs `tally.py` to aggregate votes and classify the
verdict.

### Failure asymmetry

- Agent returns no parseable JSON block → retry the CLI call once. If the
  second attempt also fails, count the vote as `unparseable`. Scenario
  continues with the remaining 2 votes.
- CLI timeout (hard cap 30s per call) → count as `timeout`.
- CLI non-zero exit → same as `unparseable`.
- The run never aborts due to one scenario's problems. Always emits a
  full report.

## MVP Scope

**In scope**:

- Corpus format: YAML frontmatter + prompt body in `.md` files
- Runner script (bash) with parallel CLI calls and 3-of-3 voting
- Tally script (Python) with terminal report
- Prompt template (skill index + `using-sp-harness` routing rules), hand-maintained
- Seed corpus of 10-12 scenarios (reused from v0.8.0 Phase 1/2 pilot)
- README explaining how to run and how to add scenarios

**Explicitly deferred (do NOT build in MVP)**:

- CI workflow or nightly run
- Baseline + regression diff
- Confusion matrix / precision-recall / per-skill metrics
- Multi-category corpus (canonical / boundary / adversarial / negative subdirs)
- `audit` sp-harness skill wrapper for in-session use
- JSON or markdown report formats
- Expansion to full ~30-skill canonical coverage
- Auto-regeneration of prompt template from current `skills/**/SKILL.md`

These may become separate features in later v0.8.x iterations after the
MVP surfaces what actually matters in practice.

## Corpus Format

One scenario = one `.md` file in `tests/skill-routing/corpus/`.

```markdown
---
id: <kebab-case, matches filename stem>
expected: <skill-name or 'none'>
---
<raw user message, freeform text, any length>
```

Two required fields only. Additional fields (rationale, tags, expected
secondary) may be added later when we know we need them.

## Runner Logic

### `audit.sh`

```
for scenario in corpus/*.md:
  parse frontmatter → id, expected
  extract body → prompt text
  substitute prompt into prompt-template.txt
  spawn 3 parallel `claude --print --max-turns 1` via stdin
  wait for all 3 (or timeout at 30s each)
  collect 3 outputs
  append (id, expected, outputs[]) to results

pass all results to tally.py
exit with tally.py's exit code
```

### `tally.py`

```
for each (id, expected, outputs) in results:
  votes = []
  for out in outputs:
    try extract fenced JSON block → parse → get primary_skill
    on failure: votes.append("unparseable")
    on success: votes.append(primary_skill)

  count_expected = sum(1 for v in votes if v == expected)
  distinct_valid = set(v for v in votes if v != "unparseable")

  classify:
    if count_expected == 3:                PASS
    elif count_expected == 2:              PASS-WEAK
    elif count_expected == 1:              FAIL
    elif len(distinct_valid) >= 2:         FLAKY    (votes disagree with each other → description ambiguous)
    else:                                  FAIL     (consensus on a wrong skill, OR all votes unparseable — reported with distinct_valid shown)

print terminal table
exit 0 if no FAIL/FLAKY, else exit 1
```

## Prompt Template

`tests/skill-routing/prompt-template.txt` contains, in order:

1. Auditor role preamble: "You are evaluating which sp-harness skill should trigger for this user message. Apply rules literally. Respond with a fenced JSON block only."
2. Full sp-harness skill index (name + description for each skill in `skills/`)
3. Relevant `using-sp-harness` sections: Feedback/adjustment classification (with the brainstorming bypass red-flag), Skill priority, the Memory Discipline sections
4. `{{SCENARIO}}` placeholder (replaced by runner with the prompt body)
5. Response format instruction: "Output exactly one fenced ```json block with keys `primary_skill` and `rationale`. Nothing else."

Hand-maintained in MVP. When skill descriptions change, the template must
be regenerated manually. A future iteration will automate this from
`skills/**/SKILL.md`.

## Terminal Report Format

```
Skill Routing Audit — 2026-04-23 22:15
Corpus: 12 scenarios

Scenario                    Expected             Got                      Verdict
─────────────────────────────────────────────────────────────────────────────────
flaky-login-test            systematic-debugging sys-debugging ×3         PASS
add-feature-spec            brainstorming        brainstorming ×3         PASS
tests-pass-done             verification-before  verification ×2, none ×1 PASS-WEAK
build-directly-no-pipeline  brainstorming        brainstorming ×3         PASS
...

Summary: 10 PASS · 2 PASS-WEAK · 0 FAIL · 0 FLAKY
```

Exit 0 if clean, exit 1 if any FAIL or FLAKY.

## Seed Corpus (MVP)

10-12 scenarios drawn from the v0.8.0 Phase 1/2 pilot, where ground truth
has already been validated. Proposed seeds:

| id | expected | source |
|---|---|---|
| flaky-login-test | systematic-debugging | Phase 2 C5 |
| hanging-after-evaluator | feedback | Test A2 |
| add-parallelize-plan-gen | brainstorming | Phase 1 S2 |
| start-next-feature | feature-tracker | Phase 1 S4 |
| change-max-retries-config | none | Phase 1 S5 |
| remind-rename-later | manage-todos | Phase 1 S6 |
| add-dashboard-roadmap | manage-features | Phase 1 S7 |
| review-branch-before-merge | requesting-code-review | Phase 1 S12 |
| reviewer-said-rename-x | receiving-code-review | Phase 1 S13 |
| health-check-sp-harness | framework-check | Phase 1 S14 |
| build-directly-no-pipeline | brainstorming | Test R2 (red-flag) |
| implement-password-reset-w-reqs | brainstorming | Test R1 (red-flag) |

## Divergence Risk Analysis

| Source | Probability | Impact | Mitigation |
|---|---|---|---|
| Claude CLI non-determinism | high | chain (wrong verdict) | 3-of-3 voting; FLAKY classification exposes ambiguous descriptions explicitly |
| Malformed JSON response | medium | local (one vote lost) | retry once, then mark `unparseable`, scenario continues with remaining votes |
| Skill index in prompt-template drifts from actual `skills/` | medium | local (stale routing signal, false-positive verdicts) | hand-maintain in MVP, document in README; auto-regen deferred to follow-up feature |
| CLI timeout/hang | low | local | hard 30s timeout per CLI call |

### Divergence tree (HIGH risk only)

```
Claude returns different skill across 3 votes
  → vote distribution wide
    → scenario classified FLAKY
      → surfaced in terminal report with "needs description work" label
      → author reviews scenario + skill descriptions for ambiguity
      → explicit signal, not silently masked failure
```

The voting design converts LLM non-determinism from a bug into a feature:
scenarios where Claude can't consistently decide ARE the scenarios where
the skill descriptions need clarification. FLAKY is a useful output, not
a test failure.

## Features

| id | category | priority | description | depends_on |
|---|---|---|---|---|
| `skill-routing-mvp-runner` | infrastructure | high | Create `tests/skill-routing/` with `audit.sh`, `tally.py`, `prompt-template.txt`, `README.md`. Implements 3-of-3 voting and terminal report. | — |
| `skill-routing-mvp-corpus-seed` | testing | high | Write 10-12 seed scenarios as `corpus/*.md` files using validated Phase 1/2 ground truth. Run `audit.sh` against seed; expect all PASS or PASS-WEAK. | `skill-routing-mvp-runner` |

Each feature is sized for a single session. Corpus-seed depends on runner
because verification requires the runner to exist.

## Supersession

None. `tests/skill-triggering/` and `tests/explicit-skill-requests/`
remain untouched in MVP. Consolidation with existing test infrastructure
is a future decision deferred until the MVP has proven its shape in use.

## Out-of-scope notes (for future iterations)

These notes are NOT requirements for MVP. They capture ideas that came up
during brainstorming and should be revisited when MVP is in use:

- Multi-category corpus (canonical / boundary / adversarial / negative) would give richer coverage metrics
- `audit` sp-harness skill wrapper would let `/audit` trigger the harness from inside a Claude Code session
- Baseline diff would catch silent regressions across skill description edits
- Confusion matrix would show systemic misrouting patterns
- Auto-regen of prompt template from `skills/**/SKILL.md` eliminates drift risk
- Potential consolidation with `tests/skill-triggering/` and `tests/explicit-skill-requests/`
