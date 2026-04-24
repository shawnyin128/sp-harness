---
name: feedback
description: |
  User-triggered feedback mode. When you observe a problem while using the
  system (bug, missing feature, agent misbehavior, performance issue, etc.),
  invoke this to have sp-feedback diagnose and route the fix back into the
  pipeline. Asks clarifying questions before analysis.
author: sp-harness
version: 3.0.0
---

# feedback

Entry point for **Mode B** of sp-feedback (the feedback agent).

Use when you are using a project built with sp-harness and you notice something
is wrong — a bug, a missing feature, an agent that behaves poorly, a
performance issue. Instead of describing it informally, invoke this skill to
get structured diagnosis and routed fixes.

## Step 1: Verify sp-feedback exists

Check `.claude/agents/sp-feedback.md` exists. If not, tell the user to run
`init-project` first to generate the feedback agent.

## Step 2: Capture user observation

Ask the user (if not already stated in the invocation):

> "What did you observe? Describe the problem briefly."

## Step 3: Dispatch sp-feedback in Mode B

Invoke `@agent sp-feedback` with:
- The user's observation
- Mode flag: `"mode": "B"`
- The orchestrator is YOU (the main session)

sp-feedback will:
1. Ask clarifying questions one at a time (what/when/expected/reproducible)
2. Run scoped checklist review based on the user's complaint
3. Auto-execute memory operations (no user gate)
4. Write `.claude/agents/state/active/feedback-actions.json`
5. Present findings grouped by action type

## Step 4: Review auto-executed memory ops

sp-feedback has already executed `memory_update` and `memory_compact` actions
before returning. Read the results from `.claude/agents/state/active/memory-ops-log.json`
and print a brief summary:

```
Auto-executed memory operations:
  memory_update: X applied, Y rejected by target agent
  memory_compact: Z agents compacted (before/after line counts)
```

This is FYI only — no confirmation needed. Agents decide via structured
checklists. Details auditable in memory-ops-log.json.

## Step 5: Per-batch confirmation (HARD-GATE for remaining actions)

For actions that require user input (`new_todo`, `fix_feature`, `manual`):

- "Add N new todos to idea backlog? (feature ideas that need brainstorming)"
- "Append M fix features to features.json? (bugs ready for direct development)"
- "Manual items: {list} — spec/architecture concerns for your review"

Wait for confirmation per batch before applying.

## Step 6: Execute approved actions

For confirmed batches:

- **new_todo**: for each approved item, invoke `sp-harness:manage-todos` Add
  with description, category (mapped from root_cause), and notes. The todos
  sit in `pending` state awaiting future brainstorming.
- **fix_feature**: invoke `sp-harness:manage-features` Add operation:
  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/skills/manage-features/scripts/mutate.py" add \
    --id=<kebab-id> --display-name="<3-5 word noun phrase>" \
    --category=functional --priority=<high|medium|low> \
    --description="<from finding>" --steps="<from suggestion>"
  ```
  Derive the display_name from the finding (what the fix IS, not what you
  do) — don't fall back to the heuristic. Will be picked up by
  feature-tracker on next loop.
- **manual**: print to user, no automated action.

## Step 7: Update calibration log

For each finding in feedback-actions.json, update the matching entry in
`.claude/sp-feedback-calibration.json` `findings_history`:

- User accepted the action → `user_action: "accepted"`
- User rejected → `user_action: "rejected"`
- Manual items → `user_action: "manual_deferred"`

Do NOT touch `runtime_validation` — that's set by sp-feedback itself
on Mode B or by staleness pass.

## Rules

1. Never skip the clarifying questions phase — user complaints are often vague.
2. Memory operations auto-execute before user gates. No confirmation needed.
3. new_todo / fix_feature / manual require per-batch confirmation.
4. Never write directly to another agent's MEMORY.md — always dispatch with
   the Append/Compact Checklist context.
5. Never auto-append to features.json without design — use new_todo for ideas
   that need brainstorming, fix_feature only for clearly scoped bugs.
6. After execution, summarize what was auto-executed, what was confirmed,
   and what was deferred.
