#!/usr/bin/env python3
"""Lint sp-harness skill SKILL.md files for user-facing output rules.

Scope: scans content inside ```output-template fenced blocks only. Other
prose, internal vocabulary, and flow instructions are ignored.

Rules:
  R1  Static codename in fence block must have inline `(<gloss>)`.
      Pattern: D1, F2, S3, "Phase 3", "Round 2", "Mode A", "Mode B".
      A codename is "covered" if `(...)` follows on the same line within
      8 chars or wraps it.
  R2  Id placeholder `<…-id>` (kebab-case ending in `-id`) must include
      `|format` modifier — `<feature-id|format>` — signalling the
      format_id() runtime renderer.
  R3  Quality heuristic, warn only, exit still 0:
        · snake_case or kebab-case multi-word tokens
        · ≥ 2 consecutive Title Case words
        · sp-harness denylist (Phase, Round, Mode A/B, F1-F9, plan.yaml,
          feature-id) when used outside its own gloss role
        · gloss clause length > 80 chars
      Inline disable: prepend `<!-- lint:disable=R3 -->` on the line above.
  R4  Section headers inside fence blocks must use `**Label**` style,
      not bare `Label:` followed by indented body. Detection: line
      matches `^\\s*[A-Z][a-zA-Z]*(\\s+[A-Za-z]+)*:\\s*$`. Inline
      disable: `<!-- lint:disable=R4 -->` on the line above.
  R5  Project-internal short codes inside fence blocks must have inline
      `(<gloss>)`. Patterns: `Track [A-Z]`, `Tier \\d+`, multi-segment
      `F\\d+\\+F\\d+(...)+`, `v\\d+\\.\\d+\\.\\d+` used as a label.
      Same 8-char-look-ahead rule as R1. Inline disable:
      `<!-- lint:disable=R5 -->` on the line above.
  R6  Fancy/curly quotes (U+201C, U+201D, U+2018, U+2019) inside fence
      blocks. ASCII `"` and `'` only. macOS smart-quote autocorrect leak
      guard. Inline disable: `<!-- lint:disable=R6 -->` on the line above.
  R7  Self-check block presence: every ``output-template`` fence MUST
      be preceded (within 30 lines before the opener) OR followed
      (within 30 lines after the closer) by one of the canonical
      self-check markers — `Self-check before print:`,
      `Output prose self-check`, or `specific-pattern self-check`.
      Catches the case where a new emit point ships without the
      self-check boilerplate. Inline disable: `<!-- lint:disable=R7 -->`
      on the line immediately above the fence opener.

Schema check (always runs unless --no-schema-check):
  Every entry in .claude/features.json and .claude/todos.json must have
  a non-empty `display_name`. Backfilled by F1; lint guards regression.

Exit codes:
  0  no R1/R2/schema failures (R3 warnings are non-failing)
  1  one or more R1/R2/schema failures
  2  internal error (file unreadable, JSON malformed, etc.)

CLI:
  --paths PATH [PATH ...]   limit scan to listed files (default: all skills/*/SKILL.md)
  --check                   machine-readable summary only
  --quiet                   suppress per-file PASS lines (still print FAIL/WARN)
  --no-schema-check         skip features.json/todos.json validation
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Fenced block extraction
# ---------------------------------------------------------------------------

_FENCE_OPEN_RE = re.compile(r"^(\s*)```output-template\s*$")
_FENCE_CLOSE_RE = re.compile(r"^(\s*)```\s*$")


@dataclass
class Block:
    file: Path
    start_line: int  # 1-based, line of opening fence
    end_line: int    # 1-based, line of closing fence
    indent: str
    lines: list[str] = field(default_factory=list)  # body lines, raw


def extract_blocks(file: Path) -> list[Block]:
    text = file.read_text(encoding="utf-8")
    raw = text.splitlines()
    blocks: list[Block] = []
    i = 0
    while i < len(raw):
        line = raw[i]
        m_open = _FENCE_OPEN_RE.match(line)
        if not m_open:
            i += 1
            continue
        indent = m_open.group(1)
        start = i
        body: list[str] = []
        i += 1
        while i < len(raw):
            close = _FENCE_CLOSE_RE.match(raw[i])
            # Close fence must match indent level of opener for nested-aware parsing
            if close and close.group(1) == indent:
                blocks.append(Block(file, start + 1, i + 1, indent, body))
                i += 1
                break
            body.append(raw[i])
            i += 1
        else:
            # EOF without closing fence — treat as block extending to EOF
            blocks.append(Block(file, start + 1, len(raw), indent, body))
    return blocks


# ---------------------------------------------------------------------------
# Rule R1: codename needs gloss
# ---------------------------------------------------------------------------

# Matches static codenames as standalone tokens. R\d+ is excluded because
# "R1/R2/R3" are the lint rule names themselves and would false-positive on
# any SKILL.md or doc that mentions them; "Round N" is matched explicitly.
_CODENAME_RE = re.compile(
    r"\b("
    r"[DFS]\d+"                # D1, F2, S3
    r"|Phase\s+\d+"
    r"|Round\s+\d+"
    r"|Mode\s+[AB]"
    r")\b"
)

# After a codename, look for `(...)` opening within 8 chars
_GLOSS_AFTER_RE = re.compile(r"^\s{0,8}\(")


def _line_has_disable(prev_line: str | None, rule: str) -> bool:
    if not prev_line:
        return False
    return f"lint:disable={rule}" in prev_line


def check_r1(block: Block) -> list[str]:
    """Return list of failure messages (one per offending line)."""
    fails: list[str] = []
    for offset, line in enumerate(block.lines):
        for m in _CODENAME_RE.finditer(line):
            tail = line[m.end():]
            if _GLOSS_AFTER_RE.match(tail):
                continue
            line_no = block.start_line + 1 + offset
            fails.append(
                f"{block.file}:{line_no}: [R1] codename "
                f"{m.group(0)!r} needs inline gloss '(...)'"
            )
    return fails


# ---------------------------------------------------------------------------
# Rule R2: id placeholder needs |format
# ---------------------------------------------------------------------------

# `<…-id>` style placeholder. Hyphens in the body, ends with `-id` (or
# `-id|format`), bracket-bounded.
_ID_PLACEHOLDER_RE = re.compile(r"<([a-z][a-z0-9-]*-id)([^>]*)>")


def check_r2(block: Block) -> list[str]:
    fails: list[str] = []
    for offset, line in enumerate(block.lines):
        for m in _ID_PLACEHOLDER_RE.finditer(line):
            modifier = m.group(2)
            if modifier.strip() == "|format":
                continue
            line_no = block.start_line + 1 + offset
            fails.append(
                f"{block.file}:{line_no}: [R2] id placeholder "
                f"<{m.group(1)}{modifier}> must use '<{m.group(1)}|format>'"
            )
    return fails


# ---------------------------------------------------------------------------
# Rule R3: quality heuristic (warn only)
# ---------------------------------------------------------------------------

_GLOSS_RE = re.compile(r"\(([^()]{1,200})\)")
_PLACEHOLDER_RE = re.compile(r"<[^<>]{1,200}>")
# Codename-followed-by-gloss patterns that legitimately use a denylist
# token in the codename position. These are stripped before denylist
# scanning so we don't false-positive on `Phase 3(架构...) 已完成`.
_CODENAME_WITH_GLOSS_RE = re.compile(
    r"\b(Phase\s+\d+|Round\s+\d+|Mode\s+[AB]|[DFS]\d+)\s*\([^()]{1,200}\)"
)
_SNAKE_KEBAB_RE = re.compile(r"\b[a-z][a-z0-9]*[_-][a-z0-9_-]*[a-z0-9]\b")
_TITLE_PAIR_RE = re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b")
_DENYLIST = (
    re.compile(r"\bPhase\b"),
    re.compile(r"\bRound\b"),
    re.compile(r"\bMode\s+[AB]\b"),
    re.compile(r"\bF[1-9]\b"),
    re.compile(r"\bplan\.yaml\b"),
    re.compile(r"\bfeature-id\b"),
)
_GLOSS_LEN_THRESHOLD = 80


def check_r3(block: Block) -> list[str]:
    """Return list of warning messages (R3 warnings — non-failing)."""
    warns: list[str] = []
    for offset, line in enumerate(block.lines):
        prev = block.lines[offset - 1] if offset > 0 else None
        if _line_has_disable(prev, "R3"):
            continue
        line_no = block.start_line + 1 + offset
        for gloss_match in _GLOSS_RE.finditer(line):
            text = gloss_match.group(1)
            if len(text) > _GLOSS_LEN_THRESHOLD:
                warns.append(
                    f"{block.file}:{line_no}: [R3] gloss clause "
                    f"is {len(text)} chars (>80)"
                )
            sk = _SNAKE_KEBAB_RE.search(text)
            if sk:
                warns.append(
                    f"{block.file}:{line_no}: [R3] gloss contains "
                    f"snake_case/kebab-case token {sk.group(0)!r}"
                )
            tp = _TITLE_PAIR_RE.search(text)
            if tp:
                warns.append(
                    f"{block.file}:{line_no}: [R3] gloss has "
                    f"consecutive Title Case words {tp.group(0)!r}"
                )
        # Denylist scan: strip codename-with-gloss (legitimate role),
        # placeholders <...>, and remaining glosses, then check what's left.
        line_for_scan = _CODENAME_WITH_GLOSS_RE.sub("", line)
        line_for_scan = _PLACEHOLDER_RE.sub("", line_for_scan)
        line_for_scan = _GLOSS_RE.sub("", line_for_scan)
        for pat in _DENYLIST:
            m = pat.search(line_for_scan)
            if m:
                warns.append(
                    f"{block.file}:{line_no}: [R3] denylist token "
                    f"{m.group(0)!r} used outside a gloss role"
                )
                break  # one denylist warning per line is enough
    return warns


# ---------------------------------------------------------------------------
# Rule R4: section header style
# ---------------------------------------------------------------------------

# Bare 'Title-case Words:' on its own line — needs '**Label**' wrapping.
# The wrapped form '**Problem**' does NOT match this regex (no colon)
# so passes trivially. The disable comment escape hatch is honored via
# the existing `lint:disable=R4` mechanism.
_BARE_LABEL_RE = re.compile(
    r"^\s*[A-Z][a-zA-Z]*(\s+[A-Za-z]+)*:\s*$"
)


def check_r4(block: Block) -> list[str]:
    fails: list[str] = []
    for offset, line in enumerate(block.lines):
        if not _BARE_LABEL_RE.match(line):
            continue
        prev = block.lines[offset - 1] if offset > 0 else None
        if _line_has_disable(prev, "R4"):
            continue
        line_no = block.start_line + 1 + offset
        label = line.strip().rstrip(":").strip()
        fails.append(
            f"{block.file}:{line_no}: [R4] section header "
            f"{label!r} uses bare 'Label:'; use '**{label}**' form"
        )
    return fails


# ---------------------------------------------------------------------------
# Rule R5: project-internal short-code gloss
# ---------------------------------------------------------------------------

# Project-internal short codes that need an inline gloss when they
# appear inside an output-template fence.
_SHORTCODE_RE = re.compile(
    r"\b("
    r"Track\s+[A-Z]"
    r"|Tier\s+\d+"
    r"|F\d+(?:\+F\d+)+"        # multi-segment cluster label, e.g. F3+F4+F5
    r"|v\d+\.\d+\.\d+"
    r")\b"
)


def check_r5(block: Block) -> list[str]:
    fails: list[str] = []
    for offset, line in enumerate(block.lines):
        prev = block.lines[offset - 1] if offset > 0 else None
        if _line_has_disable(prev, "R5"):
            continue
        for m in _SHORTCODE_RE.finditer(line):
            tail = line[m.end():]
            if _GLOSS_AFTER_RE.match(tail):
                continue
            line_no = block.start_line + 1 + offset
            fails.append(
                f"{block.file}:{line_no}: [R5] short code "
                f"{m.group(0)!r} needs inline gloss '(...)'"
            )
    return fails


# ---------------------------------------------------------------------------
# Rule R6: fancy/curly quotes
# ---------------------------------------------------------------------------

# U+201C LEFT DOUBLE QUOTATION MARK
# U+201D RIGHT DOUBLE QUOTATION MARK
# U+2018 LEFT SINGLE QUOTATION MARK
# U+2019 RIGHT SINGLE QUOTATION MARK
_FANCY_QUOTE_RE = re.compile(r"[‘’“”]")


def check_r6(block: Block) -> list[str]:
    """Flag fancy/curly quotes inside fence blocks."""
    fails: list[str] = []
    for offset, line in enumerate(block.lines):
        prev = block.lines[offset - 1] if offset > 0 else None
        if _line_has_disable(prev, "R6"):
            continue
        for m in _FANCY_QUOTE_RE.finditer(line):
            line_no = block.start_line + 1 + offset
            ch = m.group(0)
            fails.append(
                f"{block.file}:{line_no}: [R6] fancy/curly quote "
                f"{ch!r} (U+{ord(ch):04X}) — use ASCII \" or '"
            )
    return fails


# ---------------------------------------------------------------------------
# Rule R7: self-check block presence
# ---------------------------------------------------------------------------

# Markers that satisfy R7. Any one of these phrases in the search
# window counts as a self-check block.
_R7_SELF_CHECK_MARKERS = (
    "Self-check before print:",
    "Output prose self-check",
    "specific-pattern self-check",
)
_R7_WINDOW = 30  # lines before opener / after closer


def check_r7(block: Block, file_lines: list[str]) -> list[str]:
    """Each output-template fence must be preceded or followed by a
    self-check marker within the configured window. The pre-fence
    pattern is the legacy form; the post-fence pattern (with explicit
    'rewrite before emitting' language) was introduced in v0.8.23.
    Both satisfy this guard.
    """
    fails: list[str] = []
    # Honor lint:disable=R7 on the line immediately above the opener
    above_idx = block.start_line - 2  # 0-based index for line above opener
    if above_idx >= 0 and "lint:disable=R7" in file_lines[above_idx]:
        return fails
    before_start = max(0, block.start_line - 1 - _R7_WINDOW)
    before_end = block.start_line - 1
    after_start = block.end_line  # 1-based end_line == closer; index after closer = end_line
    after_end = min(len(file_lines), block.end_line + _R7_WINDOW)
    text = "\n".join(
        file_lines[before_start:before_end] + file_lines[after_start:after_end]
    )
    if not any(marker in text for marker in _R7_SELF_CHECK_MARKERS):
        fails.append(
            f"{block.file}:{block.start_line}: [R7] output-template fence "
            f"missing self-check block within {_R7_WINDOW} lines "
            f"(before opener or after closer)"
        )
    return fails


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def check_schema(repo_root: Path) -> list[str]:
    fails: list[str] = []
    for filename, list_key, kind in (
        ("features.json", "features", "feature"),
        ("todos.json", "todos", "todo"),
    ):
        path = repo_root / ".claude" / filename
        if not path.exists():
            # No data file is fine for users not yet using sp-harness state
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            fails.append(f"{path}: invalid JSON ({e})")
            continue
        for entry in data.get(list_key, []):
            name = entry.get("display_name")
            if not isinstance(name, str) or not name.strip():
                fails.append(
                    f"{path}: {kind} {entry.get('id', '<no-id>')!r} "
                    f"has empty or missing display_name"
                )
    return fails


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def default_skill_files(repo_root: Path) -> list[Path]:
    """Default scope: all skill files PLUS agent-template files.

    The agent-templates/ directory holds project-level subagent
    definitions (sp-planner, sp-evaluator, sp-feedback, sp-generator)
    whose terminal-output blocks are user-facing briefs. They share
    the same lint discipline as skills/*/SKILL.md.
    """
    return sorted(
        list((repo_root / "skills").glob("*/SKILL.md"))
        + list((repo_root / "agent-templates").glob("*.md"))
    )


def lint_files(
    files: Iterable[Path],
    quiet: bool,
    check: bool,
) -> tuple[list[str], list[str]]:
    all_fails: list[str] = []
    all_warns: list[str] = []
    for file in files:
        blocks = extract_blocks(file)
        file_lines = file.read_text(encoding="utf-8").splitlines()
        file_fails: list[str] = []
        file_warns: list[str] = []
        for block in blocks:
            file_fails.extend(check_r1(block))
            file_fails.extend(check_r2(block))
            file_warns.extend(check_r3(block))
            file_fails.extend(check_r4(block))
            file_fails.extend(check_r5(block))
            file_fails.extend(check_r6(block))
            file_fails.extend(check_r7(block, file_lines))
        if not check and not quiet and not file_fails and not file_warns:
            print(f"PASS {file}")
        all_fails.extend(file_fails)
        all_warns.extend(file_warns)
    return all_fails, all_warns


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--paths", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--no-schema-check", action="store_true")
    args = parser.parse_args()

    files = args.paths or default_skill_files(REPO_ROOT)
    files = [f for f in files if f.exists() and f.suffix == ".md"]

    try:
        fails, warns = lint_files(files, args.quiet, args.check)
    except Exception as e:  # noqa: BLE001
        print(f"error: lint engine crashed: {e}", file=sys.stderr)
        return 2

    schema_fails: list[str] = []
    if not args.no_schema_check:
        schema_fails = check_schema(REPO_ROOT)
        fails.extend(schema_fails)

    if args.check:
        print(json.dumps({
            "errors": len(fails),
            "warnings": len(warns),
            "files_scanned": len(files),
        }))
    else:
        for w in warns:
            print(f"WARN {w}", file=sys.stderr)
        for f in fails:
            print(f"FAIL {f}", file=sys.stderr)
        if not fails:
            if not args.quiet:
                print(
                    f"OK — {len(files)} files scanned, "
                    f"{len(warns)} warnings, 0 failures"
                )

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
