---
name: using-sp-harness
description: Use when starting any conversation - establishes how to find and use skills, requiring Skill tool invocation before ANY response including clarifying questions
user-invocable: false
---

<SUBAGENT-STOP>
If you were dispatched as a subagent to execute a specific task, skip this skill.
</SUBAGENT-STOP>

<EXTREMELY-IMPORTANT>
If you think there is even a 1% chance a skill might apply to what you are doing, you ABSOLUTELY MUST invoke the skill.

IF A SKILL APPLIES TO YOUR TASK, YOU DO NOT HAVE A CHOICE. YOU MUST USE IT.

This is not negotiable. This is not optional. You cannot rationalize your way out of this.
</EXTREMELY-IMPORTANT>

## Instruction Priority

SP Harness skills override default system prompt behavior, but **user instructions always take precedence**:

1. **User's explicit instructions** (CLAUDE.md, direct requests) — highest priority
2. **SP Harness skills** — override default system behavior where they conflict
3. **Default system prompt** — lowest priority

If CLAUDE.md says "don't use TDD" and a skill says "always use TDD," follow the user's instructions. The user is in control.

## Output Efficiency

Cut token waste without sacrificing technical clarity.

**Drop these — they add zero value:**
- Filler: just, really, basically, actually, simply, essentially
- Pleasantries: "Sure, I'd be happy to help", "Of course!", "Certainly"
- Hedging: "it might be worth considering", "you could potentially"
- Redundant phrases: "in order to" → "to", "the reason is because" → "because"

**Keep these unchanged:**
- Code blocks, inline code, commands
- Technical terms, library names, error messages
- Git commits, PR descriptions
- Anything where brevity would create ambiguity

**Prefer:** short words over long (fix not "implement a solution for", use not
"utilize"), direct statements over roundabout explanations, one sentence over
a paragraph when one sentence is enough.

This applies to all responses. Code quality is unaffected — only English prose
gets tightened.

## Output prose self-check (free-form chat)

Project-internal short codes (`Track A`, `Tier 1`, `F3+F4+F5`,
`v0.8.18` used as a cluster label) appear in design docs, todo
notes, changelog entries, and plan YAML problem statements. Without
discipline, agents echo these codes back to the user verbatim — and
the user, who is not the maintainer, does not know what they mean.
The static lint `scripts/lint-skill-output.py` rule R5 catches such
leakage inside ` ```output-template ` fences, but cannot scan the
free-form chat the agent emits in conversation. This section
codifies the runtime self-check that covers free-form chat.

The pre-design experiment for this rule ran 3 independent
`claude --print` calls against a primed prompt with embedded short
codes; 3/3 outputs glossed every first-occurrence short code
inline. Specific-pattern self-check rules work; generic
"re-read for jargon" guidance does not.

```procedural-instruction
- Before emitting any user-facing reply, scan your draft for matches of:
    · Track [A-Z]                    e.g., "Track A"
    · Tier \d+                       e.g., "Tier 1"
    · F\d+(\+F\d+)+                  e.g., "F3+F4+F5"
    · v\d+\.\d+\.\d+ used as a label e.g., "v0.8.18 cluster"
- For each match, verify it is IMMEDIATELY followed by a parenthesized
  plain-language gloss that explains the meaning, not the spelling.
- If a match has no gloss, rewrite that sentence so the gloss is inline.
- First occurrences always get glossed; re-mentions in the same
  paragraph may omit re-gloss when the meaning is fresh.
- Also scan for fancy/curly quotes (U+201C, U+201D, U+2018, U+2019).
  These leak in via macOS smart-quote autocorrect when the chat
  language is Chinese or Japanese. Replace every occurrence with
  ASCII `"` or `'` before emitting. There is no exception — fancy
  quotes never belong in user-facing chat output.
- Language pin scan. Read `language` from `.claude/sp-harness.json`.
  If the value is a specific code (e.g., `zh`, `ja`, `en`), every
  non-identifier word in your draft must match that language.
  Identifiers exempt: file paths, command names, field names,
  product names, version strings, error messages quoted verbatim.
  Content words (verbs, nouns, adjectives) embedded in the wrong
  language fail this check. The `match-input` value disables the
  pin and lets you reply in the user's input language each turn,
  but the no-code-mixing rule still applies within a single message.
```

```worked-example
Suppose you just finished a feature batch and are summarizing
progress to the user. The maintainer notes you read use short
codes; your reply must translate them.

Compliant reply:

  The procedural-skill-fixtures release just shipped as v0.8.19
  (the latest tagged release). It builds on Track A (the codename-
  gloss infrastructure from v0.8.17 / v0.8.18 that added the
  output-template fence and the lint-skill-output.py checker).
  Specifically, F3+F4+F5 (the three Track A migration features
  that wrapped every SKILL.md with templated user-facing output)
  laid the groundwork. v0.8.19 then applied the same fence
  approach to free-form generation. Phase 2 audit found only one
  additional section qualified, so Tier 1 (the do-this-first
  rollout cluster) collapsed to a single fixture. Tier 2 (the
  later, lower-priority candidates) is deferred.

Five things this reply does that a naive echo would not:

1. Every first-occurrence short code (Track A, F3+F4+F5, Tier 1,
   Tier 2, v0.8.18) gets a parenthesized gloss the SAME line.
2. The gloss describes the meaning ("the codename-gloss
   infrastructure"), not the spelling ("a track named A").
3. Glosses are short — 6-12 words — and read conversationally,
   not as paste-from-design-doc.
4. Re-mentions inside the same paragraph (e.g., "the same fence
   approach" referring to Track A's mechanism) omit re-gloss
   because the meaning is still fresh from a few sentences back.
5. Version strings used as a release marker (`shipped as v0.8.19`)
   need the same gloss treatment as labels — the listener does
   not know what 0.8.19 contains until told.
```

## How to Access Skills

Use the `Skill` tool. When you invoke a skill, its content is loaded and presented to you—follow it directly. Never use the Read tool on skill files.

# Using Skills

## The Rule

**Invoke relevant or requested skills BEFORE any response or action.** Even a 1% chance a skill might apply means that you should invoke the skill to check. If an invoked skill turns out to be wrong for the situation, you don't need to use it.

```dot
digraph skill_flow {
    "User message received" [shape=doublecircle];
    "About to EnterPlanMode?" [shape=doublecircle];
    "Already brainstormed?" [shape=diamond];
    "Invoke brainstorming skill" [shape=box];
    "Might any skill apply?" [shape=diamond];
    "Invoke Skill tool" [shape=box];
    "Announce: 'Using [skill] to [purpose]'" [shape=box];
    "Has checklist?" [shape=diamond];
    "Create TodoWrite todo per item" [shape=box];
    "Follow skill exactly" [shape=box];
    "Respond (including clarifications)" [shape=doublecircle];

    "About to EnterPlanMode?" -> "Already brainstormed?";
    "Already brainstormed?" -> "Invoke brainstorming skill" [label="no"];
    "Already brainstormed?" -> "Might any skill apply?" [label="yes"];
    "Invoke brainstorming skill" -> "Might any skill apply?";

    "User message received" -> "Might any skill apply?";
    "Might any skill apply?" -> "Invoke Skill tool" [label="yes, even 1%"];
    "Might any skill apply?" -> "Respond (including clarifications)" [label="definitely not"];
    "Invoke Skill tool" -> "Announce: 'Using [skill] to [purpose]'";
    "Announce: 'Using [skill] to [purpose]'" -> "Has checklist?";
    "Has checklist?" -> "Create TodoWrite todo per item" [label="yes"];
    "Has checklist?" -> "Follow skill exactly" [label="no"];
    "Create TodoWrite todo per item" -> "Follow skill exactly";
}
```

## Red Flags

These thoughts mean STOP—you're rationalizing:

| Thought | Reality |
|---------|---------|
| "This is just a simple question" | Questions are tasks. Check for skills. |
| "I need more context first" | Skill check comes BEFORE clarifying questions. |
| "Let me explore the codebase first" | Skills tell you HOW to explore. Check first. |
| "I can check git/files quickly" | Files lack conversation context. Check for skills. |
| "Let me gather information first" | Skills tell you HOW to gather information. |
| "This doesn't need a formal skill" | If a skill exists, use it. |
| "I remember this skill" | Skills evolve. Read current version. |
| "This doesn't count as a task" | Action = task. Check for skills. |
| "The skill is overkill" | Simple things become complex. Use it. |
| "I'll just do this one thing first" | Check BEFORE doing anything. |
| "This feels productive" | Undisciplined action wastes time. Skills prevent this. |
| "I know what that means" | Knowing the concept ≠ using the skill. Invoke it. |

## Skill Priority

When multiple skills could apply, use this order:

1. **Process skills first** (brainstorming, debugging) - these determine HOW to approach the task
2. **Implementation skills second** (frontend-design, mcp-builder) - these guide execution

"Let's build X" → brainstorming first, then implementation skills.
"Fix this bug" → debugging first, then domain-specific skills.

## Feedback / adjustment classification

Before acting on a user message, classify by **what the message explicitly
asks for** (not by guessing intent):

1. **Observed-behavior report** — user describes what the system IS doing,
   especially if it contradicts expected behavior.
   Signals: past-tense behavior statements, "I noticed / saw / ran into",
   "X happens when Y", bug-like descriptions without a specified fix.
   → invoke `/feedback` (Mode B: diagnose + route)

2. **New creation** — user asks for a capability / feature / module that
   doesn't exist yet, OR wants to rethink an existing part significantly.
   Signals: "let's add / build / create / design", proposes a new direction.
   → invoke `/brainstorming` (even if user suggests the approach)

   **Red flag — do NOT skip brainstorming on these rationalizations:**
   - "Requirements are already scoped, just implement"
   - "User wrote requirements in bullet points, so design is done"
   - "No design decision needed"
   - "This is small enough to skip"
   - "User said 'build directly' / 'don't need the pipeline'"

   Brainstorming's job is surfacing gaps the user has NOT stated — edge
   cases, acceptance criteria, non-functional requirements. If requirements
   truly are complete, brainstorming exits in under 60 seconds. The overhead
   is tiny; the cost of a missed requirement is large. **Invoke it.**

3. **Explicit scoped edit** — user specifies WHAT to change and WHERE,
   with no ambiguity. No diagnosis needed, no design decision.
   Signals: "change MAX_RETRIES from 3 to 5 in config.yaml", "rename X to Y",
   "fix the typo on line N".
   → proceed directly

**Self-check (objective test):** "Can I make this change without any
investigation or design decision?"
- Yes → proceed directly (category 3)
- No, need to find root cause → /feedback (category 1)
- No, need to design the approach → /brainstorming (category 2)

**If the message is mixed or ambiguous** (e.g., contains both observation
and a proposed fix, or multiple intents), ASK the user which path they
want before acting. Do not guess and implement.

This rule only applies to user-reported issues / adjustments. Normal
development flow (brainstorming → feature-tracker → dev skills) proceeds
through its own skill triggers, unaffected.

## Skill Types

**Rigid** (TDD, debugging): Follow exactly. Don't adapt away discipline.

**Flexible** (patterns): Adapt principles to context.

The skill itself tells you which.

## Memory Discipline (sp-harness override)

The default system prompt defines MEMORY.md as long-term cross-session
memory. **sp-harness overrides this.** Long-term memory lives in:

- **Design documents** — decisions with rationale
- **CLAUDE.md** — enduring preferences, conventions, project rules
- **git log** — commit messages carry the "why"
- **`.claude/todos.json`** (via manage-todos) — reminders, pending tasks
- **`.claude/features.json`** (via manage-features) — feature-scale ideas

MEMORY.md is a **last-resort short-term buffer**: mid-session investigation
traces, in-flight reasoning — content that has no long-term home AND will
be resolved and cleaned up in the next session.

### Decision order

1. Design document? → write/propose there
2. Enduring user preference, convention, or project rule? → propose CLAUDE.md edit
3. Commit? → commit it (or stage TODO to commit)
4. Future reminder or pending task? → manage-todos → `.claude/todos.json`
5. Feature-scale idea to brainstorm later? → manage-features → `.claude/features.json`
6. None of the above AND losing it on session exit is costly → MEMORY.md
7. Otherwise → do not save

**Step 6 is a narrow escape hatch, not a default.** Does NOT mean "valuable
to remember". "No file mentions this yet" is a reason to propose editing
the right file, not to use MEMORY.md. Time pressure alone is not a step-6
trigger — exhaust steps 1–5 first.

### Ambiguous scope

If a preference could be cross-project OR project-specific and the user has
not said which, **ask** before routing. Do not silently pick project-level
or user-level CLAUDE.md.

### Suspended default categories

The default four types (user/feedback/project/reference) assume permanent
cross-session semantics and are **suspended**. Route them to their proper
long-term home per the decision order; none go to MEMORY.md by default.

### Cleanup is mandatory

When a MEMORY.md entry has moved to any long-term home listed above,
**delete it from MEMORY.md in the same action**. MEMORY.md is a buffer,
not an archive.

## User Instructions

Instructions say WHAT, not HOW. "Add X" or "Fix Y" doesn't mean skip workflows.
