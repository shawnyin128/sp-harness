# SP Harness

A harness engineering skills library forked from [obra/superpowers](https://github.com/obra/superpowers). Enhanced with three-agent development, feature tracking, structured state sources, and systematic quality control.

## What's Different from Upstream

| Feature | Why |
|---------|-----|
| **init-project** | Bootstraps lean CLAUDE.md (~50 lines) with First-Principles Standards, Context Management, and a docs/ directory tree as project map. Replaces the old fps + init-mem skills. |
| **Structured state sources** | Each concern has one authoritative source: `CLAUDE.md` (map + principles), `todos.json` (idea backlog), `features.json` (decided requirements), `git log` (what happened), `agent-memory/*` (agent patterns), `agents/state/archive/` (per-feature history). No overlapping stores. |
| **Idea pipeline** | `todos.json` holds high-level ideas → brainstorming picks seeds → produces features with `from_todo` link → feature-tracker completes features → todo auto-transitions to `done`. Full traceability from idea to shipped code. sp-feedback routes discovered feature gaps to new_todo (not direct to features) so ideas get proper design. |
| **Feature tracker** | Incremental development: picks highest-priority feature from .claude/features.json, drives implementation, triggers hygiene and feedback automatically. |
| **Three-agent development** | Planner (Opus) → Generator (Sonnet) → Evaluator (Opus) with JSON-based file communication. Planner produces paired task-plan.json + eval-plan.json with per-task evaluation methods. Evaluator outputs structured eval-report.json for iteration. |
| **Divergence risk analysis** | Brainstorming identifies non-deterministic components, builds risk matrix and divergence trees. Writing-plans designs fallback chains (detection → recovery → safe stop). |
| **Test strategy selection** | TDD skill enhanced with 3-question thinking path to choose test type (unit/integration/e2e/browser) per feature. Coverage maps feature steps to tests. |
| **Git convention** | `[module]: description` commit format so git log serves as context source for new sessions. |
| **Code hygiene** | Lightweight GC-style cleanup every 3 features: removes dead code, fixes naming drift, extracts constants. Auto-fixes small issues, escalates large ones. |
| **Feedback agent** | Closes the loop. Mode A runs 6-dimension checklist after all features pass. Mode B is user-triggered (`/feedback`) for observed problems. Findings route into agent memory updates, new/fix features, or manual review — user confirms each batch. |
| **Framework check** | Health check + auto-migration. Detects old format CLAUDE.md and rewrites from template. Validates state sources, hooks, docs structure. |
| **Output efficiency** | Drops filler, pleasantries, hedging from all responses. Code and technical terms unchanged. |

## Install

```bash
# Add this fork as marketplace
/plugin marketplace add shawnyin128/sp-harness

# Install
/plugin install sp-harness@sp-harness-dev

# Update (after pushing new changes)
/plugin install sp-harness@sp-harness-dev
```

## Workflow

```
/init-project              Bootstrap CLAUDE.md + docs/ + state files + hooks
       ↓
/brainstorming             Design → spec + features.json
       ↓
/feature-tracker           Picks feature → loops through development
       ↓
  ┌─ three-agent OR single-agent development ──────┐
  │  Planner  → task-plan.json + eval-plan.json    │
  │  Generator → subagent-driven-dev → impl report │
  │  Evaluator → eval-report.json                  │
  │  ITERATE? → Planner re-plans → loop            │
  │  PASS?    → mark feature complete              │
  └────────────────────────────────────────────────┘
       ↓
  code-hygiene (every 3 features)
       ↓
  next feature → repeat
       ↓
  all features done → @agent sp-feedback (Mode A: self-check)
                        │
                        ├─ routes findings to agent memory updates,
                        │   new/fix features, or manual review
                        └─ closes the loop
```

Other skills available anytime:
- `/framework-check` — verify and fix project framework
- `/git-convention` — enforce commit format
- `/switch-dev-mode` — toggle between single-agent and three-agent development
- `/feedback` — user-triggered diagnosis when you observe a problem (Mode B)

## License

MIT — see LICENSE file. Original work by Jesse Vincent.
