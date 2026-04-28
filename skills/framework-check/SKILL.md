---
name: framework-check
description: |
  Health check for the sp-harness project framework. Runs 7 check categories,
  classifies each issue by severity (🔴 blocks runtime / 🟡 needs attention /
  ✅ pass) and fixability (auto / needs-confirm / manual), prints a structured
  report, and asks the user which fix path to take.
author: sp-harness
version: 3.0.0
---

# framework-check

Verify the current project follows the sp-harness framework. Produce a
**structured report** (same format every run) and let the user choose how
to fix issues.

---

## Check Categories (9)

Each category groups related checks. Every issue found is tagged with:

- **Severity**: 🔴 blocks runtime · 🟡 degraded · ✅ pass
- **Fixability**: `auto` (safe, no user input) · `needs-confirm` (destructive
  or side-effects) · `manual` (human judgment required)

### 1. CLAUDE.md

Severity: 🔴 if missing or old format; 🔴 if humanization or
language-consistency rules are absent (v0.8.5+ / v0.8.7+); 🟡 for other
content drift.

Checks:
- [ ] File exists
- [ ] Exactly 3 sections: `First-Principles Standards`, `Context Management`, `Project Map`
- [ ] No old-format sections: `Language`, `Problem`, `Motivation`, `Method`, `Example`, `Architecture`, `Memory, Todo and Checklist`
- [ ] Under 80 lines
- [ ] First-Principles has 4 numbered rules (Clarify, Shortest path, Root causes, Output)
- [ ] Context Management mentions `.claude/todos.json` + Session start protocol listing 6 items + `[module]: description` convention
- [ ] Context Management does NOT mention `.claude/mem/memory.md` (old scope, removed v0.3.0)
      Mentioning `.claude/memory.md` (at root, v0.4.3+ scope) is FINE — that's the current short-term memory file.
- [ ] Project Map has `### Design Docs` and `### Codebase` subsections (no tables)
- [ ] No extra sections
- [ ] **Principle 4 contains the humanization directive** (v0.8.5+, 🔴): the body
      mentions translating jargon. Marker: case-insensitive match for
      `translate jargon` OR `don't paste doc vocabulary`. Old short form
      ("Skip preamble, summaries, and obvious observations.") = FAIL.
- [ ] **Context Management Rules contains the audience-modeling line** (v0.8.5+, 🔴):
      the `**Rules:**` block starts with a bullet about translating project
      terms for the listener. Marker: case-insensitive match for
      `translate project terms into plain language` OR `listener may not share`.
- [ ] **Principle 5 contains the configurable-language rule** (v0.8.10+, 🔴):
      First-Principles section has a `**5.` heading and the body references
      reading `language` from `.claude/sp-harness.json`. Markers (all three
      required, case-insensitive): `sp-harness.json`, `language`, `code-mixing`.
      Old v0.8.7 form (just `match the user's language` + `code-mixing` with
      no `sp-harness.json` reference) = FAIL — force-update.
      Absence of any Principle 5 = FAIL.

Fixability:
- File missing → `needs-confirm` (full rewrite via init-project template)
- Old-format sections present → `needs-confirm` (full rewrite)
- Content drift (minor) → `manual` (user must decide what to keep)
- **Missing Principle 4 humanization directive (v0.8.5+) → 🔴 `auto`
  (FORCE UPDATE, no confirm, no manual fallback)**: locate
  `**4. Output only what changes decisions.**`. Replace its body (every
  line between this heading and the next blank line) with the canonical
  v0.8.5 body:
  ```
  Skip preamble and obvious observations. When summarizing plans, specs, or
  status, translate jargon — don't paste doc vocabulary back. Cite file:line
  at the end if needed, not as the lead.
  ```
  Before writing, print the old body to terminal so user can manually
  re-apply any custom wording afterwards. DO NOT downgrade to manual
  even if the body looks hand-edited — the goal is forced convergence.
- **Missing Context Management audience-modeling rule (v0.8.5+) → 🔴 `auto`
  (FORCE UPDATE, no manual fallback)**: locate the `**Rules:**` line. If
  no bullet in the Rules block matches markers `translate project terms`
  OR `listener may not share`, insert this as the new first bullet:
  `- When reporting plan/status to the user, translate project terms into plain language. The listener may not share doc vocabulary.`
- **Missing Principle 5 OR old v0.8.7 form (v0.8.10+) → 🔴 `auto` (FORCE
  UPDATE, no manual fallback)**: insert the full Principle 5 block
  immediately after the Principle 4 body's blank-line terminator and
  before the `---` separator that ends First-Principles Standards.
  Canonical form (v0.8.10+):
  ```
  **5. Inline chat language is configured in `.claude/sp-harness.json`.**
  Read the `language` field at session start. Default `match-input` replies
  in the user's input language each turn; any other value (e.g. `en`, `zh`)
  pins replies to that language regardless of input. No code-mixing in
  either case. Identifiers (paths, commands, field names, product names)
  stay in original. Files, commits, docs, code, and state always English
  regardless.
  ```
  If a `**5.` heading already exists but is missing any of the three
  markers (`sp-harness.json`, `language`, `code-mixing`), DELETE the old
  block and replace with the canonical form (print the old block to
  terminal first so user can manually re-apply customizations).

These three are 🔴 FORCE-UPDATE — runtime is observably degraded
without them (jargon dump from dense plan docs, English-Chinese
code-mixed sentences). They apply on path (a) and (b) without
per-item gating. On path (c) per-item, the agent still asks but
notes "🔴 force-recommended". On path (d) report-only, list as
unfixed but with explicit warning that user-facing output will keep
producing the broken patterns until applied.

### 2. Docs structure

Severity: 🟡. Fixability: `auto`.

Checks:
- [ ] `docs/design-docs/` exists
- [ ] `docs/plans/active/` exists
- [ ] `docs/plans/completed/` exists
- [ ] `docs/reports/` exists

Fix: mkdir missing directories.

### 3. State sources

Severity: mixed per check. Fixability: mixed.

Checks:
- [ ] `.claude/todos.json` exists with valid schema (🟡, `auto`: create `{"todos":[]}`)
- [ ] Every todo has required fields: id, description, category, status, created_at, linked_feature_ids, archived_feature_paths (🟡, `manual`)
- [ ] All `linked_feature_ids` reference existing features (🟡, `manual`)
- [ ] No duplicate todo ids (🔴, `manual`)
- [ ] `.claude/memory.md` exists (🟡, `auto`: create from template)
- [ ] memory.md has a `## Buffer` section (🟡, `manual`)
- [ ] memory.md under 30 lines (🟡, `manual`: triage bloated entries)
- [ ] `.claude/features.json` entries with `from_todo` reference existing todo ids (🔴, `manual`)

Source overlap (HARD RULE): for each memory.md buffer entry, check
if the referenced file also appears in pending todos, features.json, or
recent git log. Overlap → warn `manual` (user triages which is authoritative).

Legacy files (🟡, `needs-confirm`: delete after printing content):
- [ ] `.claude/mem/memory.md` absent (old scope pre-0.4.3)
- [ ] `.claude/mem/todo.md` absent (replaced by todos.json in 0.4.0)
- [ ] `.claude/mem/checklist.md` absent (old format)

### 4. Agent templates

Severity: 🔴 if drift or missing (runtime will break). Fixability: `needs-confirm`.

Existence:
- [ ] `.claude/agents/sp-feedback.md` exists (required regardless of dev_mode)
- [ ] If `dev_mode` is `three-agent`: sp-planner.md, sp-generator.md, sp-evaluator.md all exist
- [ ] No plugin-level `agents/sp-planner.md` / `sp-generator.md` / `sp-evaluator.md` in plugin source (legacy)

Template drift (v0.7.0+) — deployed copies may be stale:

Old-format markers (presence = BAD):
- [ ] sp-planner.md does NOT contain `task-plan.json` or `eval-plan.json`
- [ ] sp-generator.md does NOT contain `implementation.md` (as output filename)
- [ ] sp-evaluator.md does NOT contain `eval-report.json`
- [ ] sp-feedback.md does NOT contain `final-eval-report.json` or `iter-N-eval-report.json`

New-format markers (absence = BAD):
- [ ] sp-planner.md contains `<feature-id>.plan.yaml`
- [ ] sp-generator.md contains `<feature-id>.plan.yaml`
- [ ] sp-evaluator.md contains `eval.rounds[]` or `<feature-id>.plan.yaml`
- [ ] sp-feedback.md contains `<feature-id>.plan.yaml`

Configurable-language rule (v0.8.10+, 🔴 FORCE UPDATE, no manual fallback):
- [ ] Each existing `.claude/agents/sp-*.md` (except `sp-generator.md`,
      which has no terminal output) contains the configurable-language
      rule. Markers (all three required, case-insensitive): `sp-harness.json`,
      `language`, `code-mixing`. Old v0.8.7 form (just `match the user's
      language` + `code-mixing` with no `sp-harness.json` reference) =
      FAIL for that file — force-update.

Decision touch-point protocol marker (v0.8.11+, 🔴 FORCE UPDATE):
- [ ] Each existing `.claude/agents/sp-*.md` (except `sp-generator.md`,
      which has no terminal output) contains the literal string
      `decision-touchpoint-protocol`. Missing = FAIL for that file —
      force-update by appending the canonical reference (per-file
      wording in the Critical Fix Paths section below). Without this
      marker the deployed agent has no protocol reference at the
      generation site, even if the source template does.

Plugin-doc references must use `${CLAUDE_PLUGIN_ROOT}/` prefix (v0.8.14+, 🔴 FORCE UPDATE):
- [ ] Each existing `.claude/agents/sp-*.md` must NOT contain bare
      `docs/decision-touchpoint-protocol.md` or `docs/plan-file-schema.md`
      references. These resolve to the user project's working directory at
      runtime, not the plugin install dir, so any agent that tries to Read
      the path gets file-not-found. Detect bare references — substring
      match for `docs/decision-touchpoint-protocol.md` or
      `docs/plan-file-schema.md` not immediately preceded by
      `${CLAUDE_PLUGIN_ROOT}/`. Any hit = FAIL for that file.

      Detection one-liner:
      ```bash
      for f in .claude/agents/sp-{planner,evaluator,feedback,generator}.md; do
        [ -f "$f" ] || continue
        python3 -c "
import re, sys
src = open('$f').read()
for m in re.finditer(r'(?<!\\$\\{CLAUDE_PLUGIN_ROOT\\}/)docs/(decision-touchpoint-protocol|plan-file-schema)\\.md', src):
    print(f'{sys.argv[1]}: bare {m.group()}')
" "$f"
      done
      ```

Fix:
- **Old/new format markers FAIL → `needs-confirm` (full template regenerate)**:
  read `${CLAUDE_PLUGIN_ROOT}/agent-templates/{name}.md`, fill
  `{PROJECT_NAME}` and `{PROJECT_CONTEXT}` from CLAUDE.md, overwrite the
  deployed file. User-confirm because hand customization is lost.
- **Only language-consistency rule missing → 🔴 `auto` (FORCE UPDATE)**:
  append the canonical rule (per-file wording in the Critical Fix Paths
  section below) to the existing `## Rules` numbered list. Purely
  additive. DO NOT downgrade to manual or needs-confirm.
- **Only touch-point protocol marker missing → 🔴 `auto` (FORCE UPDATE)**:
  append the canonical reference (per-file wording in the Critical Fix
  Paths section below). Purely additive — no hand customization is
  destroyed.
- **Only bare plugin-doc references found → 🔴 `auto` (FORCE UPDATE)**:
  literal-string replace — for each `docs/decision-touchpoint-protocol.md`
  or `docs/plan-file-schema.md` not already preceded by
  `${CLAUDE_PLUGIN_ROOT}/`, prepend `${CLAUDE_PLUGIN_ROOT}/`. Idempotent
  (already-prefixed occurrences are skipped). Purely mechanical.

### 5. Agent state

Severity: 🟡. Fixability: `auto`.

Checks:
- [ ] `.claude/agents/state/active/` exists (may be empty)
- [ ] `.claude/agents/state/archive/` exists (may be empty)
- [ ] `docs/plans/completed/` has plans for features with `passes:true`
- [ ] `docs/plans/active/` does NOT have plans for completed features
- [ ] For each feature with `supersedes` non-empty and `passes:true`,
      `.claude/agents/state/archive/<feature-id>/supersession.json` exists and is valid JSON

Fix: create missing state directories (`auto`). Supersession mismatch → warn `manual`.

### 6. Hooks & config

Severity: mixed. Fixability: `auto` unless noted.

Checks:
- [ ] `.claude/hooks/update-todo-reminder.sh` exists and executable (🟡, `auto`)
- [ ] `.claude/settings.json` has Stop + UserPromptSubmit hooks (🟡, `auto`)
- [ ] `.claude/sp-harness.json` exists with `dev_mode`, `last_hygiene_at_completed`, `external_codebase`, `language` (🔴 if file missing, `auto`; 🟡 if file present but `language` field missing — `auto`-add as `match-input`, v0.8.10+)
- [ ] If `external_codebase: true`, `.claude/codebase-context.md` exists (🟡, `manual`: re-run init-project)
- [ ] If `external_codebase: false` (or absent), `.claude/codebase-context.md` should NOT exist (🟡, `manual`: decide which side is correct)

### 7. Git conventions

Severity: 🟡. Fixability: `manual`.

Checks:
- [ ] Last 10 commits match `[module]: description` format (warn only; never rewrite history)

### 8. Language consistency

Scope is narrow: only files that inherit their content from the plugin
(which is English-only). User-authored project files — CLAUDE.md, design
docs, memory.md buffer entries, todo descriptions — follow the user's
choice of language and are NOT checked here.

Severity: 🔴 for deployed agent files (prompt pollution breaks model
behavior); 🟡 for this repo's plugin source.

Detection depends on context:

**User-project context** (sp-harness is installed as a plugin):
```bash
grep -rP '[\x{4e00}-\x{9fff}]' .claude/agents/ 2>/dev/null
```

**Plugin-dev context** (this repo is the sp-harness repo itself; has
`skills/` and `agent-templates/` at the root):
```bash
grep -rP '[\x{4e00}-\x{9fff}]' skills/ agent-templates/ docs/ README.md CHANGELOG.md CLAUDE.md 2>/dev/null
```

Checks:

Always check (both contexts):
- [ ] No CJK characters in `.claude/agents/*.md` (deployed agents inherit
      from English plugin templates; CJK here means stale or hand-edited)

Plugin-dev only (apply when `skills/` and `agent-templates/` exist at
repo root — indicates this IS the sp-harness repo):
- [ ] No CJK in `skills/**/*.md`
- [ ] No CJK in `agent-templates/*.md`
- [ ] No CJK in `docs/**/*.md`
- [ ] No CJK in `README.md`, `CHANGELOG.md`, `CLAUDE.md`

**Never check** (user's choice):
- Any user-project `CLAUDE.md`
- `.claude/memory.md` buffer entries
- `.claude/todos.json` descriptions
- `docs/design-docs/` in user projects (user's spec, user's language)

Fixability:

- **`.claude/agents/*.md`**: `needs-confirm` — if CJK present and plugin's
  `${CLAUDE_PLUGIN_ROOT}/agent-templates/` is English (v0.7.4+), regenerate
  from template (same path as agent drift detection).
- **Plugin-dev files**: `manual`. User/Claude translates per commit.

Rationale: the plugin's source tree is English-only by contributor
convention (see repo CLAUDE.md). User projects are not bound by that
convention — they pick their own language. The only cross-boundary
concern is deployed agent files in `.claude/agents/`, which inherit from
the plugin and therefore should stay English.

### 9. Decision touch-point protocol coverage (v0.8.10+, plugin-dev only)

Scope: applies when `skills/` and `agent-templates/` exist at repo root
(this IS the sp-harness repo). Skipped in user-project context — the
protocol is a plugin-source convention, not a user-project rule.

Severity: 🔴 (degraded user-facing output if missing). Fixability:
`manual` (the LLM must understand WHY the protocol applies before
inserting the marker; mechanical insertion would defeat the purpose).

Checks:

For each file in the canonical touch-point inventory below, the literal
string `decision-touchpoint-protocol` must appear at least once
(case-sensitive). Missing = 🔴 FAIL for that file.

Inventory (matches `${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md` § Touch-point inventory):

```
agent-templates/sp-planner.md
agent-templates/sp-evaluator.md
agent-templates/sp-feedback.md
skills/three-agent-development/SKILL.md
skills/single-agent-development/SKILL.md
skills/feature-tracker/SKILL.md
skills/brainstorming/SKILL.md
skills/finishing-a-development-branch/SKILL.md
skills/framework-check/SKILL.md
skills/switch-dev-mode/SKILL.md
skills/init-project/SKILL.md
skills/requesting-code-review/code-reviewer.md
```

One-shot detection:

```bash
for f in agent-templates/sp-planner.md agent-templates/sp-evaluator.md \
         agent-templates/sp-feedback.md \
         skills/{three,single}-agent-development/SKILL.md \
         skills/feature-tracker/SKILL.md skills/brainstorming/SKILL.md \
         skills/finishing-a-development-branch/SKILL.md \
         skills/framework-check/SKILL.md skills/switch-dev-mode/SKILL.md \
         skills/init-project/SKILL.md \
         skills/requesting-code-review/code-reviewer.md; do
  grep -q "decision-touchpoint-protocol" "$f" || echo "MISSING: $f"
done
```

Fix path: `manual`. When this fires, it usually means a new touch-point
was added without a protocol reference, OR an existing touch-point was
rewritten and the marker dropped. The fix is to:

1. Read `${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md`
2. Identify the touch-point in the offending file
3. Add a sentence near the format spec: `This is a decision touch-point
   per ${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md` plus the four-part rule
   (or the structured-menu / closure-summary variant, whichever applies)
4. Verify the format spec actually conforms — adding the marker without
   conforming output defeats the check

#### 9b. Plugin-doc references must use `${CLAUDE_PLUGIN_ROOT}/` prefix (v0.8.14+, plugin-dev only)

Sub-check piggybacks on category 9's plugin-dev scope.

Severity: 🔴 (citations don't resolve in user projects without the
prefix — `${CLAUDE_PLUGIN_ROOT}/docs/X.md` resolves to the install dir,
bare `docs/X.md` resolves to user CWD).

Fixability: `auto` (FORCE UPDATE — purely mechanical literal-string
substitution, idempotent).

Checks:

Scan all files under `skills/`, `agent-templates/`, and `docs/` for
substring `docs/decision-touchpoint-protocol.md` or
`docs/plan-file-schema.md` not immediately preceded by
`${CLAUDE_PLUGIN_ROOT}/`. Any hit = FAIL for that file.

One-shot detection:

```bash
python3 - <<'PY'
import re, os
PROTECTED = ['decision-touchpoint-protocol', 'plan-file-schema']
ROOTS = ['skills', 'agent-templates', 'docs']
# Self-exclude: this skill defines the check, so its body legitimately
# contains the protected names as data (PROTECTED list, pattern strings).
EXCLUDE = {'skills/framework-check/SKILL.md'}
PATTERN = re.compile(
    r'(?<!\$\{CLAUDE_PLUGIN_ROOT\}/)docs/(' + '|'.join(PROTECTED) + r')\.md'
)
fails = []
for root in ROOTS:
    for dp, _, fs in os.walk(root):
        for fn in fs:
            if not fn.endswith('.md'):
                continue
            p = os.path.join(dp, fn)
            if p in EXCLUDE:
                continue
            with open(p) as f:
                src = f.read()
            for m in PATTERN.finditer(src):
                fails.append((p, m.group()))
for p, m in fails:
    print(f"BARE: {p}: {m}")
print(f"\n{len(fails)} bare reference(s) found.")
PY
```

Fix:

Same script with substitution — for each match, prepend
`${CLAUDE_PLUGIN_ROOT}/`. Idempotent because the regex's negative
lookbehind already excludes already-prefixed occurrences.

```bash
python3 - <<'PY'
import re, os
PROTECTED = ['decision-touchpoint-protocol', 'plan-file-schema']
ROOTS = ['skills', 'agent-templates', 'docs']
# Self-exclude: this skill defines the check, so its body legitimately
# contains the protected names as data (PROTECTED list, pattern strings).
EXCLUDE = {'skills/framework-check/SKILL.md'}
PATTERN = re.compile(
    r'(?<!\$\{CLAUDE_PLUGIN_ROOT\}/)docs/(' + '|'.join(PROTECTED) + r')\.md'
)
for root in ROOTS:
    for dp, _, fs in os.walk(root):
        for fn in fs:
            if not fn.endswith('.md'):
                continue
            p = os.path.join(dp, fn)
            if p in EXCLUDE:
                continue
            with open(p) as f:
                src = f.read()
            new = PATTERN.sub(r'${CLAUDE_PLUGIN_ROOT}/docs/\1.md', src)
            if new != src:
                with open(p, 'w') as f:
                    f.write(new)
                print(f"FIXED: {p}")
PY
```

Add new protected paths to `PROTECTED` if more plugin docs get added
that need to be referenced from skills.

Do NOT auto-insert the marker without conforming format — that hides
the real issue from future audits.

### Features validator (runs independently)

Run:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" validate
```

Script checks: valid JSON, unique ids, required fields, dangling depends_on /
supersedes refs, cycles, self-supersession. Exit 1 on errors.

Any failure → 🔴, `manual` (do NOT auto-create features.json; that is
brainstorming's job).

### Skill output lint (runs independently)

Run:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint-skill-output.py" --check
```

Scans every `skills/*/SKILL.md` for content inside ` ```output-template `
fences and verifies:

- R1: static codenames (D1, F2, S3, Phase N, Round N, Mode A/B) have inline `(<gloss>)`
- R2: id placeholders use `<…-id|format>` syntax (renderer hooked to `_lib.format_id`)
- R3 (warn-only, does not change exit): quality heuristics on gloss content
- schema invariant: every `.claude/features.json` and `.claude/todos.json` entry has non-empty `display_name`

Output is a JSON summary with `errors`, `warnings`, `files_scanned`.

Exit 1 on R1/R2/schema failure → 🔴, `manual` (do NOT auto-edit
SKILL.md content; the maintainer must fix the offending fence per
the rules in `writing-skills` "Output template rules" chapter).
R3 warnings are reported but do not fail the check.

### Skill procedural lint (runs independently)

Run:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/lint-skill-procedural.py" --check
```

Scans every `skills/*/SKILL.md` for paired ` ```procedural-instruction `
and ` ```worked-example ` fences and verifies:

- P1: every procedural-instruction fence is immediately followed (only
  blank lines between) by a worked-example fence; orphan worked-examples
  also fail
- P2: every worked-example body has at least 100 whitespace-separated words
- P3: every worked-example body contains a numbered list with >= 3 items
  (position-agnostic; blank lines between items allowed)

Output is a JSON summary with `errors` and `files_scanned`.

Exit 1 on P1/P2/P3 failure → 🔴, `manual` (do NOT auto-edit
SKILL.md content; the maintainer must fix the offending fence per
the rules in `writing-skills` "Procedural Section Rules" chapter).

---

## Step 1: Run all checks

Execute every check above. Record each finding with:
- category (1–8)
- description (short)
- severity (🔴 / 🟡 / ✅)
- fixability (auto / needs-confirm / manual)
- fix action (one-line description of what would happen)

---

## Step 2: Print structured report (fixed format)

Always use this exact format. Same every run.

Before printing, re-read each issue line aloud as if to a colleague
unfamiliar with the project. If a phrase reads like jargon, rewrite it
in plain language.

```output-template
🔍 Framework Check (v<plugin version>)

[1/9] CLAUDE.md
    <status line: ✅ pass | ⚠️ N warn | ❌ M fail>
    <for each issue:>
    - <description>  (<severity><fixability>: <short fix>)

[2/9] Docs structure
    ...

[3/9] State sources
    ...

[4/9] Agent templates
    ...

[5/9] Agent state
    ...

[6/9] Hooks & config
    ...

[7/9] Git conventions
    ...

[8/9] Language consistency
    ...

[9/9] Decision touch-point protocol  (plugin development only; skipped in user projects)
    ...

---
Summary: 9 categories · <P> pass · <W> warn · <F> fail
Severity: 🔴 <C> critical · 🟡 <D> degraded
Fixability: <A> auto · <N> needs confirm · <M> manual
```

Example:
```output-template
🔍 Framework Check (v<CURRENT>)

[1/9] CLAUDE.md
    ✅ pass

[2/9] Docs structure
    ⚠️ 1 warn (1 auto fix)
    - docs/reports/ missing (🟡auto: mkdir)

[3/9] State sources
    ✅ pass

<!-- lint:disable=R3 -->
[4/9] Agent templates
<!-- lint:disable=R3 -->
    ❌ 3 fail (🔴 blocks runtime)
<!-- lint:disable=R3 -->
    - sp-planner.md contains task-plan.json (🔴needs confirm: regenerate from template)
<!-- lint:disable=R3 -->
    - sp-generator.md contains implementation.md (🔴needs confirm: regenerate)
<!-- lint:disable=R3 -->
    - sp-evaluator.md missing plan.yaml marker (🔴needs confirm: regenerate)

[5/9] Agent state
    ✅ pass

[6/9] Hooks & config
    ⚠️ 1 warn
    - settings.json missing Stop hook (🟡auto: add hook config)

[7/9] Git conventions
    ⚠️ 2/10 commits off-format (🟡manual: review recent commits)

[8/9] Language consistency
    ✅ pass

[9/9] Decision touch-point protocol
    ✅ pass

---
Summary: 9 categories · 5 pass · 2 warn · 2 fail
Severity: 🔴 3 critical · 🟡 3 degraded
Fixability: 2 auto · 3 needs confirm · 3 manual
```

---

## Step 3: Ask user which fix path

This is a decision touch-point per `${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md`
(structured menu — each option must be a plain-language consequence).
After the report, print:

```output-template
→ Your call:
  (a) Auto-fix all — apply every 🟡auto immediately; for each
      🔴needs-confirm I'll ask "fix this? (yes/no/diff)"; manual items
      are listed at the end as still-todo.
  (b) Auto-fix only — apply 🟡auto; skip needs-confirm and manual,
      print them as unfixed at the end.
  (c) Per-item decision — walk every issue and ask one by one;
      slowest, but you see each fix before it runs.
  (d) Report only — print this report, change nothing.
```

Wait for user response.

---

## Step 4: Execute chosen path

### (a) Auto-fix all
1. Apply all `auto` fixes in order.
2. For each `needs-confirm`, ask: `Fix <desc>? (yes / no / diff)` where
   `diff` shows what would change before re-asking yes/no.
3. List `manual` items at end as "still todo for you".

### (b) Auto-fix only
1. Apply all `auto` fixes.
2. Print skipped items (needs-confirm + manual) with a note that
   they remain unfixed.

### (c) Per-item decision
For each issue in order (by category, then severity), ask:
`Fix <category><severity> <desc>? (yes / no / skip-category)`
- `yes`: apply the fix (if auto) or do the needs-confirm flow
- `no`: leave it
- `skip-category`: jump past remaining issues in this category

### (d) Report only, no changes
Exit without changes.

---

## Step 5: Re-check and commit

After any path that applied fixes:

1. Re-run all checks. Produce a second report with same format.
2. If the second report has fewer issues than the first, commit:
   ```
   [framework]: auto-fix N issues (category breakdown)
   ```
   Commit message lists which categories had fixes.
3. If any 🔴 issues remain, warn the user explicitly — feature development
   may fail at runtime until they're resolved.

---

## Critical fix paths (reference)

### CLAUDE.md missing → invoke `init-project` skill

### CLAUDE.md old format (Language/Problem/Architecture/tables)
**Rewrite from scratch** using init-project template. Do NOT patch. Only
the project name transfers. Design decisions go to docs/design-docs/;
decided ideas go to manage-todos; decided fixes go to manage-features;
recurring patterns go to agent memory via sp-feedback.

### CLAUDE.md missing v0.8.5 humanization rules (🔴 FORCE UPDATE, auto, no manual fallback)

Two surgical patches. Apply directly without user confirm.

**Patch 1: Principle 4 body.** Find the block:

```
**4. Output only what changes decisions.**
Skip preamble, summaries, and obvious observations.
```

Replace the two lines with:

```
**4. Output only what changes decisions.**
Skip preamble and obvious observations. When summarizing plans, specs, or
status, translate jargon — don't paste doc vocabulary back. Cite file:line
at the end if needed, not as the lead.
```

If Principle 4's body has been hand-edited beyond the old short form,
**still force-replace** with the canonical body. Before writing, print
the old body to terminal so the user can manually re-apply any
customization afterwards. DO NOT downgrade to manual.

**Patch 2: Context Management Rules first bullet.** Find the line
`**Rules:**` and check the immediately following bullet. If it is not
the audience-modeling line, insert this as the new first bullet:

```
- When reporting plan/status to the user, translate project terms into plain language. The listener may not share doc vocabulary.
```

If the existing first bullet already covers audience-modeling in
different wording (matches `listener` OR `translate.*plain language`),
treat as ✅ — don't insert a duplicate.

After both patches, re-check the 80-line cap. If now over, warn user:
typical fix is to trim the FILL tree examples in Project Map.

### CLAUDE.md missing Principle 5 (v0.8.7+, 🔴 FORCE UPDATE, auto, no manual fallback)

Insert the canonical Principle 5 block immediately after Principle 4 and
before the `---` separator that ends First-Principles Standards:

```
**5. Match the user's language for inline chat only.**
Reply fully in the user's language with no code-mixing. Identifiers (paths,
commands, field names, product names) stay in original. Files, commits,
docs, code, and state always English regardless.
```

If a Principle 5 already exists with different wording AND covers all of:
matches `match the user's language`, mentions `code-mixing` (or `code mixing`),
mentions a file/commit/docs carve-out → treat as ✅, don't overwrite.

If Principle 5 exists but is missing one of the markers, **delete the
existing block and replace** with the canonical form. Print the old
block to terminal first so the user can manually re-apply customization.
DO NOT downgrade to manual.

After patch, re-check 80-line cap.

### Agent files missing configurable-language rule (v0.8.10+, 🔴 FORCE UPDATE, auto)

For each existing `.claude/agents/sp-*.md` that lacks the rule (markers
all three required: `sp-harness.json`, `language`, `code-mixing`):

- Locate the file's `## Rules` section.
- If an old v0.8.7 rule is present (matches `match the user's language`
  + `code-mixing` but NOT `sp-harness.json`), DELETE the old rule and
  replace with the canonical form below.
- Otherwise append a new numbered rule continuing the existing numbering.
- Wording by file:

  - sp-planner.md / sp-evaluator.md / sp-feedback.md:
    `N. Inline chat output: at session start, read .claude/sp-harness.json field language. If match-input (default), reply in the user's input language each turn; if a specific code (en, zh, ...), pin replies to that language regardless of input. Either way: no code-mixing; identifiers (paths/commands/field names/product names) stay in original. Files / commits / docs / plan YAML always English regardless.`

  - sp-generator.md (no terminal output):
    `N. Files / commits / plan YAML always English regardless of any chat language. (Generator has no terminal output, so the inline-chat half of the language rule does not apply here.)`

If a file lacks a `## Rules` section entirely (drift), prefer full
template regeneration via `needs-confirm` (since drift this severe
suggests other issues). This is the ONE case where it's not pure-auto —
because regenerating the full file destroys hand customization, which
needs user awareness. The other cases (Rules section exists but rule
missing or stale) are pure-auto force-update.

### Agent files missing decision touch-point protocol marker (v0.8.11+, 🔴 FORCE UPDATE, auto)

For each existing `.claude/agents/sp-*.md` (except `sp-generator.md`)
that lacks the literal string `decision-touchpoint-protocol`:

- Locate the file's `## Rules` section.
- Append a new numbered rule continuing the existing numbering. Same
  wording for all three deployed agents:

  `N. Every decision touch-point follows ${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md. For open decisions: Background / What it controls / My pick / Options must each be present in plain language; bare spec IDs (D1, F1, Option B, step 3) without an in-sentence translation are forbidden; option lines must be one full sentence of consequence, never just labels.`

If a file lacks a `## Rules` section entirely → fall back to full
template regeneration via `needs-confirm` (same reasoning as the
language rule). Otherwise this is purely additive — no hand
customization is destroyed, so pure-auto.

### Agent template drift
Read `${CLAUDE_PLUGIN_ROOT}/agent-templates/{name}.md`, fill
`{PROJECT_NAME}` and `{PROJECT_CONTEXT}` from CLAUDE.md, overwrite
deployed file. Warn about lost customization. Alternative: user invokes
`sp-harness:switch-dev-mode` directly.

### Legacy `.claude/mem/*.md` files
Print content, suggest migration targets, then delete after user consent.

### Features.json invalid
Report errors. Do NOT auto-create — brainstorming's job.

### sp-harness.json missing or incomplete
Create with defaults: `{"dev_mode": "single-agent", "last_hygiene_at_completed": 0, "external_codebase": false, "language": "match-input"}`.
Missing fields only, don't overwrite existing values.

### Git conventions
Warn only. Never rewrite history.

---

## Rules

1. **Structured report is mandatory** — same format every run, no prose
   improvisation.
2. **User chooses the fix path** — no default "just fix it all".
3. Old-format CLAUDE.md = full rewrite, not patch.
4. Do not auto-create features.json.
5. Idempotent — a second run after all fixes should show all ✅.
