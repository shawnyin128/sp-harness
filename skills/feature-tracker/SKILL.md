---
name: feature-tracker
description: |
  Incremental feature development orchestrator. Reads .claude/features.json,
  picks the highest-priority unfinished feature, and drives it through
  the configured development mode (three-agent or single-agent). Loops
  automatically: after each feature completes, picks the next one.
  Use when starting or resuming feature development.
author: sp-harness
version: 3.4.0
---

# feature-tracker

Orchestrate incremental development by working through features one at a time.

<EXTREMELY-IMPORTANT>
Every feature follows the SAME path: Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → back to Step 2.
This is a LOOP. After completing a feature, you MUST return to Step 2 and pick the next one.
You do NOT stop after one feature unless ALL features pass or the user tells you to stop.
</EXTREMELY-IMPORTANT>

---

## Step 1: Read context, validate config, validate hygiene counter

Read these in order:

1. `.claude/features.json` — the feature list and status
2. `.claude/sp-harness.json` — harness configuration (dev_mode, hygiene counter, external_codebase flag)
3. `.claude/todos.json` — idea backlog (check for pending todos)
4. `git log --oneline -20` — recent commits
5. `git status` — uncommitted work (if any, someone was in the middle of something)

If `.claude/features.json` does not exist, inform the user and suggest running
brainstorming first to create one. STOP.

**MUST: Config validation — do this IMMEDIATELY after reading files.**

1. **If `.claude/sp-harness.json` does not exist:**
   - Create it with default values:
     ```json
     {"dev_mode": "single-agent", "last_hygiene_at_completed": 0, "external_codebase": false, "language": "match-input"}
     ```
   - Report: "Created sp-harness.json with defaults (single-agent mode, hygiene counter 0, no external codebase, language match-input)"
2. **If it exists:** read `dev_mode`, `last_hygiene_at_completed`, `external_codebase`, `language`
3. **If `dev_mode` is missing:** set to `"single-agent"`, write to disk
4. **If `last_hygiene_at_completed` is missing:** set to `0`, write to disk
5. **If `external_codebase` is missing:** set to `false`, write to disk
6. **If `language` is missing:** set to `"match-input"`, write to disk
   (`match-input` = reply in the user's input language each turn;
    a specific code like `en`, `zh`, `ja` = pin replies to that language
    regardless of input. Either way, code-mixing is forbidden and
    files/commits/docs always stay English.)

**MUST: Declare session language and follow it.**

Right after reading `language` from `.claude/sp-harness.json`,
print `Session language: <code>` as the first line of your reply for
this session. Then follow the rule for the remainder of the session:

- `match-input` (default) — reply in the user's input language each
  turn.
- Any specific code (`en`, `zh`, `ja`, ...) — pin replies to that
  language regardless of input.

In either mode, no code-mixing within a single message. Identifiers
(file paths, command names, field names, product names, IDs) stay in
their original form. Files / commits / docs / plan YAML always
English regardless of chat language. This rule mirrors the one already
present in sp-planner / sp-evaluator / sp-feedback subagent templates;
it exists here because the orchestrator's own terminal output (progress
summary, decision asks, feature briefs) goes through the main session
and was previously not bound by the rule.

**MUST: Hygiene counter validation — ONLY validates. Does NOT trigger cleanup.**

1. Read `last_hygiene_at_completed` from `.claude/sp-harness.json`
2. Count features with `"passes": true` → `completed_count`
3. Compute `delta = completed_count - last_hygiene_at_completed`
4. **Validate:** `delta` MUST be < 3. If `delta >= 3`, something went wrong
   (Step 5 should have cleaned up). Report warning:
   "Hygiene counter invalid: delta={delta}, expected < 3. Will clean in Step 5."

---

## Step 2: Show progress summary

Get stats via script:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" stats
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" list --passes=false
```

Present a brief status to the user combining the outputs:

```
Feature Progress: <passed>/<total> completed
Dev Mode: {dev_mode}
Hygiene: last at {last_hygiene_at_completed}, next at {last_hygiene_at_completed + 3}

Remaining (from script output — display_name primary, id on indented line):
  · [priority] Display Name
      id: feature-id   deps: Dep Display Name
      Description text
  ...
```

---

## Step 3: Pick next feature

Use `sp-harness:manage-features` (invoked via its bundled script) to pick:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" next --format=table
```

**Exit behavior:**
- **Exit 0, feature printed** → proceed, present feature to user (the script
  output already includes all fields: id, description, priority, depends_on,
  from_todo, steps)
- **Exit 0, `{"all_done": true}`** → jump to Step 5's "ALL features pass" branch
  (dispatch sp-feedback)
- **Exit 1, `{"deadlock": true, ...}`** → print the blocked features and their
  unmet dependencies. STOP and ask user to resolve.

Ask the user — this is a decision touch-point per
`${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md`, so spell out both paths:

```
→ Ready to start "<display_name>" (<feature-id>)?
  · yes  → dispatch the development skill (<dev_mode>) on this feature now.
  · pick → show the remaining list and let you choose a different one.
  · no   → stop here; nothing runs until you come back.
```

Wait for user confirmation before proceeding.

**Do NOT hand-implement the selection algorithm.** The script is the
authoritative implementation.

---

## Step 4: Invoke development skill

Read `dev_mode` from `.claude/sp-harness.json` and dispatch accordingly:

**If `dev_mode` is `"three-agent"`:**
Invoke `sp-harness:three-agent-development` with the selected feature.

This skill will:
1. Dispatch sp-planner subagent → writes `<feature-id>.plan.yaml` (problem, steps, decisions)
2. **Print condensed plan summary and ask for decisions needing user input**
3. Dispatch sp-generator subagent → appends execution sections to plan YAML (no terminal output)
4. Dispatch sp-evaluator subagent → appends `eval.rounds[]` with per-round verdict
5. Handle Round-based iteration (fix / force-merge / replan) or optimization pass on PASS

**If `dev_mode` is `"single-agent"`:**
Invoke `sp-harness:single-agent-development` with the selected feature.

Same pipeline (Plan → Implement → Evaluate) but all phases run in the
main session without subagent dispatch. See single-agent-development for details.

---

You will see the plan and approve it before any code is written.

When the development skill returns PASS, feature-tracker proceeds to Step 5.
If REJECT, feature-tracker stops and reports to user.

---

## Step 5: Commit, hygiene cleanup, LOOP BACK

<EXTREMELY-IMPORTANT>
Step 5 runs as a single unit. Every MUST-block below — archive plan,
check todo, commit completion, hygiene cleanup, Print Feature Brief,
loop-back-to-Step-2 — must execute in order with no early exit. In
particular, if hygiene is dispatched (5d), control returns here; the
brief and the loop-back still owe you. The hygiene skill prints a
sentinel line ("CONTROL RETURNS TO feature-tracker Step 5d.d ...") and
writes `next_action: "continue_step_5d_d"` to its result file precisely
to remind you of this — heed both signals and continue.
</EXTREMELY-IMPORTANT>

The dev skill (three-agent or single-agent) already archived state files
to `.claude/agents/state/archive/<feature-id>/` on PASS.

**MUST: Archive completed plan.**

If `docs/plans/active/` contains the plan for this feature, move it to
`docs/plans/completed/`. No index file needed — git tracks the move.

**MUST: Check originating todo completion.**

Get the feature's `from_todo` field via script:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" \
  get <feature-id>
```

Read the `from_todo` field from the output. If non-null:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-todos/scripts/mutate.py" \
  check-done <todo-id>
```

If the result shows `done=true`, the todo auto-transitioned to done
(manage-todos handled it). Include `.claude/todos.json` in the upcoming
commit. If `done=false`, remaining features are listed — no further
action needed.

**MUST: Commit feature completion — do NOT skip:**

Fetch the display_name for the completed feature:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/query.py" \
  get <feature-id> --format=json
```
Parse `display_name` from that JSON (fall back to `<feature-id>` if the
field is missing or empty — shouldn't happen after backfill, but stay safe).

```
git add .claude/features.json .claude/sp-harness.json \
        .claude/agents/state/archive/ .claude/todos.json \
        docs/plans/
git commit -m "[features]: complete \"{display_name}\" ({feature-id})"
```
This commit is how new sessions know which features are done via `git log`.
Without it, the session start protocol's git log step is useless.

**MUST: Hygiene cleanup — AUTOMATIC, do NOT ask the user for permission.**

a. Read `last_hygiene_at_completed` from `.claude/sp-harness.json`
b. Count features with `"passes": true` → `completed_count`
c. Compute `delta = completed_count - last_hygiene_at_completed`
d. **If delta >= 3:**
   a. Print: "Hygiene threshold reached (delta={delta}). Running code-hygiene now."
   b. Invoke `sp-harness:code-hygiene` IMMEDIATELY. Do NOT ask "should I run
      hygiene?" or "would you like me to clean up?". This is automatic. Just do it.
   c. Read `.claude/agents/state/active/hygiene-result.json`
   d. **If file exists AND `status` is `"complete"`:**
      - Set `last_hygiene_at_completed` to `completed_count` in `.claude/sp-harness.json`
      - Write sp-harness.json to disk
      - Delete `.claude/agents/state/active/hygiene-result.json`
      - Report: "Hygiene complete. Counter updated to {completed_count}."
      - **DO NOT STOP here.** Hygiene is not the terminal step of this
        feature. Continue immediately to "MUST: Print Feature Brief"
        below, then back to Step 2. Hygiene's commit + report does not
        replace the brief, and the brief does not replace the
        loop-back. All three still owe you.
   e. **If file missing OR status is NOT `"complete"`:**
      - Do NOT update the counter
      - Warn: "Hygiene did not complete. Counter not updated. Will retry next loop."
e. **If delta < 3:** continue

**MUST: Print Feature Brief — this is the LAST output for this feature.**

This is a closure-summary touch-point per
`${CLAUDE_PLUGIN_ROOT}/docs/decision-touchpoint-protocol.md`. The brief
is no longer hand-assembled from prose. **MUST run this script — do
not improvise the brief:**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/feature-tracker/scripts/print-brief.py" <feature-id>
```

The script reads
`.claude/agents/state/archive/<feature-id>/<feature-id>.plan.yaml`,
fetches `display_name` from `.claude/features.json`, derives the short
git hash via `git rev-parse --short HEAD`, and emits the canonical brief
on stdout. Print the script's stdout verbatim — do not rewrap, restyle,
translate, or summarize. The script's output IS the brief.

This step MUST come after hygiene cleanup and BEFORE the all-done branch
or the loop-back-to-Step-2 jump. The brief is the final per-feature
output the user sees; nothing else may print between it and the next
loop iteration. If hygiene ran and printed output, the brief still
prints after hygiene — it is always the closing line for the current
feature. Hygiene's report and sentinel line do NOT substitute for the
brief; the brief is mandatory regardless of whether hygiene ran.

**Language exception (intentional, do not "fix"):** the scripted brief
is English-only regardless of the `language` field in
`.claude/sp-harness.json`. Plan YAML is English-only by schema (see
`${CLAUDE_PLUGIN_ROOT}/docs/plan-file-schema.md`); the script reads
verbatim; runtime translation is incompatible with the determinism the
script is here to provide. This carves out a single line of language
inconsistency — accepted as the cost of guaranteed brief delivery.

Reference output format the script produces (do not re-implement
in prose):

```
─── Feature complete: "<display_name>" (<feature-id>) ───
What:      <one-line problem statement, whitespace-collapsed>
Steps:     <N steps · M commits>
Files:     <unique paths from steps[].files + unplanned_changes[].loc, "—" if none>
Tests:     <N tests · avg X% coverage from the last eval round>
Rounds:    <N (PASS in round Y)>
Followups: <K suggestions / "—">
Commit:    <short hash>
─────────────────────────────────────────────────────────
```

Rules:
- Do NOT dispatch any subagent for this step. Run the script directly.
- Do NOT compress this into the commit message body — it is terminal
  output only.
- The script handles missing YAML fields by printing "—". Do not
  pre-process the YAML or "fix" missing fields before running it.
- If the script exits non-zero, the archive is missing or malformed.
  Investigate; do not improvise a brief from memory.

3. **Check if ALL features pass:**
   - **NO (features remain)** → GO BACK TO STEP 2 NOW.
   - **YES (all pass)** →
     ```
     All features complete. .claude/features.json shows X/X passing.
     Dispatching sp-feedback (Mode A) for system-level review.
     ```
     Dispatch `@agent sp-feedback` with `"mode": "A"`. This is the only exit
     from the loop. sp-feedback runs the structured checklist, writes
     `.claude/agents/state/active/feedback-actions.json`, and presents findings
     grouped by action type. You (orchestrator) then handle per-batch
     user confirmation and action execution (see sp-feedback's definition
     for the protocol).

     **If sp-feedback results in new_todo or fix_feature actions** that
     the user approves → append to features.json and re-enter the loop
     at Step 2 to develop them.

---

## Rules

1. One feature per cycle — do not batch multiple features
2. Verification is handled by the development skill's Evaluator — do not
   mark passes: true without Evaluator PASS verdict
3. Never skip the user confirmation in Step 3
4. If a feature turns out to be too large during implementation, pause and
   split it into sub-features in features.json before continuing
5. If implementation reveals a new feature that is needed, add it to
   features.json with appropriate priority — do not scope-creep the current feature
6. Step 1 VALIDATES the hygiene counter (exists, value is sane).
   Step 5 TRIGGERS cleanup (invokes code-hygiene, updates counter).
   Never skip either step.
7. To switch dev_mode, use `sp-harness:switch-dev-mode` skill.
