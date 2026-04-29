"""Regression guards for the emit-time discipline rules.

Scope: the three skills whose user-facing emit points are subject to
the 6-item self-check pattern established in v0.8.23 + extended by
this feature:

  - skills/single-agent-development/SKILL.md  (Plan summary fence)
  - skills/sp-planner-role/SKILL.md            (Plan summary fence)
  - skills/sp-evaluator-role/SKILL.md          (verdict fences)

Other skills with output-template fences (code-hygiene status reports,
feature-tracker progress prints, feedback Mode-A summaries, etc.) have
their own emit shapes and existing self-check patterns; broader
migration is tracked separately.

This test fails when:
  (a) any output-template fence in the in-scope skills lacks a
      self-check marker within 30 lines above it; or
  (b) any in-scope skill reintroduces a global terminal-output line cap
      (the obsolete '≤ 35 lines' / 'under 30 lines' phrases).
Cap detection ignores file-size limits ("CLAUDE.md under 80 lines",
"memory.md under 30 lines") and per-element constraints inside fences
("≤ 5 lines per Closure block"), since those are not global emit caps.
"""
from __future__ import annotations

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

IN_SCOPE_SKILLS = (
    "skills/single-agent-development/SKILL.md",
    "skills/sp-planner-role/SKILL.md",
    "skills/sp-evaluator-role/SKILL.md",
)

FENCE_OPEN_RE = re.compile(r"^(\s*)```output-template\s*$")
FENCE_CLOSE_RE = re.compile(r"^(\s*)```\s*$")
SELF_CHECK_MARKERS = (
    "Self-check before print:",
    "Output prose self-check",
    "specific-pattern self-check",
)
GLOBAL_CAP_PATTERNS = (
    re.compile(r"≤\s*\d+\s*lines"),
    re.compile(r"under\s+\d+\s+lines"),
)
# Phrases adjacent to a cap that mark it as a non-emit constraint.
NON_EMIT_CAP_HINTS = (
    ".md",          # file size limit (CLAUDE.md, memory.md, etc.)
    "options",      # multi-choice limit
    "chars",        # length limit on a string
    "words",        # word count limit on a label
    "items",        # list-size limit
    "block",        # per-section limit, not whole emit
    " per ",        # "≤ N per <element>"
)


def find_fence_pairs(text: str) -> list[tuple[int, int]]:
    """Return list of (opener_line_no, closer_line_no), 1-based.
    For an unclosed fence, the closer is the last line of the file."""
    lines = text.splitlines()
    pairs: list[tuple[int, int]] = []
    i = 0
    while i < len(lines):
        m = FENCE_OPEN_RE.match(lines[i])
        if not m:
            i += 1
            continue
        indent = m.group(1)
        opener = i + 1
        j = i + 1
        while j < len(lines):
            close = FENCE_CLOSE_RE.match(lines[j])
            if close and close.group(1) == indent:
                break
            j += 1
        closer = j + 1 if j < len(lines) else len(lines)
        pairs.append((opener, closer))
        i = j + 1
    return pairs


def find_fence_open_line_numbers(text: str) -> list[int]:
    return [opener for opener, _ in find_fence_pairs(text)]


def line_is_inside_a_fence(lines: list[str], line_no: int) -> bool:
    """Return True if 1-based line_no falls between an output-template
    fence opener and its matching closer."""
    inside = False
    indent: str | None = None
    for i, line in enumerate(lines, start=1):
        if not inside:
            m = FENCE_OPEN_RE.match(line)
            if m:
                inside = True
                indent = m.group(1)
                if i == line_no:
                    return True
                continue
        else:
            close = FENCE_CLOSE_RE.match(line)
            if close and close.group(1) == indent:
                inside = False
                indent = None
                if i == line_no:
                    return True
                continue
            if i == line_no:
                return True
    return False


def has_self_check_marker_within(lines: list[str], opener: int, closer: int, window: int = 30) -> bool:
    """Search `window` lines BEFORE the fence opener OR `window` lines
    AFTER the fence closer for any self-check marker. The v0.8.23
    pattern places the checklist after the fence with explicit
    'rewrite before emitting' language; pre-fence checklists are also
    valid. Both patterns satisfy this guard."""
    before_start = max(0, opener - 1 - window)
    before_end = opener - 1
    after_start = closer
    after_end = min(len(lines), closer + window)
    block = "\n".join(lines[before_start:before_end] + lines[after_start:after_end])
    return any(marker in block for marker in SELF_CHECK_MARKERS)


class TestSelfCheckPrecedesInScopeFences(unittest.TestCase):
    def test_every_in_scope_fence_has_self_check_block_within_30_lines(self):
        offenders: list[str] = []
        for rel in IN_SCOPE_SKILLS:
            path = REPO_ROOT / rel
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            for opener, closer in find_fence_pairs(text):
                if not has_self_check_marker_within(lines, opener, closer):
                    offenders.append(f"{rel}:{opener}")
        self.assertEqual(
            offenders,
            [],
            "output-template fences in emit-discipline-critical skills "
            "without a self-check block within 30 lines of the fence:\n  "
            + "\n  ".join(offenders)
        )


class TestNoObsoleteGlobalCaps(unittest.TestCase):
    def test_in_scope_skills_have_no_global_emit_caps(self):
        offenders: list[str] = []
        for rel in IN_SCOPE_SKILLS:
            path = REPO_ROOT / rel
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            for line_no, line in enumerate(lines, start=1):
                lower = line.lower()
                if any(hint in lower for hint in NON_EMIT_CAP_HINTS):
                    continue
                if line_is_inside_a_fence(lines, line_no):
                    continue
                for pattern in GLOBAL_CAP_PATTERNS:
                    m = pattern.search(line)
                    if m:
                        offenders.append(
                            f"{rel}:{line_no}: matched obsolete cap "
                            f"phrase {m.group(0)!r}"
                        )
                        break
        self.assertEqual(
            offenders,
            [],
            "obsolete global emit-cap phrases detected (must be replaced "
            "with 'structure decides shape, self-check decides "
            "density'):\n  " + "\n  ".join(offenders)
        )


class TestUsingSpHarnessHasLanguagePinScan(unittest.TestCase):
    def test_output_prose_self_check_includes_language_pin_item(self):
        path = REPO_ROOT / "skills" / "using-sp-harness" / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        m = re.search(
            r"## Output prose self-check.*?```procedural-instruction\n(.*?)\n```",
            text,
            re.DOTALL,
        )
        self.assertIsNotNone(m, "could not find Output prose self-check procedural block")
        block = m.group(1)
        self.assertRegex(
            block,
            r"[Ll]anguage[ -]pin",
            "Output prose self-check is missing a language-pin scan item",
        )


if __name__ == "__main__":
    unittest.main()
