# SP Harness Changelog

> Note on version sequence: sp-harness was forked from upstream
> superpowers v5.0.7 (Apr 8, 2026) and tagged 1.0.0 to mark the rename
> + content reset. Real ongoing development was then re-versioned from
> v0.5.0 onward (post-fork-reset). The 1.0.0 entry at the bottom of
> this file documents the fork creation. Everything above it is
> post-reset history, newest-first.
>
> **Documented release gap:** v0.5.1 — v0.8.15 are not described here;
> 39 version bumps in that range carried internal iteration that was
> never written into release notes. They survive in `git log
> --oneline` (commit messages of the form `[infra]: bump version to
> X`). v0.8.16 picks up the changelog narrative at the next
> meaningful inflection point.

## v0.8.23 (2026-04-29)

Single-patch release: lock the Plan summary format and ban macOS
smart-quote leakage from touch-point output.

### What's new

- **Single-agent Plan summary fence now lives inline in the skill.**
  Previously `skills/single-agent-development/SKILL.md` Phase 3 said
  "see sp-planner template for exact format" — a cross-file reference
  the main session never opens. Result: every Plan summary was
  reconstructed from LLM memory of the format, drifting into invented
  section headers (`Approach (3 steps)`, `Decisions (...)`), bare
  `S1`/`D1` labels without plain-language glosses, and Chinese-English
  code-mixing inside Chinese-pinned sessions. The canonical
  `output-template` fence is now physically inlined into the
  single-agent SKILL, byte-identical to the source in
  `agent-templates/sp-planner.md`. A new regression test in
  `tests/canonical-plan-summary-parity/` fails the moment one copy
  drifts from the other.
- **Self-check before emitting Plan summary (parity with Evaluator).**
  Phase 3 in single-agent mode previously had no pre-emit check, while
  Phase 4 (Evaluator) had a mandatory "re-read each option line aloud"
  pass plus the Output prose self-check. Phase 3 now has its own six-
  item gate: literal section headers, both `Goal:` and `Approach:`
  lines per step, no bare `S\d+`/`D\d+`/`F\d+` outside a parenthesized
  gloss, no code-mixing, no fancy/curly quotes, and the runtime self-
  check from `using-sp-harness`. Failing any check forces a rewrite
  before emitting.
- **R6 rule in `lint-skill-output.py` bans fancy/curly quotes.**
  U+2018 / U+2019 / U+201C / U+201D inside `output-template` fences
  now fail static lint. macOS smart-quote autocorrect is the typical
  leak source on Chinese-language sessions; the rule catches them at
  source-tree time before they ship in user-facing fences. Inline
  escape hatch via `<!-- lint:disable=R6 -->` for the rare case where
  a touch-point intentionally quotes typographic examples. Four-test
  regression suite in `tests/output-prose-lint-r6/` covers ASCII pass,
  curly-double fail, curly-single fail, and disable-comment pass.
- **Runtime self-check and decision-touchpoint protocol both ban
  fancy quotes.** `skills/using-sp-harness/SKILL.md` Output prose
  self-check now scans free-form chat drafts for the four code points
  alongside the existing short-code patterns;
  `docs/decision-touchpoint-protocol.md` Forbidden patterns lists the
  same restriction. Three layers of defense (runtime self-check,
  protocol-level forbidden pattern, static lint) make the regression
  much harder to reintroduce.

### Notes

- This release is the response to a recurring complaint about Planner
  output format drift in `language: zh` single-agent sessions. Three
  prior point-fixes had each added another prose rule somewhere in the
  skill tree without addressing the structural cause: the canonical
  format lived in `agent-templates/`, the runtime self-check lived in
  `using-sp-harness`, and the chat language pin lived in
  `single-agent-development` itself — three rules, zero of them visible
  to the Planner role at emit time. Inlining the fence and adding a
  pre-emit self-check brings all the rules to one place.
- The fancy-quote ban is a new rule, not a strengthening of an existing
  one. Pre-emit self-check at the runtime layer + R6 at static-lint
  layer is the same belt-and-suspenders pattern as R5 (project-internal
  short codes).

## v0.8.22 (2026-04-28)

Single-patch release: brainstorming skill now has explicit guidance for
the merged-todo case.

### What's new

- **Brainstorming `link-features` step now checks for merged duplicates.**
  When a brainstorm consolidates multiple seed todos into one spec, the
  skill previously linked the new feature set only to the Step 0 seed
  todo, leaving any other in-scope `pending` / `in_brainstorm` todos
  untouched. Worst-case: the user manually relinked the same feature set
  to a second todo, and `check-done` then marked both done at the same
  moment with no record of the merge. New mandatory check before
  `link-features`: scan `.claude/todos.json` for other todos covering
  the same problem, surface them to the user, and `manage-todos drop
  <other-id> --reason="merged into <seed-id>"` for each confirmed merge.

### Notes

- Discovered while reconciling todo state: two `in_feature` todos
  (`standardize-dev-skill-terminal-output-schema-...` and
  `inline-explain-framework-ids-...`) had been linked to the same five
  `skill-output-*` features after their concerns merged into one Track A
  spec. Both `check-done`-promoted to `done` simultaneously; the spec
  text fix prevents this shape from recurring.

## v0.8.21 (2026-04-27)

Follow-up patch closing two gaps that sp-feedback Mode A surfaced
after the v0.8.20 batch shipped.

### What's new

- **Agent templates now in lint scope.** `agent-templates/sp-planner.md`
  and `agent-templates/sp-evaluator.md` print user-facing briefs but
  were outside the default `lint-skill-output.py` scan scope (which
  globbed only `skills/*/SKILL.md`). Both templates' brief fences
  migrated from plain ` ``` ` to ` ```output-template `; bare labels
  in `sp-planner.md` (Problem / Key decisions / Options) wrapped as
  `**Label**`; both templates' `<feature-id>` placeholders use the
  `<feature-id|format>` runtime-renderer form. `default_skill_files()`
  now returns `skills/*/SKILL.md` UNION `agent-templates/*.md`
  (30 files vs the previous 26).

- **CHANGELOG.md gloss audit.** Five naked project-internal short
  codes in older v0.8.18 / v0.8.17 / v0.8.16 entries (cluster-label
  references like `F3+F4+F5`, `F1+F2`, `F3-F5`) gained inline glosses
  describing the cluster's meaning. Backtick-quoted pattern
  descriptions (e.g. `` `F\d+(\+F\d+)+` ``) are unchanged — those
  are documentation, not references. New regression test in
  `tests/output-prose-changelog-shortcode-gloss/` strips backtick
  spans and fenced blocks before scanning so pattern docs do not
  false-positive.

### Notes

- Single-commit packaging note: the agent-templates implementation
  ended up in a single `[tests]`-labeled commit because the original
  `[scripts]` commit message hit a heredoc parse error on literal
  triple-backticks. Per `CLAUDE.md` no-amend rule, left as-is.
- One follow-up pending: an R3 false-positive — `feature-id` inside
  the `<feature-id|format>` placeholder syntax is detected as a
  snake_case token when the placeholder sits inside a parenthesized
  gloss. R3 is warn-only so this doesn't break builds; tracked
  informally.

---

## v0.8.20 (2026-04-27)

Output prose discipline release. Six-feature design
([output-prose-discipline](docs/design-docs/2026-04-27-output-prose-discipline-design.md))
extending the v0.8.17 / v0.8.18 (Output Template Rules — codename
gloss inside fences) and v0.8.19 (Procedural Section Rules — paired
worked-example for free-form generation) infrastructure to two more
disciplines: section header style and project-internal short-code
glossing (across both fenced output and free-form chat).

### What problem this solves

Two distinct symptoms in user-facing terminal output:

1. **Section headers were visually flat.** Brief blocks used bare
   `Problem:` / `Steps:` / `Files:` form. Users had to eye-scan to
   find section boundaries.

2. **Project-internal short codes leaked verbatim into chat.** Agents
   read design docs, todo notes, CHANGELOG entries that use short
   codes (`Track A`, `Tier 1`, multi-segment cluster labels, version-
   as-label) and echoed them back without translating. Users without
   the maintainer's context did not know what they meant. The
   pre-existing user-memory rule was generic and failed in practice.

### Pre-design experiment

Before committing to the runtime self-check approach (the only fix
path for short codes in free-form chat), 3 calls of `claude --print`
with a specific-pattern self-check rule went 3-for-3: every short-
code introduction got an inline parenthesized gloss. Generic
"re-read aloud" rules had previously failed; specific-pattern rules
work. The conclusion shaped both the new central rule (pinned in
`using-sp-harness/SKILL.md`) and the audit-and-upgrade decision for
8 existing generic self-check sites.

### What's new

- **Two new lint rules in `lint-skill-output.py`:**
    - **R4** — section header style. Lines matching `Title-case
      Words:` at end of line inside `output-template` fences must
      use `**Label**` form. Inline disable available.
    - **R5** — short-code gloss. Inside `output-template` fences,
      matches of `Track [A-Z]`, `Tier \d+`, multi-segment
      `F\d+(\+F\d+)+`, and `v\d+\.\d+\.\d+` must be immediately
      followed (within 8 chars on the same line) by a parenthesized
      gloss. Same semantics as R1's codename gloss check.
  Both rules failure-level. Live tree had 7 R4 violations on launch
  (all repaired by the migration step) and 0 R5 violations on launch
  (locked by regression test).

- **Section header migration to `**Label**` style.** Seven bare
  `Label:` patterns in `brainstorming/SKILL.md` (Decision Brief
  multi-line block: Problem / Approach / Key decisions made /
  Divergence risks / Scope / Options) and `finishing-a-development-
  branch/SKILL.md` (discard confirmation prompt) wrapped as
  `**Label**`. Compact one-line briefs (Feature Brief from
  `print-brief.py`) use `**Label:**` with colon kept as same-line
  delimiter; `feature-tracker/SKILL.md` reference template updated
  to match. Five `print-brief.py` snapshot fixtures regenerated.

- **Runtime self-check rule in `using-sp-harness/SKILL.md`.** New
  section pairs a `procedural-instruction` fence (the rule) with a
  `worked-example` fence (a ~150-word compliant project-status
  reply demonstrating each pattern correctly glossed plus a 5-item
  observation list). Loaded automatically at every sp-harness
  session start, so free-form chat output gets the same discipline
  R5 enforces inside fences.

- **Eight existing generic self-check sites AUGMENTED with cross-
  reference.** `audit-feedback`, `feature-tracker` (×2 sites),
  `switch-dev-mode`, `finishing-a-development-branch`,
  `three-agent-development`, `single-agent-development`,
  `brainstorming`, `framework-check` — each retained the original
  `re-read aloud as if to a colleague` generic rule (catches
  arbitrary jargon) and added a one-line cross-reference to the
  central specific-pattern rule (catches the named short codes).
  Both layers run at every print site; neither is redundant.

- **`writing-skills` chapter "Output Prose Discipline".** Sibling
  to "Output Template Rules" and "Procedural Section Rules". Three
  subsections (section header style, short-code glossing, why
  generic self-checks fail) plus cross-links to the other two
  discipline chapters.

### Notes

- The R5 regex requires multi-segment cluster labels
  (`F\d+(\+F\d+)+`, e.g. `F3+F4+F5`); single-segment `F\d+` is left
  to R1's codename rule territory. Documented in the design doc
  after sp-feedback Mode A surfaced an apparent spec/implementation
  drift that turned out to be intentional.
- sp-feedback Mode A also surfaced two real gaps (agent-templates
  outside the lint scope, CHANGELOG.md still has naked short codes
  from older entries). Both tracked as fix-features for the next
  batch (`output-prose-agent-templates-lint-scope`,
  `output-prose-changelog-shortcode-gloss`).
- A new `ux-improvement` todo records the broader "source-side
  short-code gloss discipline" question for future brainstorming.

---

## v0.8.19 (2026-04-27)

Procedural skill instruction fixtures release. Five-feature design
([procedural-skill-fixtures](docs/design-docs/2026-04-27-procedural-skill-fixtures-design.md))
shipping a parallel mechanism to the v0.8.17/18 output-template work,
applied to a different content class: free-form generation sections
inside SKILL.md files.

### What problem this solves

Some SKILL.md sections tell the agent to *render a template* — a
fixed shape with placeholders. Output Template Rules (v0.8.17/18)
governs those. But other sections tell the agent to *freely generate*
200-300 words of original output from a directive (e.g.
brainstorming's `Presenting the design`, which says "Cover
architecture, components, data flow, error handling, testing"). Until
this release, those directive sections used only abstract bullets
with no concrete worked example. Agents read them and self-interpret
"depth" idiosyncratically — output quality drifted session-to-session.

### What's new

- **New fence pair: `procedural-instruction` + `worked-example`.**
  Authors wrap the abstract directive bullets in
  ` ```procedural-instruction `, immediately followed (only blank
  lines between) by ` ```worked-example ` carrying a ~200-word sample
  output that demonstrates the target depth, plus a numbered list of
  three or more "things to notice in this example" that translate
  concrete choices in the sample back to abstract principles.

- **Static lint: `scripts/lint-skill-procedural.py`.** Three rules:
    - **P1 (pairing)** every procedural-instruction is immediately
      followed by a worked-example; orphans on either side fail.
    - **P2 (minimum body)** worked-example body has >= 100
      whitespace-separated words.
    - **P3 (observation list)** worked-example body contains a
      numbered list with >= 3 items (position-agnostic; blank lines
      between items allowed).
  Wired into `framework-check` as a 🔴 manual check. Round 1 of the
  evaluator pipeline caught a P3 false-positive on blank-line-separated
  list items; rule was tightened to total-count rather than
  max-consecutive-run before merge.

- **`writing-skills` chapter "Procedural Section Rules".** Sibling
  to "Output Template Rules". Defines what counts as a procedural
  section, the P1/P2/P3 rules with one-line definitions, the explicit
  no-anti-examples rule (with rationale citing past mimicry incidents
  in this codebase), and a self-anchoring worked-example pair
  demonstrating the form. Cross-linked with Output Template Rules
  so authors finding either chapter find the other.

- **Phase 1 pilot: brainstorming `Presenting the design`.**
  Original 5 directive bullets preserved verbatim inside a
  procedural-instruction fence; worked-example fence below carries a
  URL-shortener-with-admin-dashboard sample (concrete tables, key
  fields, sliding-window keying, RFC 7807 error format, named test
  categories). 5 numbered observation points pin the form: name
  concrete files/tables not abstract roles · HOW + KEYED BY WHAT for
  components · trade-offs in choices not in whether-to-have-it ·
  specific status codes / formats · named test categories.

- **Phase 1 verification (before/after comparison).** Ran a
  primed-prompt comparison on a deliberately fresh scenario (markdown
  note-taking CLI with cross-device sync — distinct from URL shortener
  used inside the fixture). Pre-pilot baseline 743 words; post-pilot
  pilot 516 words. Pilot adopted all 5 fixture observation patterns
  applied to the new domain — strongest evidence the methodology
  shapes form, not text. Verdict: concreteness IMPROVED, form transfer
  IMPROVED, depth NEUTRAL → Phase 2 gate cleared.

- **Phase 2 audit + rollout.** Audit of the originally-projected
  "5 SKILL.md files, multiple sections each" found that only **one**
  additional section across the 5 candidate files meets the strict
  free-form-generation definition: brainstorming's
  `Exploring approaches`. Other candidates are checklist-style
  instructions, principle-giving meta-guidance, or templated output
  already covered by Output Template Rules. Phase 2 wrapped exactly
  that one section (API-keys storage decision space sample, 5
  observation points). Spot-check on a fresh API-cache scenario
  produced fixture-shaped output including a stronger conditional-swap
  close that goes beyond the fixture pattern. Tests lock the four
  audit-negative files at zero procedural-instruction fences so a
  future author cannot quietly add one without revisiting the audit.

### Notes

- The Phase 2 audit is the most informative outcome of this release:
  the original design's "5 files, multiple sections" projection was
  optimistic. Tight rule for "what counts as procedural" + locking
  test for the audit-negative files are more valuable than expanding
  scope.
- Mid-implementation, the writing-skills chapter caught its own
  meta-violation: the first draft used `❌ BAD` literally to name the
  banned anti-example pattern, which the chapter's own no-anti-example
  test rejected. Reworded to "negative samples / negative variant" —
  the chapter follows the rule it teaches.
- Brief / verdict files in `tests/skill-procedural/` are gitignored
  (maintainer-local, not distributed with the plugin).

---

## v0.8.18 (2026-04-27)

Skill-output codename gloss migration release. F3+F4+F5 (the three skill-output migration features) of the
[skill-output-codename-gloss design](docs/design-docs/2026-04-27-skill-output-codename-gloss-design.md):
every SKILL.md with prescribed user-facing terminal output now wraps
that output in the lint-enforced ` ```output-template ` fence
introduced by v0.8.17. The migration is now end-to-end: lint guards
the entire user-facing surface against future codename leakage.

### What's new

- **Dev pipeline cluster migrated** (F3): `single-agent-development`,
  `three-agent-development`, and `feature-tracker` SKILL.md files now
  wrap their decision touchpoints, round verdicts, and feature-brief
  reference in `output-template` fences. Naked `Round 6` / `Round N+1`
  codenames dropped in favor of plain action language ("try one more
  iteration", "another evaluation runs"). Self-check instructions
  added before every emission step. `subagent-driven-development`
  unchanged: it has no prescribed terminal output of its own.
- **Brainstorm/plan cluster migrated** (F4): `brainstorming` Decision
  Brief restructured from trailing-codename form
  `<gloss> (D1) → choice` to the canonical leading form
  `D1(<gloss>) → choice`. Concrete-example anchor applied to D1
  placeholder. Protocol reference and meta-instruction moved out of
  the fenced template into surrounding prose. `writing-plans`,
  `executing-plans`, and `dispatching-parallel-agents` unchanged:
  process documentation, no rendered output blocks of their own.
- **Remaining cluster migrated** (F5): seven more skills wrapped —
  `audit-feedback` (calibration summary), `code-hygiene` (hygiene-
  complete report + return-of-control sentinel), `feedback`
  (memory-operations summary), `finishing-a-development-branch`
  (tests-failing template, structured menu, discard confirmation),
  `framework-check` (structured-report format, example report,
  → Your call menu), `init-project` (Q1 dev-mode menu, three-agent
  defaults print, Q2 use-defaults menu), `switch-dev-mode` (stale-
  agents detected report, regenerate menu). The remaining ~10 process-
  doc / bash-catalog skills lint-pass trivially with no fences.
- **Vocabulary fixes inside glosses.** Domain phrases rephrased to
  drop unnecessary kebab-case where it didn't change meaning
  (`auto-fixable` → `auto`, `need-confirm` → `needs confirm`,
  `plugin-dev` → `plugin development`, `re-confirmed` → `confirm
  again`, `(true red-team)` → `(true adversarial review)`,
  `<plain-language summary>` → `<short summary>`). Where the kebab
  is genuinely the displayed label (file names like `task-plan.json`
  / `plan.yaml` / `eval-report.json` in switch-dev-mode's stale-marker
  block; `🔴needs-confirm` tags in framework-check's example report;
  `sp-feedback` self-references in audit-feedback), inline
  `<!-- lint:disable=R3 -->` comments accompany the legitimate use.

### Migration acceptance

26 SKILL.md files scanned by `lint-skill-output.py`: 0 errors,
0 warnings. Every file with a `output-template` fence passes R1
(codename-needs-gloss) and R2 (id-placeholder-needs-format) under
strict rules; every file without a fence lint-passes trivially per
the design's no-allowlist principle.

### Notes

- The original feature plans for F3-F5 (the three migration features) each listed a "Remove grace
  allowlist" step that turned out to be vestigial: there has never
  been an allowlist mechanism in `lint-skill-output.py`. The fence-
  as-gate already handles the same concern more simply (un-fenced
  files trivially pass; wrapping IS the migration).
- Same-session dogfood is impossible because the harness reads SKILL
  content from a cached path that doesn't refresh mid-session. Each
  feature's edits become observable in the *next* session that loads
  them. Real runtime validation accumulates as users naturally
  exercise the skills.

---

## v0.8.17 (2026-04-27)

Skill-output codename gloss infrastructure release. F1+F2 (the lint infrastructure and renderer foundation) of the
[skill-output-codename-gloss design](docs/design-docs/2026-04-27-skill-output-codename-gloss-design.md):
the static-lint and centralized-renderer foundation that F3-F5 (the three migration features) will
build on to migrate every skill's user-facing output to a uniform
`代号(白话)` format.

### What's new

- **Centralized id renderer.** New `skills/_lib/format_id.py` exposes
  `get_display_name(id, kind)` and `format_id(id, kind)` →
  `<id>(<display_name>)`. Both raise `ValueError` on unknown id,
  empty `display_name`, or invalid kind — no fallback to bare id.
  `skills/feature-tracker/scripts/print-brief.py` now imports the
  helper instead of its local `lookup_display_name()`. Behavior of
  the existing brief format is preserved at this step (F3 owns the
  format flip to `<id>(<display_name>)`).
- **Schema invariant: `display_name` is required and non-empty.**
  `manage-features` and `manage-todos` `mutate.py add/update` now
  reject empty or whitespace-only `display_name` (explicit empty
  is distinguished from omitted-with-derive-fallback). The
  corresponding `backfill_display_names.py` scripts also fail loudly
  when the heuristic would write empty, naming the offending entry
  id and leaving the file untouched.
- **Skill output lint.** New `scripts/lint-skill-output.py` scans
  `skills/*/SKILL.md` for content inside ` ```output-template `
  fenced blocks and enforces:
    - **R1**: static codenames (`D1`, `F2`, `S3`, `Phase N`,
      `Round N`, `Mode A/B`) need an immediately-adjacent `(<gloss>)`.
    - **R2**: id placeholders use `<…-id|format>` syntax that
      signals the runtime renderer.
    - **R3** (warn-only, exit unchanged): heuristics for
      snake_case/kebab-case in glosses, consecutive Title Case
      pairs, sp-harness denylist tokens (`Phase`, `Round`,
      `Mode A/B`, `F1`-`F9`, `plan.yaml`, `feature-id`) used
      outside their codename role, and `>80`-char gloss clauses.
      Inline disable via `<!-- lint:disable=R3 -->`.
    - **schema check**: every `.claude/features.json` and
      `.claude/todos.json` entry has non-empty `display_name`
      (regression guard for the new invariant).
- **`writing-skills` "Output template rules" chapter.** New section
  in `skills/writing-skills/SKILL.md` covering when to use the
  fence, gloss format with concrete `GOOD`/`BAD` examples, id
  placeholder syntax, the concrete-anchor rule, the self-check
  step, the R3 quality rubric, and how to wire the lint script
  into project-local pre-commit / CI per project convention. The
  chapter explicitly opts NOT to ship pre-commit/CI config —
  `framework-check` is the in-plugin enforcement.
- **`framework-check` runs the lint.** New "Skill output lint"
  validator section calls `scripts/lint-skill-output.py --check`;
  failure is red and manual.

### Background and context

The 2026-04-23 "Humanize sp-harness user-facing output" work landed
the `display_name` field in `features.json` / `todos.json` and
populated it via a `derive_display_name` heuristic, but consumption
was patchy — only 5 of 27 SKILL.md files actually used it, and the
field was schema-optional with empty-fallback to bare id. v0.8.17
closes that gap: required + non-empty schema, no-fallback
centralized renderer, lint that prevents future regression.

F3-F5 (the three migration features for dev-pipeline / brainstorm-plan / remaining-cluster
migration) will incrementally add ` ```output-template ` fences to
skill files and flip the user-visible output format. That work is
unchanged in v0.8.17 — no fences exist yet, so the lint passes
trivially over all 26 SKILL.md.

### Tests

76 tests in `tests/skill-output-format-id-helper/`: 13 `format_id`
unit tests, 14 mutate.py tests across both managers, 5 backfill
tests, 4 print-brief integration tests, 16 lint-script tests across
7 fixtures plus CLI flag and schema-integration coverage. 24
humanize-schema-and-backfill regression tests still pass.

## v0.8.16 (2026-04-27)

Cleanup-and-tighten release. Six features merged in one session that
plug long-standing gaps in the orchestrator chain and shrink the
plugin's distribution footprint.

### What's new

- **Hygiene → tracker dual-signal contract.** `code-hygiene` now
  prints a verbatim "CONTROL RETURNS TO feature-tracker Step 5d.d"
  sentinel and writes `next_action: "continue_step_5d_d"` to its
  result file, plus three reinforcement points in feature-tracker
  Step 5. Fixes the silent chain break where the orchestrator treated
  hygiene's commit as the end of the feature loop and skipped the
  Feature Brief / loop-back.
- **Scripted Feature Brief.** `skills/feature-tracker/scripts/print-
  brief.py` replaces the prose template; the script reads the
  archived plan YAML and emits a fixed 9-line brief. Bundled
  stdlib-only YAML loader handles the plan-file-schema subset
  (block mappings, "- |" sequence-item block scalars, wrapped
  multi-line scalars, identifier-key mapping items). The brief is
  English-only by design; new exception note in feature-tracker
  SKILL + plan-file-schema.md documents why.
- **Orchestrator language enforcement.** Three orchestrator SKILLs
  (feature-tracker, single-agent-development, three-agent-
  development) gain a "Session language" hard-gate at session
  entry, mirroring the existing rule on sp-* subagent templates. New
  sp-feedback Mode A dimension 8 ("Language compliance") flags
  drift.

### Cleanup

- **Upstream-fork residue removed.** `.github/`, 5 unreferenced
  upstream test corpora (`tests/{brainstorm-server, claude-code,
  explicit-skill-requests, skill-triggering, subagent-driven-dev}`),
  `docs/testing.md`, and stray `.DS_Store` files — ~280KB stops
  shipping to user installs. CLAUDE.md references to the removed
  PR template were rewritten in place.
- **CHANGELOG consolidated.** This file replaces the prior 29-line
  fork-creation stub plus the parallel `RELEASE-NOTES.md`; v0.5.0+
  history is now in one canonical place. (v0.5.1 — v0.8.15 remains
  undocumented; that gap predates this consolidation.)
- **Maintainer-only tooling untracked.** `scripts/bump-version.sh`,
  `.version-bump.json`, `.githooks/pre-push`, `tests/humanize-*`
  (4 dirs) — all stay on the maintainer's working tree but no
  longer ship to user installs via marketplace `source: "./"`.
  Recovery story: trust git history.
- **Single canonical version source.** `package.json` deleted;
  `.githooks/pre-push` and `.version-bump.json` migrated to read
  `.claude-plugin/plugin.json` exclusively.

### Test infrastructure

- New `tests/_helpers/version_check.py` (shared `assert_min_version`
  with `>= baseline` semantics) plus `tests/conftest.py` adding
  `tests/` to sys.path. Markdown-grep regression tests across the
  six features lock the new directives + script behavior + cleanup
  state in place. 34 tests / 6 feature suites.

## v0.5.0 (2026-04-14)

**NEW MECHANISM**: Supersession tracking. When a feature replaces
existing code, sp-harness now forces explicit declaration of what to
clean up (source + runtime artifacts) and verifies it through multiple
pipeline checkpoints. Prevents the "new code reads old knowledge base"
class of bug.

### Motivation

Real harness failure: a developer built feature-v2 to replace feature-v1,
but v1's knowledge base (generated data file) was never cleaned up.
Inference pipeline under v2 kept reading the stale knowledge, producing
wrong results. This was not caught by code-hygiene (knowledge file is
not dead code — it's live data from dead code). Not caught by sp-evaluator
(checks v2's correctness, not v1's absence). Not caught by sp-feedback
(no mechanism to track supersession relationships).

Root cause in sp-harness design: supersession as a concept was never modeled.
Every actor assumed someone else handled cleanup.

### What's new

- **Schema change**: features.json entries gain `supersedes: [feature-id]`
  array (optional, default empty). Validated by manage-features:
  referenced ids must exist; no self-supersession.
- **brainstorming Step 1b adds Supersession Question**: "Will this new
  feature REPLACE any existing feature/module?" If yes, fills the
  **mandatory** `## Supersession Plan` spec section listing source files
  AND runtime artifacts with HANDLE action (DELETE | MIGRATE | KEEP).
- **writing-plans Supersession Cleanup Tasks**: If spec has Supersession
  Plan, writing-plans generates cleanup tasks FIRST (before implementation
  tasks): remove source, handle artifacts, verify no stale references,
  runtime sanity check.
- **sp-evaluator Supersession Evaluation**: auto criteria — source paths
  absent, artifacts DELETE'd or MIGRATE'd correctly, grep verification
  patterns empty, runtime checks pass. Single failure = ITERATE minimum.
- **PASS archival**: on PASS, three/single-agent-development serializes
  Supersession Plan to `archive/<feature-id>/supersession.json` for
  future audit.
- **sp-feedback Mode A 7th dimension** (Supersession artifact staleness):
  reads all archived supersession.json records, re-verifies artifacts
  are still gone (catches drift — someone re-introduced the old path).
- **framework-check**: validates supersedes refs + supersession.json
  archive integrity.

### Intentional boundaries

- Artifact paths are **mandatory** in Supersession Plan (HARD-GATE).
  If agent can't enumerate them, stop and investigate — that's why the
  bug happens.
- Only triggered on **explicit supersession declaration**. Regular
  features that modify existing code don't trigger this heavy machinery
  (would be noise).

## v0.4.4 (2026-04-14)

sp-feedback self-health calibration. Tracks precision/recall via
`.claude/sp-feedback-calibration.json`. New internal skill `audit-feedback`
computes stats. Addresses single-point-of-failure for feedback loop.

## v0.4.3 (2026-04-14)

Short-term memory reintroduced with tightened scope. Pre-triage
observations now have a home without duplicating other state sources.

### Rationale

Between state-source updates, there's a gap: observations made during
work (bugs noticed, hypotheses, user concerns) that are not yet decided.
If session ends before they're processed, they're lost — agent has to
rediscover. `memory.md` with a tight, boundary-enforced scope fills
this gap without reintroducing the v0.2.x overlap problems.

### What's new

- **`.claude/memory.md`** (top-level, markdown) — short-term observations
- Template includes explicit scope comment + triage protocol
- HARD RULE: never duplicate with todos.json / features.json / agent-memory
- Agent must triage existing entries (git correlation + grep other sources)
  before adding new ones

### Boundary definition

- **memory.md** = "still undecided" (bugs unverified, hypotheses, concerns,
  in-flight investigation progress)
- **todos.json** = "decided to track, needs design"
- **features.json** = "decided to build (specific)"
- **agent-memory** = "reusable patterns"
- **docs/** = "design rationale"
- **git log** = "historical events"

Triage from memory routes to the appropriate permanent home, then the
memory entry is removed.

### Changes

- init-project creates `.claude/memory.md` with scope template
- CLAUDE.md session-start protocol reads memory.md (step 5)
- Hook renamed: `update-todo-reminder.sh` → `update-context-reminder.sh`;
  text expanded to cover ideas (todos), decided bugs (features), and
  undecided observations (memory)
- framework-check validates memory.md exists, scope sections present,
  and scans for overlap with other sources (warns on duplicates)

### Intentionally NOT done

- No Python helper script for memory (keep it simple — agent uses Edit/Write)
- No JSON schema for memory (markdown preserved for low friction)
- No PostToolUse / SessionStart triage hooks (existing UserPromptSubmit
  reminder + agent self-triage rules in template comment are enough)
- No auto-deletion (triage requires agent judgment + user oversight via
  framework-check overlap warnings)

## v0.4.2 (2026-04-14)

Scripted manage-features. Selection algorithm (topological + priority)
now lives in `scripts/query.py next` — deterministic, tested.
Same pattern as v0.4.1 (manage-todos).

## v0.4.1 (2026-04-14)

Scripted manage-todos. Bundled Python scripts handle todos.json CRUD;
agents never read the full file. Token savings + divergence control.

## v0.4.0 (2026-04-14)

**BREAKING**: `.claude/mem/todo.md` replaced by structured `.claude/todos.json`.
todo becomes the idea pipeline entry point.

### Rationale

todo.md was an unstructured markdown checklist. It served as main-session
scratchpad. But ideas that surface during development deserve proper
handling — they may become features, or get dropped, or merge with other
ideas. Markdown checkboxes can't capture this lifecycle.

todo.json upgrades todo into a first-class state source alongside
features.json, with a state machine: pending → in_brainstorm → in_feature → done.
Every feature can trace back to a todo origin (or null). sp-feedback routes
feature_gap findings to new_todo (not direct-to-features) so ideas get proper
brainstorming instead of skipping design.

### Changes

- **New skill** `sp-harness:manage-todos` (internal, user-invocable: false):
  CRUD + state transitions for `.claude/todos.json`
- **New data source** `.claude/todos.json` with schema:
  `{id, description, category, status, notes, created_at, linked_feature_ids, archived_feature_paths}`
- **brainstorming Step 0**: checks todos.json, offers pending todos as seeds
- **features.json schema**: adds `from_todo` field (nullable reference to todo id)
- **feature-tracker Step 5**: when a feature passes, checks if its originating
  todo is now complete (all linked features done) → auto-transitions todo to `done`
- **sp-feedback routing change**: `feature_gap` → `new_todo` (not `new_feature`).
  Bugs still go direct to fix_feature.
- **Removed** `.claude/mem/todo.md` (replaced by `.claude/todos.json`)
- **Directory** `.claude/mem/` no longer created by init-project (empty after
  memory.md and todo.md removals)

### Migration for existing projects

- Run `/framework-check` — it detects legacy todo.md and memory.md, suggests
  migration paths
- Manually review todo.md content:
  - Items that are ideas → add via manage-todos
  - Items that are stale session notes → discard
- Delete `.claude/mem/todo.md` after migration
- If `.claude/mem/` ends up empty, remove it

## v0.3.0 (2026-04-14)

**BREAKING**: Removed `memory.md` and `update-mem` skill. State sources restructured.

### Rationale

memory.md had three sections (Current State / Key Decisions / Findings) that
duplicated information already available from authoritative sources:
- Current State → derivable from `features.json` + `git log` + `git status`
- Key Decisions → project-level in `docs/design-docs/`; session-level in commit messages
- Findings → recurring patterns in `agent-memory/*`; open problems in `todo.md`

Keeping memory.md violated the "one authoritative source per concern" principle
and caused drift between memory.md and the actual state.

### Changes

- **Removed** `.claude/mem/memory.md` (init-project no longer creates it)
- **Removed** `skills/update-mem/`
- **New structured context sources per role**: each subagent reads only what it
  needs (sp-planner: CLAUDE.md + feature entry + spec + own memory; sp-evaluator:
  eval-plan + implementation + code + own memory; etc.)
- **Removed** `{PROJECT_CONTEXT}` slot from agent templates — agents dynamically
  read CLAUDE.md on every invocation instead of having frozen project info
- **State file archival**: `.claude/agents/state/` now split into `active/`
  (current feature) and `archive/<feature-id>/` (completed features). sp-feedback
  reads archive for cross-feature analysis.
- **Hook renamed**: `update-mem-reminder.sh` → `update-todo-reminder.sh`
- **Session-start protocol**: CLAUDE.md → features.json → sp-harness.json → todo.md
  → git log → git status

### Migration for existing projects

- Run `/framework-check` — it will detect legacy memory.md and suggest migration
- Manually review memory.md content and distribute: decisions → docs/, open
  problems → todo.md, patterns accumulate to agent-memory naturally
- Delete memory.md after migration

## Earlier releases (0.0.12 – 0.2.4)

Forked from [obra/superpowers](https://github.com/obra/superpowers) v5.0.7.

Highlights across these iterations:
- **init-project** + CLAUDE.md + docs/ hierarchy
- **feature-tracker** with topological + priority-based feature selection
- **three-agent-development** and **single-agent-development** modes
- **sp-feedback** closed-loop system review (Mode A auto + Mode B user-triggered)
- **Structured Append/Compact Checklists** for agent memory with Gate 1 (structural) + Gate 2 (value)
- **Hybrid architecture gate** in brainstorming, **Codebase Understanding** step
- **feature dependencies** (`depends_on` with topological ordering)
- **Skill visibility split**: 8 user-facing core skills, 16 internal

## [1.0.0] - 2026-04-08 (fork creation)

The fork-from-upstream-superpowers marker. Versioning then reset to
v0.5.0+ above; the entries below describe the rename / cleanup commit
that created sp-harness.

### Added
- init-project: lean CLAUDE.md bootstrap with strict template
- update-mem: structured memory state snapshots
- feature-tracker: incremental feature development loop
- three-agent-development: Planner/Generator/Evaluator with JSON communication
- git-convention: `[module]: description` commit format
- code-hygiene: periodic cleanup every 3 features
- system-feedback: 4-dimension optimization review
- framework-check: health check + auto-migration

### Changed
- brainstorming: PROPOSAL.md input, features.json output, divergence risk analysis, Project Map updates
- writing-plans: docs/plans/active/ output, fallback chain design
- test-driven-development: test strategy selection, coverage awareness
- using-sp-harness: output efficiency rules

### Removed
- Upstream legacy docs (docs/superpowers/, docs/plans/2025-*)
- Deprecated commands (commands/)
- CODE_OF_CONDUCT.md

### Meta
- Renamed: superpowers → sp-harness (73+ files)
- Version: 1.0.0 (was 5.0.7)
- License: MIT, original copyright preserved
