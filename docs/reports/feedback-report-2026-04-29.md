# Feedback Report — 2026-04-29 (Mode A)

Run trigger: feature-tracker exit branch — features.json shows 43/43
PASS after the orchestrator-refactor batch (create-role-skills,
refactor-{single,three,feedback}-orchestrator,
language-pin-emit-self-check-coverage, lint-r7-self-check-block-presence,
switch-dev-mode-migration-rewrite, framework-check-cat4-removal,
role-skills-test-suite-update).

## Context sources read

- CLAUDE.md
- .claude/features.json (43 features, all `passes: true`)
- .claude/sp-harness.json (`dev_mode: three-agent`, `language: zh`)
- .claude/memory.md (project session-buffer)
- .claude/agent-memory/sp-feedback/MEMORY.md (14 lines, no compact)
- .claude/sp-feedback-calibration.json (15 prior findings, 2 missed)
- skills/feature-tracker/SKILL.md, skills/feedback/SKILL.md,
  skills/sp-feedback-role/SKILL.md, skills/single-agent-development,
  skills/three-agent-development, skills/switch-dev-mode,
  skills/init-project
- .claude/agents/, agent-templates/
- skills/feature-tracker/scripts/print-brief.py
- .claude/agents/state/archive/role-skills-test-suite-update/role-skills-test-suite-update.plan.yaml
- tests/role-skill-dispatch-smoke/, tests/agent-file-migration/,
  tests/switch-dev-mode-migration-rewrite/
- git log --oneline -50

## Findings

### F1 — feature-tracker Mode A dispatch verb is stale

- **Dimension**: agent / spec drift
- **Root cause**: bug
- **Action**: fix_feature
- **Evidence**: skills/feature-tracker/SKILL.md L341–347 still says
  ```
  Dispatch `@agent sp-feedback` with `"mode": "A"`.
  ```
  Every other dispatch site in the orchestrator-refactor batch
  migrated to `Agent(subagent_type='general-purpose')` +
  `Skill(sp-harness:sp-feedback-role)` (see skills/feedback/SKILL.md
  L27–39 and skills/three-agent-development/SKILL.md "Subagent
  Dispatch Contract" L89). tests/role-skill-dispatch-smoke/
  test_dispatch_contract.py only covers skills/feedback Step 2 —
  feature-tracker's exit branch is unguarded. With
  .claude/agents/sp-feedback.md slated for removal (per
  switch-dev-mode), the legacy verb will dispatch into thin air on
  next ALL-PASS exit.
- **Suggestion**: rewrite feature-tracker SKILL.md Step 5 ALL-PASS
  branch to mirror skills/feedback/SKILL.md Step 2: dispatch a
  fresh general-purpose subagent invoking
  `Skill(sp-harness:sp-feedback-role)` with `mode='A'`, following
  the canonical Subagent Dispatch Contract and retry-with-stronger-
  prompt protocol. Extend tests/role-skill-dispatch-smoke/
  test_dispatch_contract.py with a feature-tracker case so this
  doesn't regress.

### F2 — `.claude/agents/sp-feedback.md` residue in this repo

- **Dimension**: code quality / dead docs
- **Root cause**: bug
- **Action**: fix_feature
- **Evidence**: `.claude/agents/sp-feedback.md` (18 KB) still present.
  The other three (sp-planner, sp-generator, sp-evaluator) were
  already removed. switch-dev-mode/SKILL.md L74–86 explicitly
  classifies all four `.claude/agents/sp-{planner,generator,
  evaluator,feedback}.md` paths as inert, never-read residue, with
  a `Remove these stale agent files?` cleanup prompt. The role
  skill at skills/sp-feedback-role/SKILL.md is now the canonical
  body; the `.claude/agents/sp-feedback.md` copy has already
  diverged (says "6 dimensions" vs role skill's "8 dimensions"),
  proving it is no longer maintained.
- **Suggestion**: delete `.claude/agents/sp-feedback.md`. Decision
  on whether to keep it as a test fixture: not needed —
  tests/agent-file-migration/test_migration.py already has its own
  tmpdir-seeded copy (see L114 `_seed_project`), so production
  removal does not break any test.

### F3 — init-project still emits per-project agent files that nothing reads

- **Dimension**: spec drift / architecture
- **Root cause**: architecture
- **Action**: manual
- **Evidence**: skills/init-project/SKILL.md Step 6a (L373–380)
  always writes `.claude/agents/sp-feedback.md` from
  `agent-templates/sp-feedback.md`; Step 6b (L382–416) writes
  `sp-planner.md` / `sp-generator.md` / `sp-evaluator.md` when the
  user picks three-agent. Per skills/switch-dev-mode/SKILL.md
  L23–28: "The orchestrators … now dispatch role skills … directly.
  Per-project subagent files in `.claude/agents/sp-*.md` are no
  longer read by anything in the pipeline." So init-project
  bootstraps a new project by writing four files that
  switch-dev-mode immediately wants to delete. The agent-templates/
  directory currently has one live consumer (init-project) and one
  drifting copy (the same content lives at skills/sp-*-role/SKILL.md).
- **Suggestion (decision required)**: pick one of three structural
  paths.
  (a) Retire the per-project agent files: drop init-project Step 6a
      / 6b's file emission; init-project still asks Q1 (dev_mode)
      and writes `dev_mode` into sp-harness.json, but emits no
      `.claude/agents/sp-*.md` files. Then `agent-templates/`
      becomes dead — delete it. Cleanest, eliminates the drift
      surface, but loses the customization knob (Q2 "walk through
      four config knobs" path, init-project SKILL.md L409–416).
  (b) Keep `agent-templates/` as the customization baseline, but
      relabel it: it's no longer the canonical agent body (the role
      skills are), it's an *override starting point* for projects
      that want to customize per-project. Document this in
      agent-templates/README.md and trim the body content down to
      just the customizable surface (model, tools, memory,
      worktree, project-context block).
  (c) Status quo. Accept that new projects bootstrap with stale
      copies that switch-dev-mode immediately cleans up, and that
      `agent-templates/` and `skills/sp-*-role/SKILL.md` will drift.
  Recommendation: (a) is the natural completion of the
  switch-dev-mode-migration-rewrite + create-role-skills batch.

### F4 — print-brief.py YAML parser misclassifies `Edge:` items

- **Dimension**: code quality / functional correctness
- **Root cause**: bug
- **Action**: fix_feature
- **Evidence**:
  `.claude/agents/state/archive/role-skills-test-suite-update/role-skills-test-suite-update.plan.yaml`
  has 5 steps (S1–S5, lines 26 / 69 / 115 / 140 / 163) and
  `eval.rounds[]` with PASS verdict — `print-brief.py` reports
  `Steps: 2 steps · 0 commits` and `Tests: 0 tests · avg —%
  coverage` instead. Reproduced. Trace shows the parser stops at
  S2 because S2's `test_plan` block contains items beginning with
  `- Edge: stale-files set is empty …` and `- Edge: only some of
  the four files …`. The bundled loader's
  `_MAPPING_ITEM_RE = ^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$`
  (skills/feature-tracker/scripts/print-brief.py:49) matches
  `Edge:` as a bare-identifier mapping key, so the plain-prose
  test_plan items get parsed as mapping items, which then
  desynchronizes the indent stack and aborts the outer steps[]
  sequence. Other archived plans (e.g.
  switch-dev-mode-migration-rewrite) avoid the trigger only by not
  using the `Edge:` prefix in their test_plan items — fragile.
- **Suggestion**: tighten the mapping-item heuristic in
  print-brief.py. Two viable shapes:
  (i) require the value to look like a typed value (quoted, or
      starts with `[`/`|`, or is a bare scalar that does not
      contain a space) to qualify as a mapping item; treat
      `Edge: free-form prose with spaces` as plain scalar.
  (ii) maintain a small allow-list of mapping keys legal at this
       indent level (id / desc / approach / files / test_plan /
       coverage_min, plus the eval-side keys), and only enter the
       mapping-item branch when the regex hit names a key in that
       list. Both close the bug; (i) is fewer assumptions about
       schema shape. Add a regression test against the
       role-skills-test-suite-update.plan.yaml fixture (steps == 5,
       rounds >= 1).

### F5 — `.claude/agents/sp-feedback.md` content has drifted from canonical role skill

- **Dimension**: spec drift / code quality
- **Root cause**: bug (subset of F2 cleanup)
- **Action**: manual (rolled into F2's fix_feature)
- **Evidence**: `.claude/agents/sp-feedback.md` L70 says "## Structured
  Checklist (6 dimensions)"; canonical
  skills/sp-feedback-role/SKILL.md L64 and
  agent-templates/sp-feedback.md L70 both say "8 dimensions" (added
  Section 7 supersession-staleness and Section 8 language-compliance
  in later features). Confirms `.claude/agents/sp-feedback.md` has
  been frozen since the per-project files stopped being read; F2's
  delete is the right resolution, no separate fix_feature needed.

### F6 — dev_mode flipped mid-session — investigation inconclusive

- **Dimension**: agent / functional
- **Root cause**: unknown
- **Action**: manual
- **Evidence**: per .claude/memory.md
  `dev-mode-flipped-mid-session`, sp-harness.json's `dev_mode`
  changed from `single-agent` to `three-agent` without a
  switch-dev-mode invocation. Investigation today:
  - `git log --oneline -- .claude/sp-harness.json` is empty (file
    is gitignored, so no audit trail).
  - `grep -rn "sp-harness.json" scripts/ skills/` finds 4 hits, all
    prose references in feature-tracker and switch-dev-mode SKILL.md
    bodies. Only switch-dev-mode/SKILL.md describes a write path,
    and that requires explicit user `yes` to Q1.
  - hooks/session-start and hooks/post-push-reminder do not touch
    sp-harness.json.
  - tests/agent-file-migration/test_migration.py and
    tests/switch-dev-mode-migration-rewrite/test_skill_rewrite.py
    operate against tmpdir copies via `_seed_project`, never against
    the real `.claude/sp-harness.json`.
  No write path identified. Most plausible explanation is an
  out-of-band `Edit` against sp-harness.json earlier in the session
  (e.g. during the switch-dev-mode-migration-rewrite feature itself,
  the agent may have manually flipped the field while iterating).
  Insufficient evidence to promote to a fix_feature; surface for
  user awareness only. If it recurs, capture the offending
  commit/tool-call so the writer can be identified.

## Memory bloat check

- sp-feedback MEMORY.md: 14 lines — no compact.
- sp-planner MEMORY.md: not checked this run (out of scope when
  no agent-specific finding routes there).
- sp-evaluator MEMORY.md: same.

## Memory pattern check

No new cross-feature meta-pattern emerged from this batch that
isn't already covered by the existing `single-agent-emit-weakest-link`
pattern (sp-feedback MEMORY.md, dated 2026-04-29). All findings here
are scoped bugs or one-off architectural calls — none satisfy the
"recurring pattern that shapes future decisions" bar. No
memory_update proposed.

## Calibration entries

5 findings appended to `.claude/sp-feedback-calibration.json`
findings_history with `user_action: "pending"` and
`runtime_validation: "pending"`. F6 is logged as a finding rather
than a `missed_detections` entry because the user did not surface a
runtime complaint — Mode A produced it from the project-memory
breadcrumb.
