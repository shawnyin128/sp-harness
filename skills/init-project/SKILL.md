---
name: init-project
description: |
  Bootstrap a new project with a lean, map-style CLAUDE.md (~50 lines),
  structured memory in .claude/mem/, and update-mem hooks. Use when starting
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
- **B**: Does `.claude/mem/` exist with `memory.md` and `todo.md`?
- **C**: Are Stop and UserPromptSubmit hooks configured in `.claude/settings.json`?

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

Memory lives in `.claude/mem/`. memory.md is a state snapshot, not a log.

**Session start — read in order:**
1. `.claude/mem/memory.md` — current state, decisions, findings
2. `.claude/mem/todo.md` — open problems
3. `git log --oneline -20` — recent commits
4. `docs/features.json` — feature progress (if exists)

**Rules:** update memory.md after every non-trivial task. Keep under ~40 lines.
Commits use `[module]: description` format.

---

## Project Map

{FILL: quick commands if detected, e.g. "build: npm run build | test: npm test", or omit if none}

### Design Docs
{FILL: tree listing of docs/ showing every subdirectory and file, e.g.:
docs/
├── design-docs/
│   └── (empty)
├── plans/
│   ├── active/
│   └── completed/
├── features.json
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
└── reports/           ← system-feedback and optimization reports
```

Skip any directories that already exist. Do not overwrite existing content.

If the project already has docs in a different structure (e.g.,
`docs/sp-harness/specs/`), leave them in place — the new structure
is for new documents going forward.

---

## Step 4: Create `.claude/mem/` files

If `.claude/mem/` already exists with both files (check B), skip this step.

Create any missing files:

**`.claude/mem/memory.md`:**
```markdown
# Project Memory

## Current State
Project just initialized. No work started yet.

## Key Decisions

## Findings
```

**`.claude/mem/todo.md`:**
```markdown
# Todo
```

Do not overwrite existing files.

---

## Step 5: Configure hooks

If hooks are already configured (check C), skip this step.

Create `.claude/hooks/update-mem-reminder.sh`:

```bash
#!/bin/bash
cat <<'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEMORY UPDATE CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After this response:
1. Did you make a design decision, find a root cause, or produce a result?
   → Update .claude/mem/memory.md
2. Did you find a new problem or resolve an existing one?
   → Update .claude/mem/todo.md

Skip if this was a trivial task (typo fix, formatting, single-line edit).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
```

Make it executable: `chmod +x .claude/hooks/update-mem-reminder.sh`

Get the absolute path: `<project_root>/.claude/hooks/update-mem-reminder.sh`

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

## Step 6: Confirm

Report a status line for each action:

```
CLAUDE.md                  ✓ created / ✓ updated / ✓ already complete
docs/                      ✓ directory structure created / ✓ already complete
.claude/mem/               ✓ initialized / ✓ already complete
.claude/settings.json      ✓ hooks configured / ✓ already complete
```

---

## Notes

- **Why both Stop AND UserPromptSubmit hooks?** Stop hook output goes to terminal
  only. UserPromptSubmit output is injected into Claude's context as a system
  reminder, which actually triggers the memory check.
- If the project has a PROPOSAL.md (research project), the user should use the
  research-specific init-project skill instead.
- After init completes, the project is ready for development.
