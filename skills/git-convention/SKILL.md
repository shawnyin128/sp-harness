---
name: git-convention
description: |
  Enforce [module]: description commit format before every git commit.
  Module = top-level directory name of primary change area.
author: sp-harness
version: 1.1.0
---

# git-convention

Invoke before every `git commit`.

## Format

```
[module]: what changed and why
```

- **module**: top-level directory of primary change (e.g., `skills`, `hooks`, `docs`, `tests`). If commit spans multiple, use the primary one. Tie-breaker: use the one with most lines changed.
- **description**: one line, under 72 chars. Must be meaningful in `git log --oneline`.
- **trivial commits** (typo, formatting): still use `[module]:` but reason can be omitted.

## Examples

```
[skills]: add init-project for lean CLAUDE.md bootstrap
[hooks]: fix session-start variable naming for sp-harness
[docs]: update README install instructions
```

Bad:
```
update files                    ← no module, no info
[misc]: various changes         ← says nothing
[skills]: update skills         ← redundant
```

## Why

New sessions read `git log --oneline -20` for context recovery. Structured messages make this reliable.
