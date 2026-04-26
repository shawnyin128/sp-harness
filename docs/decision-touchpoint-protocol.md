# Decision Touch-Point Protocol

**Version**: 1.0 (introduced v0.8.10)
**Applies to**: every sp-harness output that asks the user to decide,
confirm, or review.

## Why this exists

Skills and agents in this repo print to two audiences:

1. **Other agents** — via plan YAMLs, JSON state, schema-tight files.
   These can be terse and reference-heavy.
2. **The human reviewer** — via terminal output that asks for a choice.
   These must read like prose written for someone who has not memorized
   the spec.

Historically, output rules drifted because "humanize the output" was
deployed as a project-level *principle* (in CLAUDE.md) rather than as an
operational *protocol* enforced at every output-generation site. The
result: format slots like `<situation>` or `<planner_view>` got filled
with raw spec IDs (`D1`, `F1`, `Option B`) and doc shorthand, because
nothing at the format-spec level forbade it. CLAUDE.md principles were
overridden by the concrete slots in front of the LLM.

This protocol fixes that by inlining the rules into every touch-point.

## What counts as a decision touch-point

Any terminal output where:

- The user is asked to pick an option (a/b/c, yes/no/adjust, ...), OR
- The user is asked to confirm before the system continues, OR
- The system reports a closure summary the user is expected to read
  before the next agent runs (e.g. feature-tracker's Feature Brief).

Pure agent-to-agent files (plan YAML, eval reports stored to disk) are
NOT touch-points and follow their own schemas.

## The four-part rule (for open decisions)

When the system asks the user to make a substantive choice, the prompt
MUST include these four parts in this order, each in plain language:

1. **Background** — what the current code or behavior state is that
   triggered this question. Describe the *situation*, not the spec
   section that documents it. No bare `D1` / `F1` / `step 3` / `Option B`
   without a translation in the same sentence.

2. **What it controls** — what observable behavior changes depending on
   which option the user picks. Describe the *consequence*, not the
   internal field that flips.

3. **My pick** — which option the system recommends, the confidence
   level, and a one-sentence reason. If the system genuinely has no
   recommendation, say "no recommendation — this is a values call"
   and explain why.

4. **Options** — each option as ONE sentence describing what happens
   if the user picks it, in plain language. Do NOT write
   `(b) Option B from spec` or `(c) approach 2`. If an option cannot
   be described without referring to its name in the spec, the option
   should not be presented to the user.

### Canonical shape

```
⚠️ <one-sentence question in plain language>
   Background: <code/behavior state — no bare spec IDs>
   What it controls: <observable behavior change>
   My pick: (x) <option label> — <reason>, <confidence>%
   Options:
     (a) <one-sentence consequence>
     (b) <one-sentence consequence>
     (c) <one-sentence consequence>
```

## The lighter rule (for structured menus)

Some touch-points are not open decisions but fixed menus the system
always presents (e.g. framework-check's "(a) Auto-fix all / (b) Auto
only / (c) Per-item / (d) Report only"; the dev skill's "(a) Send back /
(b) Force-merge / (c) Replan"). These do NOT need Background / What it
controls / My pick. They DO need:

- Each option spelled out as a plain-language consequence (not just
  the option name).
- A short header line describing the situation (one sentence is enough).

The reader must be able to choose without consulting the spec.

## The closure-summary rule (for reports the user reads, not picks from)

Closure summaries (feature-tracker's Feature Brief, framework-check's
final report, sp-feedback's findings list) follow these rules:

- Lead with plain-language label, follow with internal IDs in
  parentheses if needed.
- Field labels stay English for grepability; prose values follow the
  user's conversation language per the standing language-consistency
  rule (CLAUDE.md Principle 5).
- No raw doc vocabulary; if the closure mentions a feature/decision/
  step by ID, the same line includes a 3-6 word plain-language label.

## Forbidden patterns (apply to all three rules above)

- Bare `D1`, `F1`, `step 3`, `Option B`, `Approach 2` etc. without a
  same-sentence translation.
- Treating a spec section name as an explanation
  (`see § 4.2` is not Background).
- Listing options whose only differentiator is their label.
- Asking the user to confirm without saying what would happen if they
  said no.
- Confidence numbers without a reason.

## Compliance marker

Every file that defines a touch-point format MUST contain the literal
string `decision-touchpoint-protocol` somewhere in its body — either
as a reference link, a `Per docs/decision-touchpoint-protocol.md` lead,
or in a Rules section. `framework-check` greps for this marker as a
drift check (added v0.8.10).

## Touch-point inventory (for maintenance)

Files with touch-points (must contain the compliance marker):

**Open decisions:**
- `agent-templates/sp-planner.md` — Touch Point 1 (decisions ask)
- `agent-templates/sp-evaluator.md` — Touch Point 2 (verdict ask)
- `agent-templates/sp-feedback.md` — Mode A per-batch confirmation
- `skills/brainstorming/SKILL.md` — clarifying questions
- `skills/finishing-a-development-branch/SKILL.md` — completion options

**Structured menus:**
- `skills/three-agent-development/SKILL.md` — fix/force-merge/replan
- `skills/single-agent-development/SKILL.md` — same
- `skills/feature-tracker/SKILL.md` — "Ready to start?" gate
- `skills/framework-check/SKILL.md` — fix-path picker
- `skills/switch-dev-mode/SKILL.md` — regenerate confirm
- `skills/init-project/SKILL.md` — bootstrap Q&A

**Closure summaries:**
- `skills/feature-tracker/SKILL.md` — Step 2 progress + Step 5 Brief
- `skills/framework-check/SKILL.md` — final structured report
- `skills/requesting-code-review/code-reviewer.md` — review verdict

When adding a new touch-point, add it to this list and include the
compliance marker.
