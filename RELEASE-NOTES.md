# SP Harness Release Notes

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
