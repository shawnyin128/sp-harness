#!/usr/bin/env python3
"""
Tally skill-routing audit results.

Reads run-level JSON from stdin in the schema produced by audit.sh:
  {"scenarios": [{"id": str, "expected": str, "votes": [{"output": str, "exit_code": int}, ...]}, ...]}

For each scenario, extracts the `primary_skill` from the first fenced ```json
block in each vote's output, tallies votes matching `expected`, and classifies
a verdict per the MVP spec:

  PASS       — 3 of 3 votes == expected
  PASS-WEAK  — 2 of 3 votes == expected
  FAIL       — 1 of 3 votes == expected
  FAIL       — 0 of 3 votes == expected AND votes are consensus on a wrong skill
                  OR 0 of 3 votes are parseable (all unparseable)
  FLAKY      — 0 of 3 votes == expected AND parseable votes disagree with each other

Exit 0 iff no FAIL and no FLAKY.
"""

import json
import re
import sys
from collections import Counter

JSON_BLOCK_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


def extract_skill(vote_output: str) -> str:
    """Return primary_skill, or the literal 'unparseable' if extraction fails."""
    if not vote_output:
        return "unparseable"
    m = JSON_BLOCK_RE.search(vote_output)
    if not m:
        return "unparseable"
    try:
        obj = json.loads(m.group(1))
    except json.JSONDecodeError:
        return "unparseable"
    skill = obj.get("primary_skill")
    if not isinstance(skill, str) or not skill.strip():
        return "unparseable"
    return skill.strip()


def classify(votes: list[str], expected: str) -> str:
    count_expected = sum(1 for v in votes if v == expected)
    distinct_valid = {v for v in votes if v != "unparseable"}
    if count_expected == 3:
        return "PASS"
    if count_expected == 2:
        return "PASS-WEAK"
    if count_expected == 1:
        return "FAIL"
    # count_expected == 0
    if len(distinct_valid) >= 2:
        return "FLAKY"
    return "FAIL"


def format_votes(votes: list[str]) -> str:
    """Compact: 'brainstorming ×2, none ×1' style."""
    counts = Counter(votes)
    parts = [f"{k} ×{v}" for k, v in counts.most_common()]
    return ", ".join(parts)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        sys.stderr.write(f"tally.py: invalid results JSON on stdin: {e}\n")
        return 2

    scenarios = data.get("scenarios", [])
    if not scenarios:
        print("No scenarios to tally.")
        return 0

    rows = []
    summary = Counter()
    for s in scenarios:
        sid = s["id"]
        expected = s["expected"]
        votes = [extract_skill(v.get("output", "")) for v in s["votes"]]
        verdict = classify(votes, expected)
        rows.append((sid, expected, format_votes(votes), verdict))
        summary[verdict] += 1

    # Compute column widths from the data (with sane minimums).
    col_id = max(len("Scenario"), *(len(r[0]) for r in rows))
    col_exp = max(len("Expected"), *(len(r[1]) for r in rows))
    col_got = max(len("Got"), *(len(r[2]) for r in rows))
    col_ver = max(len("Verdict"), *(len(r[3]) for r in rows))

    from datetime import datetime
    print(f"Skill Routing Audit — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Corpus: {len(scenarios)} scenarios\n")

    header = f"{'Scenario':<{col_id}}  {'Expected':<{col_exp}}  {'Got':<{col_got}}  {'Verdict':<{col_ver}}"
    print(header)
    print("─" * len(header))
    for sid, expected, got, verdict in rows:
        print(f"{sid:<{col_id}}  {expected:<{col_exp}}  {got:<{col_got}}  {verdict:<{col_ver}}")

    print()
    parts = []
    for v in ("PASS", "PASS-WEAK", "FAIL", "FLAKY"):
        parts.append(f"{summary.get(v, 0)} {v}")
    print("Summary: " + " · ".join(parts))

    return 0 if summary.get("FAIL", 0) == 0 and summary.get("FLAKY", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
