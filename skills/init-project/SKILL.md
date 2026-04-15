---
name: init-project
description: |
  Bootstrap a new project with a lean, map-style CLAUDE.md (~50 lines),
  structured state in .claude/, and todo-reminder hooks. Use when starting
  any new project or onboarding an existing codebase. Scans the repo to
  generate a project map automatically. Safe to re-run: skips completed steps.
author: sp-harness
version: 1.0.0
---

# init-project

Bootstrap a project with a lean CLAUDE.md and structured memory system.
Run once per project. Re-running is safe — completed steps are skipped.

---

## Step 0: Check what is already done

Check the following independently. Record results to skip completed steps.

- **A**: Does `CLAUDE.md` exist with all three required sections?
  Look for: `First-Principles`, `Context Management`, `Project Map`.
- **B**: Does `.claude/todos.json` exist? (replaces `.claude/mem/todo.md` from v0.4.0)
- **B2**: Does `.claude/memory.md` exist? (short-term session memory, reintroduced in v0.4.3 with tightened scope)
- **C**: Are Stop and UserPromptSubmit hooks configured in `.claude/settings.json`?
- **D**: Does `.claude/sp-harness.json` exist with `dev_mode` AND `external_codebase`?
- **E**: Does `.claude/agents/sp-feedback.md` exist? If dev_mode is three-agent, also check sp-planner.md, sp-generator.md, sp-evaluator.md.

If all are done, report "All steps already complete." and stop.

---

## Step 1: Scan the project

Examine the repository to understand what this project is. Read (if they exist):

- `README.md` or `README.*` — project purpose
- `package.json`, `Cargo.toml`, `pyproject.toml`, `go.mod`, etc. — language, build/test commands
- Top-level directory listing — key directories and their purpose
- `docs/` directory listing — existing documentation

Extract:

1. **Project name**
2. **Quick commands**: build, test, lint, dev server (from package.json scripts, Makefile, etc.)
3. **Docs tree**: full directory tree of docs/ — every subdirectory and file
4. **Codebase tree**: top-level directories and key subdirectories with a few
   words each (e.g., `src/api/ — REST endpoints`). Keep it brief.

If the project is empty or has no recognizable structure, ask the user to describe
what the project will be. Use their answer for the Project Map section.

---

## Step 2: Create CLAUDE.md

If `CLAUDE.md` already exists with all three sections (check A), skip this step.

If `CLAUDE.md` exists but is incomplete, **merge** missing sections in — do not
overwrite existing content.

If `CLAUDE.md` does not exist, create it using the EXACT template below.

**STRICT RULES — read before writing:**
- Copy the template EXACTLY. Do not rearrange, rename, or add sections.
- The ONLY parts you fill in are marked with `{FILL}`. Everything else is literal.
- Do NOT add: Key References, tables, extra headings, summaries, language
  preferences, "respond in X language", or ANY content not in the template.
- Total CLAUDE.md MUST stay under 80 lines.
- If you are tempted to "improve" the template — stop. Use it as-is.

### Template (copy exactly, fill in `{FILL}` parts only):

````markdown
# {FILL: project name}

## First-Principles Standards

**1. Clarify before acting.**
If the goal is unclear, stop and ask. Do not infer intent silently.

**2. Shortest path wins.**
If a better approach exists, say so and wait for a decision.

**3. Fix root causes, not symptoms.**
Find out why before touching code. No defensive patches.

**4. Output only what changes decisions.**
Skip preamble, summaries, and obvious observations.

---

## Context Management

State lives in structured files — each concern has one authoritative source.

**Session start — read in order:**
1. `CLAUDE.md` — this file (map + principles)
2. `.claude/features.json` — feature list and status
3. `.claude/sp-harness.json` — config (dev_mode, hygiene counter, external_codebase flag)
4. `.claude/codebase-context.md` — only if sp-harness.json has `external_codebase: true`
5. `.claude/todos.json` — idea backlog
6. `.claude/memory.md` — short-term session memory (undecided observations)
7. `git log --oneline -20` — recent activity
8. `git status` — uncommitted work (where you physically left off)

**Rules:**
- commits use `[module]: description` format
- Decided ideas → `.claude/todos.json` (manage-todos)
- Decided requirements → `.claude/features.json` (manage-features)
- Undecided observations → `.claude/memory.md`
- Design rationale → `docs/design-docs/`
- Reusable patterns → raise via sp-feedback (agent-memory)

Each concern has ONE home. Never duplicate across sources.

---

## Project Map

{FILL: commands from package.json/Makefile, e.g. "build: npm run build | test: npm test". Omit this line entirely if no build system found.}

### Design Docs
{FILL: tree listing of docs/ showing every subdirectory and file, e.g.:
docs/
├── design-docs/
│   └── (empty)
├── plans/
│   ├── active/
│   └── completed/
└── reports/
}

### Codebase
{FILL: directory tree of code dirs, a few words per entry, e.g.:
src/api/        — REST endpoints
src/models/     — data layer
tests/          — pytest suite
}
````

---

## Step 3: Create docs directory structure

Create the standard documentation hierarchy if it does not exist:

```
docs/
├── design-docs/       ← specs from brainstorming
├── plans/
│   ├── active/        ← plans currently being executed
│   └── completed/     ← finished plans (moved here after completion)
└── reports/           ← sp-feedback optimization reports
```

Skip any directories that already exist. Do not overwrite existing content.

If the project already has docs in a different structure (e.g.,
`docs/sp-harness/specs/`), leave them in place — the new structure
is for new documents going forward.

---

## Step 4: Create state files

### 4a. `.claude/todos.json` (idea backlog)

If already exists (check B), skip.

Create with empty backlog:
```json
{
  "todos": []
}
```

`todos.json` holds high-level ideas/directions that need brainstorming to
scope into concrete features. Operations via `sp-harness:manage-todos` —
don't hand-edit in ways that break the schema.

### 4b. `.claude/memory.md` (short-term session memory)

If already exists (check B2), skip.

Create with this EXACT content (template + scope comment):

````markdown
# Session Memory (short-term, pre-triage)

<!--
SCOPE: Observations not yet decided how to handle. Cleared as triaged.

WHAT GOES HERE:
  - bug: observed, not yet verified or decided to fix
  - hypothesis: theory under investigation
  - concern: raised but undecided
  - note: mid-investigation progress

WHAT DOES NOT GO HERE (already decided → SKIP memory, go direct):
  - Ideas to pursue → sp-harness:manage-todos add
  - Bugs to fix → sp-harness:manage-features add (fix_feature)
  - Reusable patterns → raise via sp-feedback (routes to agent-memory)
  - Design decisions → docs/design-docs/
  - Project architecture → CLAUDE.md + docs/

BEFORE ADDING (mandatory triage of existing entries):
  For each existing entry, run these checks in order:
    1. `git log --since="<entry timestamp>" -- <referenced-file>` — resolved?
    2. grep todos.json / features.json for entry's key terms — now tracked?
    3. Still undecided? Keep. Otherwise remove.
  Then add the new entry.

HARD RULE: NEVER duplicate with todos.json / features.json / agent-memory.
Keep under 30 lines. If bloated, triage before adding more.
-->

## Observations

<!-- Format: - [YYYY-MM-DD] [bug|hypothesis|concern|note] description — refs: <file:line, feature-id, commit-sha, ...> -->

## In-flight

<!-- One block, replaced (not appended) as investigation progresses.
- Investigating: ...
- Checked: ...
- Next: ...
-->
````

### 4c. Legacy cleanup (pre-0.4.x projects)

- If `.claude/mem/todo.md` exists: do NOT delete. Report:
  "Legacy todo.md detected. Transfer ideas to `.claude/todos.json` via manage-todos."
- If `.claude/mem/memory.md` exists: do NOT delete. Report:
  "Legacy memory.md detected (old scope). The new memory.md has a tighter
  scope (short-term pre-triage observations only). Review old content:
  design decisions → docs/, decided ideas → todos.json, decided fixes →
  features.json. After migration, delete the old file."
- `.claude/mem/` directory may become empty after user migrates; they can remove it.

---

## Step 5: Configure hooks

If hooks are already configured (check C), skip this step.

Create `.claude/hooks/update-context-reminder.sh`:

```bash
#!/bin/bash
cat <<'EOF'
CONTEXT CHECK: If this task surfaced anything worth remembering, route it:
  - Decided idea/direction → sp-harness:manage-todos add (.claude/todos.json)
  - Decided bug to fix → sp-harness:manage-features add with fix_feature
  - Undecided observation (bug/hypothesis/concern/in-flight) → append to
    .claude/memory.md (before adding, triage existing entries against git log
    and other state sources — remove any already-resolved or already-tracked)

Each concern has ONE home. Never duplicate across sources.
EOF
```

Make executable: `chmod +x .claude/hooks/update-context-reminder.sh`

Get absolute path with `pwd`: `$(pwd)/.claude/hooks/update-context-reminder.sh`

Configure `.claude/settings.json` with both `Stop` and `UserPromptSubmit` hooks.
If settings.json already exists, **merge** — do not overwrite existing hooks.

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"<absolute_path_to_hook>\""
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "\"<absolute_path_to_hook>\""
          }
        ]
      }
    ]
  }
}
```

**CRITICAL**: The path in `command` MUST be wrapped in escaped double quotes
to handle spaces in paths.

---

## Step 6: Configure development mode and generate project-level agents

All agent definitions are project-level. Plugin ships templates at
`${CLAUDE_PLUGIN_ROOT}/agent-templates/sp-*.md`. init-project **always**
generates project-level copies adapted to this project's context.

### Q1: Dev mode

> "Which development mode? (a) Three-agent — Planner, Generator, Evaluator as separate subagents (recommended for complex projects), (b) Single-agent — one agent plays all three roles sequentially (faster, lower token cost)"

### Step 6a: Generate sp-feedback (always, regardless of dev mode)

Read `${CLAUDE_PLUGIN_ROOT}/agent-templates/sp-feedback.md`. Replace:
- `{PROJECT_NAME}` → project name from CLAUDE.md
- `{PROJECT_CONTEXT}` → 2-4 lines summarizing: stack, key modules, critical
  invariants identified during Step 1 scan

Write to `.claude/agents/sp-feedback.md`.

### Step 6b: If three-agent, generate sp-planner / sp-generator / sp-evaluator

Print defaults from templates:
```
Default three-agent configuration (from agent-templates/):
  sp-planner:   opus, tools=Read/Grep/Glob/Bash/Write/Edit/Skill, memory=project, skills=sp-harness:writing-plans
  sp-generator: sonnet, isolation=worktree, skills=subagent-driven-dev+TDD+git-convention
  sp-evaluator: opus, tools=Read/Grep/Glob/Bash, memory=project
```

**Q2:** "Use these defaults? (yes/no)"

- **If yes:** For each of sp-planner, sp-generator, sp-evaluator:
  Read template from `${CLAUDE_PLUGIN_ROOT}/agent-templates/{name}.md`.
  Replace `{PROJECT_NAME}` and `{PROJECT_CONTEXT}` with project-specific values.
  Write to `.claude/agents/{name}.md`.

- **If no:** For each agent, ask:
  1. "Model?" (opus / sonnet / haiku / inherit)
  2. "Tools?" (default / read-only / custom list)
  3. "Cross-session memory?" (none / project / user / local)
  4. "Isolated worktree?" (yes / no)

  Read template, override frontmatter fields with user answers, fill context,
  write to `.claude/agents/{name}.md`.

### Step 6c: External codebase question

> "Is this project an existing codebase that wasn't built through sp-harness?
>  (e.g., legacy code, third-party integration, or a project predating
>  your sp-harness adoption.)
>  - Yes → I'll scan the codebase once and save the structured understanding
>    to `.claude/codebase-context.md` as ground truth for downstream skills.
>  - No → skip; design docs from brainstorming will be the source of truth.
>    You can re-run `init-project` later if external code gets added."

If **Yes** → run a deep scan now (read key source files, identify modules,
find variants, check git activity for active vs stale). Save to
`.claude/codebase-context.md` with this structure:

```markdown
# Codebase Context (external, pre-sp-harness)

Generated: <ISO date> by init-project
Scope: <directories scanned>

## Core modules
- <path> — <what it does> [active|stale|deprecated]

## Variants found
- <functionality>: <path A> vs <path B> — <key difference>

## Module dependencies
- <module A> → <module B> for <reason>

## Notes
<anything else worth recording>
```

Set `external_codebase: true` in sp-harness.json (next step).

If **No** → skip scan, do not create the file. Set `external_codebase: false`.

### Step 6d: Write config

```json
{
  "dev_mode": "three-agent" | "single-agent",
  "last_hygiene_at_completed": 0,
  "external_codebase": true | false
}
```

to `.claude/sp-harness.json`.

**Single-agent mode note:** only `sp-feedback.md` is generated as a subagent.
Planner/Generator/Evaluator roles are played by main session — no subagent
definitions needed for them.

---

## Step 7: Confirm

Report a status line for each action:

```
CLAUDE.md                  ✓ created / ✓ updated / ✓ already complete
docs/                      ✓ directory structure created / ✓ already complete
.claude/todos.json         ✓ initialized (empty backlog) / ✓ already complete
.claude/memory.md          ✓ initialized (template) / ✓ already complete
.claude/settings.json      ✓ hooks configured / ✓ already complete
.claude/sp-feedback-calibration.json  (auto-created on first sp-feedback run)
.claude/sp-harness.json    ✓ dev_mode={mode}, external_codebase={true|false}
.claude/codebase-context.md  ✓ generated (only if external_codebase=true) / — skipped
.claude/agents/            ✓ sp-feedback.md + {3 dev agents if three-agent}
```

---

## Notes

- Stop hook: terminal display only. UserPromptSubmit hook: injected into agent context (triggers context-routing checks for todos/memory/features).
- After init, project is ready for brainstorming.
