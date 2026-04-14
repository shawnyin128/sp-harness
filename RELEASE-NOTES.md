# SP Harness Release Notes

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
