#!/usr/bin/env python3
"""Backfill display_name on existing .claude/features.json entries.

Usage:
  backfill_display_names.py [path-to-features.json]

Defaults to .claude/features.json in the current working directory.
Idempotent — entries that already have a non-empty display_name are left
untouched. Prints a summary and exits 0 on success.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from display_name import derive_display_name

DEFAULT_PATH = Path(".claude/features.json")


def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else DEFAULT_PATH
    if not target.exists():
        print(f"error: {target} does not exist", file=sys.stderr)
        return 1

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"error: {target} is not valid JSON: {e}", file=sys.stderr)
        return 1

    entries = data.get("features", [])
    filled = 0
    skipped = 0
    for entry in entries:
        if entry.get("display_name"):
            skipped += 1
            continue
        entry["display_name"] = derive_display_name(entry.get("description", ""))
        filled += 1

    target.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"backfill complete: {filled} filled, {skipped} already had display_name")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
