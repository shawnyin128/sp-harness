"""Regression: skills/ tree has zero R5 violations.

R5 (project-internal short-code gloss) was added to lint-skill-output.py
in feature output-prose-lint-r4-r5. The live tree scan at that time
reported 0 R5 violations — fence-internal output didn't leak short
codes. This test locks the invariant: any future author who introduces
a fence-internal short code without inline gloss gets caught here.

Also includes a positive-control test that re-invokes the lint against
a known-bad fixture, so silent rule degradation (e.g., removing R5
from lint_files) does NOT silently let the live-tree test pass.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LINT = REPO_ROOT / "scripts" / "lint-skill-output.py"
NAKED_TRACK_FIXTURE = (
    REPO_ROOT
    / "tests"
    / "output-prose-lint-r4-r5"
    / "lint-fixtures"
    / "invalid_r5_naked_track.md"
)


def test_full_tree_zero_r5_violations() -> None:
    """The live skills/ tree must have zero R5 violations."""
    res = subprocess.run(
        [sys.executable, str(LINT), "--quiet", "--no-schema-check"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, (
        f"full skills/ tree fails lint-skill-output.py: {res.stderr}"
    )
    assert "[R5]" not in res.stderr, (
        f"unexpected [R5] markers in stderr: {res.stderr}"
    )


def test_full_tree_check_json_zero_errors() -> None:
    """JSON check mode reports 0 errors."""
    res = subprocess.run(
        [sys.executable, str(LINT), "--check", "--no-schema-check"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0
    payload = json.loads(res.stdout)
    assert payload["errors"] == 0, (
        f"errors > 0 unexpectedly: {payload}"
    )


def test_positive_control_naked_track_still_caught() -> None:
    """Sanity: lint still flags a known-bad fixture. If someone
    accidentally removes check_r5 from lint_files, the live-tree test
    above could still pass (since no fence currently uses short codes
    fenceside) — this control test fails loudly in that case."""
    res = subprocess.run(
        [
            sys.executable,
            str(LINT),
            "--no-schema-check",
            "--paths",
            str(NAKED_TRACK_FIXTURE),
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 1, (
        f"positive-control fixture should fail R5 but didn't: {res.stderr}"
    )
    assert "[R5]" in res.stderr, (
        f"positive-control fixture should emit [R5] marker: {res.stderr}"
    )
    assert "Track A" in res.stderr
