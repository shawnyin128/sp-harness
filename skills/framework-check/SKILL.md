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

## Check Categories (8)

Each category groups related checks. Every issue found is tagged with:

- **Severity**: 🔴 blocks runtime · 🟡 degraded · ✅ pass
- **Fixability**: `auto` (safe, no user input) · `needs-confirm` (destructive
  or side-effects) · `manual` (human judgment required)

### 1. CLAUDE.md

Severity: 🔴 if missing or old format; 🟡 if content drift.

Checks:
- [ ] File exists
- [ ] Exactly 3 sections: `First-Principles Standards`, `Context Management`, `Project Map`
- [ ] No old-format sections: `Language`, `Problem`, `Motivation`, `Method`, `Example`, `Architecture`, `Memory, Todo and Checklist`
- [ ] Under 80 lines
- [ ] First-Principles has 4 numbered rules (Clarify, Shortest path, Root causes, Output)
- [ ] Context Management mentions `.claude/todos.json` + Session start protocol listing 6 items + `[module]: description` convention
- [ ] Context Management does NOT mention `memory.md` (deprecated v0.3.0)
- [ ] Project Map has `### Design Docs` and `### Codebase` subsections (no tables)
- [ ] No extra sections

Fixability:
- File missing → `needs-confirm` (full rewrite via init-project template)
- Old-format sections present → `needs-confirm` (full rewrite)
- Content drift (minor) → `manual` (user must decide what to keep)

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
- [ ] memory.md has `## Observations` + `## In-flight` sections (🟡, `manual`)
- [ ] memory.md under 30 lines (🟡, `manual`: triage bloated entries)
- [ ] `.claude/features.json` entries with `from_todo` reference existing todo ids (🔴, `manual`)

Source overlap (HARD RULE): for each memory.md observation entry, check
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

Fix: regenerate from `${CLAUDE_PLUGIN_ROOT}/agent-templates/{name}.md`
(fills {PROJECT_NAME}, {PROJECT_CONTEXT} from CLAUDE.md, overwrites).
`needs-confirm` because any hand customization is lost.

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
- [ ] `.claude/sp-harness.json` exists with `dev_mode`, `last_hygiene_at_completed`, `external_codebase` (🔴 if missing, `auto`)
- [ ] If `external_codebase: true`, `.claude/codebase-context.md` exists (🟡, `manual`: re-run init-project)
- [ ] If `external_codebase: false` (or absent), `.claude/codebase-context.md` should NOT exist (🟡, `manual`: decide which side is correct)

### 7. Git conventions

Severity: 🟡. Fixability: `manual`.

Checks:
- [ ] Last 10 commits match `[module]: description` format (warn only; never rewrite history)

### 8. Language consistency

Severity: 🟡. Fixability: `manual`.

sp-harness content is English-only. Agent prompts, skill docs, and schema
must be in English regardless of the user's interaction language. User
conversations in other languages are fine — but anything written into
`skills/`, `agent-templates/`, `docs/`, or top-level docs like `README.md`
and `CHANGELOG.md` must be English.

Detection (run from repo root):

```bash
grep -rP '[\x{4e00}-\x{9fff}]' skills/ agent-templates/ docs/ README.md CHANGELOG.md 2>/dev/null
```

Any hit → violation. Report each file + line number.

Checks:
- [ ] No CJK characters in `skills/**/*.md`
- [ ] No CJK characters in `agent-templates/*.md`
- [ ] No CJK characters in `docs/**/*.md`
- [ ] No CJK characters in `README.md`, `CHANGELOG.md`

Fix path: `manual`. Auto-translation is lossy and would risk changing
intent. The user (or Claude in a separate pass) must translate each
occurrence to English, preserving the semantics and formatting.

Rationale: the plugin is distributed to users whose interaction language
is unknown. Agent prompts in mixed language degrade model behavior and
break grep-based tooling that assumes English tokens.

### Features validator (runs independently)

Run:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" validate
```

Script checks: valid JSON, unique ids, required fields, dangling depends_on /
supersedes refs, cycles, self-supersession. Exit 1 on errors.

Any failure → 🔴, `manual` (do NOT auto-create features.json; that is
brainstorming's job).

---

## Step 1: Run all checks

Execute every check above. Record each finding with:
- category (1–7)
- description (short)
- severity (🔴 / 🟡 / ✅)
- fixability (auto / needs-confirm / manual)
- fix action (one-line description of what would happen)

---

## Step 2: Print structured report (fixed format)

Always use this exact format. Same every run.

```
🔍 Framework Check (v<plugin version>)

[1/8] CLAUDE.md
    <status line: ✅ pass | ⚠️ N warn | ❌ M fail>
    <for each issue:>
    - <description>  (<severity><fixability>: <one-line fix>)

[2/8] Docs structure
    ...

[3/8] State sources
    ...

[4/8] Agent templates
    ...

[5/8] Agent state
    ...

[6/8] Hooks & config
    ...

[7/8] Git conventions
    ...

[8/8] Language consistency
    ...

---
Summary: 8 categories · <P> pass · <W> warn · <F> fail
Severity: 🔴 <C> critical · 🟡 <D> degraded
Fixability: <A> auto-fixable · <N> need-confirm · <M> manual
```

Example:
```
🔍 Framework Check (v<CURRENT>)

[1/8] CLAUDE.md
    ✅ pass

[2/8] Docs structure
    ⚠️ 1 warn (auto-fixable)
    - docs/reports/ missing (🟡auto: mkdir)

[3/8] State sources
    ✅ pass

[4/8] Agent templates
    ❌ 3 fail (🔴 blocks runtime)
    - sp-planner.md contains task-plan.json (🔴needs-confirm: regenerate from template)
    - sp-generator.md contains implementation.md (🔴needs-confirm: regenerate)
    - sp-evaluator.md missing plan.yaml marker (🔴needs-confirm: regenerate)

[5/8] Agent state
    ✅ pass

[6/8] Hooks & config
    ⚠️ 1 warn
    - settings.json missing Stop hook (🟡auto: add hook config)

[7/8] Git conventions
    ⚠️ 2/10 commits off-format (🟡manual: review recent commits)

[8/8] Language consistency
    ✅ pass

---
Summary: 8 categories · 4 pass · 2 warn · 2 fail
Severity: 🔴 3 critical · 🟡 3 degraded
Fixability: 2 auto-fixable · 3 need-confirm · 3 manual
```

---

## Step 3: Ask user which fix path

After the report, print exactly:

```
→ Your call:
  (a) Auto-fix all (🟡auto applied directly, 🔴needs-confirm asked one by one, manual listed as skipped)
  (b) Auto-fix only (skip needs-confirm and manual, list them)
  (c) Per-item decision (ask for each issue)
  (d) Report only, no changes
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
Create with defaults: `{"dev_mode": "three-agent", "last_hygiene_at_completed": 0, "external_codebase": false}`.
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
