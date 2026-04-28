#!/usr/bin/env python3
"""Lint sp-harness skill SKILL.md files for procedural-section fixtures.

Scope: scans pairs of ```procedural-instruction and ```worked-example
fenced blocks. Other prose, internal vocabulary, and content inside
```output-template fences (covered by lint-skill-output.py) are ignored.

Rules:
  P1  Pairing — every ```procedural-instruction fence must be immediately
      followed by a ```worked-example fence. Only blank lines may appear
      between them. A ```worked-example fence not preceded by a
      ```procedural-instruction is also a P1 failure.
  P2  Minimum body — the body of each ```worked-example fence must
      contain at least 100 whitespace-separated words. Empty lines and
      the fence markers themselves do not count.
  P3  Observation list — the body of each ```worked-example fence must
      contain at least one ordered list with three or more numbered
      items (lines matching ``^\\s*\\d+\\.\\s+``).

Exit codes:
  0  no P1/P2/P3 failures
  1  one or more P1/P2/P3 failures
  2  internal error (file unreadable, etc.)

CLI:
  --paths PATH [PATH ...]   limit scan to listed files (default: all skills/*/SKILL.md)
  --check                   machine-readable summary only
  --quiet                   suppress per-file PASS lines (still print FAIL)
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

PROCEDURAL = "procedural-instruction"
WORKED_EXAMPLE = "worked-example"

_FENCE_OPEN_RE = re.compile(
    r"^(\s*)```(" + PROCEDURAL + r"|" + WORKED_EXAMPLE + r")\s*$"
)
_FENCE_CLOSE_RE = re.compile(r"^(\s*)```\s*$")


@dataclass
class Block:
    file: Path
    kind: str            # 'procedural-instruction' | 'worked-example'
    start_line: int      # 1-based, line of opening fence
    end_line: int        # 1-based, line of closing fence (or EOF)
    indent: str
    lines: list[str] = field(default_factory=list)  # body lines, raw


def extract_blocks(file: Path) -> list[Block]:
    text = file.read_text(encoding="utf-8")
    raw = text.splitlines()
    blocks: list[Block] = []
    i = 0
    while i < len(raw):
        m_open = _FENCE_OPEN_RE.match(raw[i])
        if not m_open:
            i += 1
            continue
        indent = m_open.group(1)
        kind = m_open.group(2)
        start = i
        body: list[str] = []
        i += 1
        while i < len(raw):
            close = _FENCE_CLOSE_RE.match(raw[i])
            if close and close.group(1) == indent:
                blocks.append(Block(file, kind, start + 1, i + 1, indent, body))
                i += 1
                break
            body.append(raw[i])
            i += 1
        else:
            blocks.append(Block(file, kind, start + 1, len(raw), indent, body))
    return blocks


# ---------------------------------------------------------------------------
# Rule P1: pairing
# ---------------------------------------------------------------------------

def _is_blank(line: str) -> bool:
    return not line.strip()


def check_p1(file: Path, blocks: list[Block], raw: list[str]) -> list[str]:
    """Walk blocks in document order; enforce pairing rules.

    Reports:
      · procedural-instruction not followed by worked-example
      · prose (non-blank line) between procedural-instruction and worked-example
      · worked-example not preceded by procedural-instruction
    """
    fails: list[str] = []
    last_proc: Block | None = None
    for block in blocks:
        if block.kind == PROCEDURAL:
            if last_proc is not None:
                fails.append(
                    f"{file}:{last_proc.start_line}: [P1] "
                    f"procedural-instruction not followed by worked-example "
                    f"(another procedural-instruction at L{block.start_line})"
                )
            last_proc = block
            continue
        # block.kind == worked-example
        if last_proc is None:
            fails.append(
                f"{file}:{block.start_line}: [P1] "
                f"worked-example not preceded by a procedural-instruction"
            )
            continue
        # Verify nothing but blank lines between last_proc.end_line and
        # block.start_line. Lines are 1-based; raw is 0-based.
        between = raw[last_proc.end_line:block.start_line - 1]
        if any(not _is_blank(line) for line in between):
            fails.append(
                f"{file}:{last_proc.start_line}: [P1] "
                f"prose between procedural-instruction and "
                f"worked-example (worked-example at L{block.start_line})"
            )
        last_proc = None  # consumed
    if last_proc is not None:
        fails.append(
            f"{file}:{last_proc.start_line}: [P1] "
            f"procedural-instruction not followed by worked-example "
            f"(no worked-example until EOF)"
        )
    return fails


# ---------------------------------------------------------------------------
# Rule P2: minimum body
# ---------------------------------------------------------------------------

P2_MIN_WORDS = 100


def _count_words(lines: list[str]) -> int:
    return sum(len(line.split()) for line in lines)


def check_p2(block: Block) -> list[str]:
    if block.kind != WORKED_EXAMPLE:
        return []
    n = _count_words(block.lines)
    if n >= P2_MIN_WORDS:
        return []
    return [
        f"{block.file}:{block.start_line}: [P2] worked-example body "
        f"has {n} words; >= {P2_MIN_WORDS} required"
    ]


# ---------------------------------------------------------------------------
# Rule P3: observation list
# ---------------------------------------------------------------------------

P3_MIN_ITEMS = 3
_ORDERED_ITEM_RE = re.compile(r"^\s*\d+\.\s+\S")


def _max_consecutive_ordered_items(lines: list[str]) -> int:
    best = 0
    run = 0
    for line in lines:
        if _ORDERED_ITEM_RE.match(line):
            run += 1
            best = max(best, run)
        else:
            # Continuation lines (indented but not a list item) preserve the run.
            # An empty line breaks the run.
            if not line.strip():
                run = 0
    return best


def check_p3(block: Block) -> list[str]:
    if block.kind != WORKED_EXAMPLE:
        return []
    if _max_consecutive_ordered_items(block.lines) >= P3_MIN_ITEMS:
        return []
    return [
        f"{block.file}:{block.start_line}: [P3] worked-example body "
        f"missing numbered observation list (>= {P3_MIN_ITEMS} items required)"
    ]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def default_skill_files(repo_root: Path) -> list[Path]:
    return sorted((repo_root / "skills").glob("*/SKILL.md"))


def lint_files(
    files: Iterable[Path],
    quiet: bool,
    check: bool,
) -> list[str]:
    all_fails: list[str] = []
    for file in files:
        text = file.read_text(encoding="utf-8")
        raw = text.splitlines()
        blocks = extract_blocks(file)
        file_fails: list[str] = []
        file_fails.extend(check_p1(file, blocks, raw))
        for block in blocks:
            file_fails.extend(check_p2(block))
            file_fails.extend(check_p3(block))
        if not check and not quiet and not file_fails:
            print(f"PASS {file}")
        all_fails.extend(file_fails)
    return all_fails


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--paths", nargs="+", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    if args.paths:
        files = args.paths
        for f in files:
            if not f.exists():
                print(f"error: file not found: {f}", file=sys.stderr)
                return 2
    else:
        files = default_skill_files(REPO_ROOT)
    files = [f for f in files if f.suffix == ".md"]

    try:
        fails = lint_files(files, args.quiet, args.check)
    except Exception as e:  # noqa: BLE001
        print(f"error: lint engine crashed: {e}", file=sys.stderr)
        return 2

    if args.check:
        print(json.dumps({
            "errors": len(fails),
            "files_scanned": len(files),
        }))
    else:
        for f in fails:
            print(f"FAIL {f}", file=sys.stderr)
        if not fails and not args.quiet:
            print(
                f"OK — {len(files)} files scanned, 0 failures"
            )

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
