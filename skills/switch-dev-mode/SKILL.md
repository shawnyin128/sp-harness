---
name: switch-dev-mode
description: |
  Switch between single-agent and three-agent development modes by
  toggling the dev_mode field in .claude/sp-harness.json. Also detects
  leftover per-project agent files in .claude/agents/ (residue from
  pre-role-skill projects) and offers a one-time cleanup. Use when the
  user wants to change how features are developed.
author: sp-harness
version: 3.0.0
---

# switch-dev-mode

Two responsibilities, both narrow:

1. Flip the `dev_mode` field in `.claude/sp-harness.json` between
   `single-agent` and `three-agent`.
2. Detect leftover per-project subagent files at
   `.claude/agents/sp-{planner,generator,evaluator,feedback}.md` and
   offer a one-time cleanup.

The orchestrators (`skills/single-agent-development`,
`skills/three-agent-development`, `skills/feature-tracker`) now dispatch
role skills (`sp-planner-role`, `sp-generator-role`, `sp-evaluator-role`,
`sp-feedback-role`) directly. Per-project subagent files in
`.claude/agents/sp-*.md` are no longer read by anything in the pipeline
and should be removed from older projects.

## Steps

### 1. Read configuration

Read `.claude/sp-harness.json`. If the file is missing, create it with
the default contents below and treat the current mode as `single-agent`:

```json
{"dev_mode": "single-agent", "last_hygiene_at_completed": 0, "external_codebase": false, "language": "match-input"}
```

Capture the current `dev_mode` value as `current_mode` (one of
`single-agent` or `three-agent`) and compute `other_mode` as the opposite
value.

### 2. Ask whether to switch dev_mode

Print the current mode and ask whether to switch. This is a decision
touch-point per `${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md`
(structured menu — header line + plain-language consequences for each
option).

**Self-check before print:** apply the runtime self-check from
`using-sp-harness/SKILL.md` "Output prose self-check" — every
first-occurrence short code glossed inline, no fancy/curly quotes,
language pin honored. Re-read each option line aloud as if to a
colleague unfamiliar with the project; rewrite if any phrase reads
like jargon.

```output-template
Current dev_mode: <current_mode>

→ Switch dev_mode to <other_mode>?
  · yes — write <other_mode> back to .claude/sp-harness.json; the
          next feature run uses the new orchestration (only the
          isolation between Planner / Generator / Evaluator changes;
          both modes dispatch the same role skills).
  · no  — leave dev_mode as <current_mode>; nothing is written.
```

If the user picks `yes`: rewrite `.claude/sp-harness.json` with
`dev_mode` set to `other_mode`, preserving every other field
unchanged. If `no`: skip the write.

### 3. Detect leftover agent files

Regardless of the answer in step 2, look for these four exact paths:

- `.claude/agents/sp-planner.md`
- `.claude/agents/sp-generator.md`
- `.claude/agents/sp-evaluator.md`
- `.claude/agents/sp-feedback.md`

Do NOT recurse into `.claude/agents/state/`. Collect the paths that
exist into `stale_files`. If the list is empty, print a one-line
"no leftover agent files" confirmation and stop.

### 4. Offer one-time cleanup

If `stale_files` is non-empty, print the list and ask. This is a
decision touch-point per
`${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md`.

**Self-check before print:** apply the runtime self-check from
`using-sp-harness/SKILL.md` "Output prose self-check" — every
first-occurrence short code glossed inline, no fancy/curly quotes,
language pin honored. Re-read each option line aloud as if to a
colleague unfamiliar with the project; rewrite if any phrase reads
like jargon.

```output-template
Found leftover per-project agent files in .claude/agents/. The
orchestrators no longer read these — they dispatch role skills
(sp-planner-role, sp-generator-role, sp-evaluator-role,
sp-feedback-role) directly, so these files are inert.

  <each path in stale_files, one per line>

→ Remove these stale agent files?
  · yes — delete every listed file from .claude/agents/; nothing
          else in the project changes (state/ is untouched).
  · no  — keep them in place; they will not be used by any
          orchestrator, but framework-check will surface them again
          on the next health check.
```

On `yes`: delete each path in `stale_files`. Print a one-line
confirmation listing what was removed.

On `no`: print a one-line note that the files are inert and the
next framework-check will flag them again. Do not delete anything.

## Rules

1. The skill writes ONLY to `.claude/sp-harness.json` (toggle path) and
   deletes ONLY the four listed files in `.claude/agents/` (cleanup
   path). Nothing else in the project tree is touched.
2. The cleanup detection runs every invocation, independent of whether
   the user accepted the toggle in step 2 — the two questions are
   decoupled.
3. The four cleanup targets are fixed: `sp-planner.md`,
   `sp-generator.md`, `sp-evaluator.md`, `sp-feedback.md`. Other files
   under `.claude/agents/` (including `state/` and any unrelated `.md`
   files) are never considered stale by this skill.
