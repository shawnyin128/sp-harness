# SP Harness

A harness engineering skills library for Claude Code. Forked from
[obra/superpowers](https://github.com/obra/superpowers) with added
structure around state sources, three-agent development, idea
pipelines, and self-feedback loops.

**Design principle:** each concern has one authoritative source. The
plugin enforces this through structured state files, explicit skill
scopes, and a closed feedback loop.

## Install

```bash
# Add this fork as marketplace
/plugin marketplace add shawnyin128/sp-harness

# Install
/plugin install sp-harness@sp-harness-dev

# Update after new releases
/plugin install sp-harness@sp-harness-dev
```

## User-facing skills (what you actually invoke)

sp-harness exposes 8 skills in the `/` menu. Everything else is internal —
used by other skills, not by you.

| Skill | When to use |
|-------|------------|
| `/init-project` | Once, at project start. Bootstraps CLAUDE.md, docs tree, state files, dev-mode config, agent definitions. |
| `/brainstorming` | Before writing any code. Explores intent, design, produces spec + features. |
| `/feature-tracker` | To drive incremental development. Picks the next feature, runs the full pipeline, loops. |
| `/three-agent-development` | Develop one feature using Planner → Generator → Evaluator. Usually invoked by feature-tracker. |
| `/single-agent-development` | Develop one feature with the main session playing all three roles. Usually invoked by feature-tracker. |
| `/switch-dev-mode` | Toggle between three-agent and single-agent modes. Updates config + regenerates agent files as needed. |
| `/feedback` | Report an observed runtime issue. sp-feedback diagnoses, routes findings back into the pipeline (Mode B). |
| `/framework-check` | Validate project framework health. Detects layout issues, legacy files, source overlap, supersession integrity. |

Internal skills (not shown in `/` menu) handle: writing plans, executing
plans, subagent-driven development, TDD, git conventions, code hygiene,
code review dispatch, debugging, verification discipline, parallel
dispatching, worktrees, and state-file CRUD (manage-todos, manage-features,
audit-feedback).

## Quick start (5 minutes)

```bash
# 1. Install the plugin (see above)

# 2. Go to your project directory
cd my-project

# 3. Claude Code
claude

# 4. Inside Claude Code, bootstrap
/init-project

# Answer the questions:
#   - Dev mode: three-agent or single-agent?
#   - Agent config: defaults or custom?

# 5. Design your first system
/brainstorming

# Follow the conversation. This produces:
#   - docs/design-docs/YYYY-MM-DD-<topic>-design.md (spec)
#   - .claude/features.json (feature list with dependencies)

# 6. Start development
/feature-tracker

# It picks the next feature, runs the full dev pipeline, loops until done.
# For each feature it invokes three-agent-development OR
# single-agent-development depending on your dev mode.
# HARD-GATE at: (a) feature selection, (b) plan approval per iteration,
# (c) feedback action batches (at the end).
```

## Choosing the dev mode

sp-harness runs features through a Planner → Generator → Evaluator pipeline.
Two ways to run this pipeline:

| Mode | How it runs | Token cost | Evaluation rigor | Best for |
|------|------------|-----------:|-----------------:|----------|
| **three-agent** | 3 separate subagents (Opus + Sonnet + Opus), each with its own context | Higher | Stronger (independent evaluator) | Complex projects, production code, long-lived codebases |
| **single-agent** | Main session plays all 3 roles sequentially | Lower | Weaker (self-persuasion risk, mitigated by explicit protocol) | Simple projects, quick iterations, token-constrained work |

### When you choose

**At project init:**
```
/init-project
```
Step 6 asks: "Which development mode? (a) three-agent, (b) single-agent"

This writes `dev_mode` to `.claude/sp-harness.json`. `feature-tracker`
reads this field on every invocation and dispatches the right skill.

**To switch later:**
```
/switch-dev-mode
```
What it does:
- Reads current `dev_mode` from `.claude/sp-harness.json`
- Prints current mode
- Asks: "Switch to <other mode>? (yes/no)"
- On yes, updates `dev_mode`
- **If switching to three-agent**: checks if `.claude/agents/sp-planner.md`,
  `sp-generator.md`, `sp-evaluator.md` exist. If missing, generates them
  from plugin templates with project-adapted context. Asks if you want to
  customize frontmatter (model, tools, memory, isolation) per agent.
- **If switching to single-agent**: leaves any existing agent files in
  place (they're simply unused). No reconfiguration needed.

`sp-feedback.md` is present in both modes — it's the feedback agent, not
a dev-role agent.

**Rule of thumb:** start with three-agent if you're unsure. Switching to
single-agent later is free (no file cleanup needed). Switching from
single-agent to three-agent requires generating the 3 dev-agent files
(automatic via switch-dev-mode).

## Tutorial A — Three-agent mode (default)

Best for: complex projects, production-quality code, hardening against
self-persuasion bias.

### Setup

```bash
/init-project

# When asked dev mode, choose: three-agent
# When asked agent config, choose: defaults (unless you want custom models/tools)
```

init-project generates:

- `CLAUDE.md` — project map + principles
- `docs/` — design-docs, plans, reports directories
- `.claude/sp-harness.json` — dev_mode=three-agent
- `.claude/features.json` — empty feature list (filled later by brainstorming)
- `.claude/todos.json` — empty idea backlog
- `.claude/memory.md` — empty short-term observations
- `.claude/agents/sp-planner.md` — Opus, writing-plans preloaded
- `.claude/agents/sp-generator.md` — Sonnet, worktree isolation
- `.claude/agents/sp-evaluator.md` — Opus, read-only + Bash
- `.claude/agents/sp-feedback.md` — Opus, project memory
- `.claude/settings.json` — hooks configured

### First feature

```bash
/brainstorming
```

You'll walk through:
1. Codebase Understanding (if existing code) — Claude scans, presents,
   you confirm. Supersession plan required if feature replaces existing code.
2. Architecture type — pure-code / pure-agent / hybrid
3. Clarifying questions — iterated one at a time
4. Design proposal — 2-3 approaches, you pick
5. Spec written to `docs/design-docs/`
6. Divergence risk analysis appended to spec
7. Features extracted to `.claude/features.json` via manage-features

```bash
/feature-tracker
```

Loop begins. For each feature:
1. Feature picked via topological + priority algorithm (from manage-features)
2. Confirm with user (HARD-GATE)
3. Invokes `three-agent-development` which dispatches:
   - `@agent sp-planner` → writes `<feature-id>.plan.yaml` (problem, steps, decisions)
   - Orchestrator prints condensed plan + asks for low-confidence decisions (HARD-GATE)
   - `@agent sp-generator` → appends execution sections to plan YAML (no terminal output)
   - `@agent sp-evaluator` → appends `eval.rounds[]`, designs/runs unit tests, prints closure + tests + blockers
4. Per-round user choice: fix (→ Generator Round N+1) / force-merge / replan
5. On PASS: Evaluator runs optimization pass → user picks merge or optimize
6. On merge: `mark-passing` via manage-features, archive plan YAML, commit
7. On replan: archive current iter, restart from Planner with iteration N+1

Every 3 passed features: `code-hygiene` auto-triggered. All features done:
`sp-feedback` Mode A auto-triggered, runs 7-dimension checklist, routes
findings (`memory_update` / `memory_compact` / `new_todo` / `fix_feature` / `manual`).

### When to use three-agent

- Complex projects where adversarial evaluation catches real bugs
- Long-running codebases needing pattern accumulation in agent memory
- Multiple contributors or teams that need stable, reproducible review
- You want independent context between plan/implement/evaluate phases

### Token cost

Higher than single-agent — 3 subagents per feature, each with its own
context window. sp-planner and sp-evaluator use Opus; sp-generator uses
Sonnet.

## Tutorial B — Single-agent mode

Best for: quick iterations, simple features, prototyping, token-constrained
contexts.

### Setup

```bash
/init-project

# When asked dev mode, choose: single-agent
# (No agent config questions — main session plays all roles)
```

init-project generates:
- Same infrastructure as three-agent mode
- `.claude/agents/sp-feedback.md` — still a subagent
- **NO** sp-planner / sp-generator / sp-evaluator files (main session plays those roles)

### First feature

```bash
/brainstorming
# (same as three-agent mode)

/feature-tracker
```

Loop begins. For each feature:
1. Feature picked via algorithm, confirmed (HARD-GATE)
2. Invokes `single-agent-development`:
   - **Planner role** (main session) — Phase 1 gap discovery, Phase 2 writing-plans, Phase 3 eval-plan
   - Orchestrator prints plan table (HARD-GATE)
   - **Generator role** (main session) — runs TDD per task
   - **Evaluator role** (main session) — with **enhanced anti-self-persuasion protocol** (mandatory cool-down, zero-issue second pass, explicit self-persuasion traps reminder)
3. Same PASS/ITERATE/REJECT flow
4. Same archival, hygiene, feedback at end

### Switching modes later

```bash
/switch-dev-mode
```

This skill:
- Shows current mode
- Asks if you want to switch
- If switching to three-agent: generates missing agent files from templates
- If switching to single-agent: leaves existing agent files in place (unused)

### When to use single-agent

- Simple or early-stage projects
- You want faster iteration (no subagent dispatch overhead)
- Token budget matters
- You trust your own adversarial discipline
- Prototyping, exploratory work

### Self-persuasion warning

Single-agent's weakness: the Evaluator role is played by the same session
that just implemented the code. Our single-agent-development skill embeds
anti-self-persuasion protocols, but this is structurally weaker than
three-agent's independent evaluator. If you're catching the same class
of bug repeatedly in production, consider switching to three-agent.

## What happens during the loop

Beyond the two dev modes, the outer loop is the same:

```
brainstorming → features.json (with from_todo links if started from todos)
     ↓
feature-tracker (loops)
     ├─ pick feature (topological + priority)
     ├─ dispatch dev skill (three-agent or single-agent)
     ├─ on PASS: mark-passing, archive, commit, check if todo complete
     ├─ every 3 features: code-hygiene
     └─ all done: @agent sp-feedback Mode A
                    │
                    ├─ memory_update / memory_compact → auto-execute via Append/Compact Checklists
                    ├─ new_todo → append to todos.json (seeds future brainstorming)
                    ├─ fix_feature → append to features.json (next loop picks up)
                    └─ manual → report only
```

At any point during or after development, if you observe a runtime issue:

```bash
/feedback
```

Describes the observation. sp-feedback runs **Mode B** — asks clarifying
questions, correlates with past findings (precision tracking via
`.claude/sp-feedback-calibration.json`), routes actions, logs missed
detections.

## State sources (where everything lives)

```
.claude/
├── CLAUDE.md                          map + principles (top-level map)
├── sp-harness.json                    dev_mode + hygiene counter
├── features.json                      decided requirements
├── todos.json                         idea backlog
├── memory.md                          pre-triage observations (short-term)
├── sp-feedback-calibration.json       sp-feedback's self-health log
├── agents/
│   ├── sp-feedback.md                 feedback agent (always)
│   ├── sp-planner.md                  three-agent only
│   ├── sp-generator.md                three-agent only
│   ├── sp-evaluator.md                three-agent only
│   └── state/
│       ├── active/                    current feature's work
│       └── archive/<feature-id>/      completed features + supersession records
├── agent-memory/                      per-agent accumulated patterns
│   ├── sp-planner/MEMORY.md
│   ├── sp-evaluator/MEMORY.md
│   └── sp-feedback/MEMORY.md
├── hooks/
└── settings.json

docs/
├── design-docs/                       specs from brainstorming
├── plans/{active,completed}/          writing-plans output
└── reports/                           sp-feedback Mode A reports
```

Each concern has exactly one authoritative source. No duplicate content
across files. `framework-check` detects drift and overlap.

## Troubleshooting

**Dev mode feels wrong.** Run `/switch-dev-mode`.

**Project framework looks broken.** Run `/framework-check`. Reports
violations, auto-fixes most issues, suggests migration paths for legacy
files (pre-0.4.x memory.md, todo.md, etc.).

**sp-feedback predictions seem unreliable.** The calibration log tracks
precision/recall of past findings. An internal `audit-feedback` skill
can be invoked by the main session to print the stats. If precision is
low, manually tune sp-feedback's checklist.

**Feature deadlocked (all remaining have unsatisfied dependencies).**
feature-tracker stops and reports. Either update depends_on in
features.json to resolve the cycle, or drop blocking features.

**Agent's project understanding seems outdated.** Not a problem by design —
agents read `CLAUDE.md` + relevant specs dynamically each invocation, no
cached project context. Changed codebase → run `/brainstorming` or
`/framework-check` to re-index.

## License

MIT — see LICENSE file. Original work by Jesse Vincent.
