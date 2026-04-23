# Skill Routing Audit (MVP)

A reusable harness that checks whether sp-harness skills are triggered
correctly for given user messages. Built for v0.8.x boundary-optimization
work. See [the design spec](../../docs/design-docs/2026-04-23-skill-routing-mvp-design.md)
for the full rationale.

## What this does

For each scenario in `corpus/`:

1. Substitutes the scenario body into `prompt-template.txt` (which contains
   the full sp-harness skill index + routing rules).
2. Sends the prompt to a headless `claude --print --max-turns 1` subprocess,
   **three times in parallel**.
3. Parses the fenced JSON response from each vote.
4. Classifies the scenario's verdict by vote distribution.

The three-vote design converts Claude's non-determinism into a useful
signal: scenarios where Claude can't consistently decide ARE the scenarios
whose skill descriptions need clarification.

## Quick start

```bash
# Run every scenario in corpus/
./audit.sh

# Run one scenario (by filename stem)
./audit.sh --scenario=flaky-login-test
```

Exit code: `0` if all scenarios PASS or PASS-WEAK, `1` if any FAIL or FLAKY.

## Adding a scenario

One scenario = one `.md` file in `corpus/`. Filename stem should match the
`id` field.

```markdown
---
id: flaky-login-test
expected: systematic-debugging
---
The login test is flaky — sometimes passes, sometimes times out. Fix it.
```

Two required frontmatter fields:

- `id` — kebab-case identifier, matches filename stem.
- `expected` — the skill name you expect Claude to pick, OR the literal
  string `none` (for explicit scoped edits that shouldn't trigger a skill),
  OR `ASK-USER` (for genuinely ambiguous prompts that should make Claude
  ask first).

Body (below the closing `---`) is the user message text. Freeform.

## Verdicts

Per scenario, across 3 votes:

| Verdict | Meaning | What to do |
|---|---|---|
| **PASS** | 3/3 votes matched `expected` | ✅ routing is stable |
| **PASS-WEAK** | 2/3 matched | ⚠️ minor flake; may warrant attention if it degrades |
| **FAIL** | 1/3 matched, OR 0/3 with consensus on a wrong skill, OR all 3 unparseable | ❌ routing is broken or description is wrong |
| **FLAKY** | 0/3 matched AND the parseable votes disagree with each other | ⚠️ description is ambiguous — Claude can't decide |

A FLAKY verdict is often more actionable than FAIL: it directly identifies
a skill pair whose descriptions need disambiguation.

## Limitations (deliberate, per MVP spec)

- **No CI / nightly run.** Run manually when you want. CI integration is a
  future feature.
- **No baseline diff.** No automatic regression detection across runs. Each
  audit is independent.
- **No confusion matrix / per-skill metrics.** Just the per-scenario table.
- **`prompt-template.txt` is hand-maintained.** When skill descriptions
  change in `skills/**/SKILL.md`, the template must be updated by hand.
  Drift risk is acknowledged; auto-regen is a future feature.
- **Corpus is flat.** No `canonical/boundary/adversarial/negative` split —
  every scenario is simply `<id>.md` under `corpus/`.

## Dependencies

- `claude` CLI on PATH (the Claude Code headless runner).
- Python 3.9+ (stdlib only). Handles parsing, timeouts, and parallelism —
  no GNU coreutils dependency.

The runner does a preflight check and exits with a clear error if either
is missing.

## Baseline — 2026-04-23

First full run of the 12-scenario seed corpus against `claude` CLI 2.1.118:

```
Summary: 11 PASS · 0 PASS-WEAK · 1 FAIL · 0 FLAKY
```

Known issue surfaced:

- **`add-dashboard-roadmap`** (expected `manage-features`, got `manage-todos ×3`).
  Prompt: *"Also a bigger idea worth brainstorming eventually: a self-service
  dashboard so users can manage their own API keys. Too big for today, park it."*
  Claude consistently reads this as a reminder-to-self rather than a feature-scale
  idea. Root cause: the Memory Discipline decision order distinguishes step 4
  (pending tasks → `manage-todos`) from step 5 (feature-scale → `manage-features`),
  but the `manage-todos` vs `manage-features` skill descriptions do not clearly
  demarcate "todo scale" vs "feature scale". **This is a real v0.8.x
  boundary-tightening target**, not a framework bug. Scenario kept as-is to
  serve as the regression marker.

## Files

```
tests/skill-routing/
  corpus/*.md            scenarios (frontmatter + body)
  prompt-template.txt    skill index + routing rules + {{SCENARIO}} placeholder
  audit.sh               runner — parallel votes per scenario, feeds tally.py
  tally.py               classifier + terminal report
  README.md              this file
```
