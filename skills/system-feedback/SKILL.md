---
name: system-feedback
description: |
  System-level optimization review after all features are complete. Analyzes
  the entire codebase across four dimensions (performance, user experience,
  code quality, architecture) and produces a file-level optimization report.
  Triggered by feature-tracker when all features pass.
author: superpowers
version: 1.0.0
---

# system-feedback

Comprehensive system-level review after all features are implemented and tested.
This is NOT about whether features work (that is feature-tracker + tests).
This is about making the system better: faster, cleaner, more maintainable.

**Trigger:** feature-tracker invokes this when all features in docs/features.json
pass. Can also be invoked manually at any time.

---

## Step 1: Gather Context

Read:
1. `docs/features.json` — what was built
2. `.claude/mem/memory.md` — key decisions and findings
3. `CLAUDE.md` — project map, architecture
4. The spec document(s) referenced in CLAUDE.md
5. `git log --oneline -30` — recent change history

Scan the codebase:
- List all source files changed during this development cycle (from git)
- Note file sizes, directory structure, dependency graph

---

## Step 2: Run Fixed Checks

For each dimension, run these concrete checks. Report findings at file level.

### Performance Checks

- [ ] **Hot loops:** Any nested loops over collections that could be flattened
      or indexed? (file + line)
- [ ] **Redundant computation:** Same calculation done multiple times where
      result could be cached or memoized? (file + function)
- [ ] **N+1 patterns:** Database/API calls inside loops? (file + line)
- [ ] **Blocking operations:** Synchronous I/O on hot paths where async is
      available? (file + function)
- [ ] **Bundle/payload size:** Large imports, unused dependencies, oversized
      assets? (file + import)
- [ ] **Memory patterns:** Large objects held longer than needed, growing
      collections without bounds? (file + variable)

### User Experience Checks

- [ ] **Error states:** Every error path shows a meaningful message to the user,
      not a raw exception or generic "something went wrong"? (file + error handler)
- [ ] **Empty states:** UI/output handles zero-data gracefully (empty lists,
      first-time use, no results)? (file + component/function)
- [ ] **Loading states:** Long operations show progress or feedback? (file + operation)
- [ ] **Input validation:** User input validated early with clear feedback on
      what is wrong and how to fix it? (file + input handler)
- [ ] **Edge cases:** Boundary values handled (empty string, max length, special
      characters, concurrent access)? (file + function)

### Code Quality Checks

- [ ] **Duplication:** Similar code blocks (>10 lines) that should be extracted
      to a shared function? (file A + file B + description)
- [ ] **Complexity:** Functions over ~40 lines or with >3 levels of nesting
      that should be decomposed? (file + function)
- [ ] **Naming:** Inconsistent naming patterns across the codebase (camelCase
      vs snake_case mix, unclear abbreviations)? (file + examples)
- [ ] **Dead code:** Unused functions, unreachable branches, commented-out code
      that should be removed? (file + symbol)
- [ ] **Dependency hygiene:** Unused imports, circular dependencies, dependencies
      that could be eliminated? (file + import)

### Architecture Checks

- [ ] **Single responsibility:** Any file/module doing more than one job? (file + description)
- [ ] **Coupling:** Components that know too much about each other's internals?
      (file A → file B, what is leaked)
- [ ] **Interface clarity:** Public APIs that are hard to use correctly or easy
      to misuse? (file + function signature)
- [ ] **Spec alignment:** Implementation matches the original spec's architecture
      design? Any drift? (spec section → actual implementation)

---

## Step 3: Run Deep Analysis

Beyond the fixed checks, apply analytical thinking to find issues the checklist
misses. For each dimension, answer:

**Performance:**
- Where is the system's bottleneck? Trace the critical path from user action
  to response. Which step is slowest?
- If load doubles, what breaks first?

**User Experience:**
- Walk through the primary user flow end-to-end. Where does the user have to
  think or wait? Where might they get confused?
- What happens when things go wrong in the middle of a flow?

**Code Quality:**
- If a new developer reads this codebase tomorrow, where will they get confused?
- Which file would you be most afraid to modify? Why?

**Architecture:**
- Does the current structure support the next likely changes? (Check todo.md
  and any known future requirements)
- Is there a simpler way to achieve the same result with fewer moving parts?

---

## Step 4: Produce Report

Write `docs/reports/optimization-report.md` using this EXACT structure.
Do not add or rename sections.

````markdown
# System Optimization Report

## Date: {FILL}
## Scope: {FILL: feature set analyzed}

## Summary
{FILL: 1-3 sentences — overall health + top priorities}

## Performance
- [{P1}] {file:function} — {issue} — {suggestion}
- [{P2}] ...
- Deep: {FILL: bottleneck analysis, 2-3 sentences max}

## User Experience
- [{UX1}] {file:component} — {issue} — {suggestion}
- Deep: {FILL: user flow findings, 2-3 sentences max}

## Code Quality
- [{CQ1}] {file:function} — {issue} — {suggestion}
- Deep: {FILL: maintainability concerns, 2-3 sentences max}

## Architecture
- [{AR1}] {file/module} — {issue} — {suggestion}
- Deep: {FILL: structural concerns, 2-3 sentences max}

## Recommended Priority
1. {ID} {one-line description}
2. {ID} {one-line description}
3. {ID} {one-line description}
````

---

## Step 5: Update Memory

Update `.claude/mem/memory.md` Current State:
- Note that system feedback review is complete
- Reference the report location

Commit:
```
[feedback]: system optimization report for [feature set]
```

---

## Rules

1. Every issue must reference a specific file (and function/line when applicable)
2. Every issue must have a concrete suggestion, not just "improve this"
3. Do not recommend changes that would break existing tests
4. Do not recommend changes outside the scope of the current feature set
5. The report is advisory — it does not trigger automatic changes
6. Keep the report actionable: if an issue takes more than 2 sentences to
   explain, it needs to be broken into smaller issues
