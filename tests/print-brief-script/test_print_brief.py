"""Snapshot tests for skills/feature-tracker/scripts/print-brief.py.

Each fixture pairs a plan YAML with an expected stdout. Failure mode shows
exactly what about the brief format moved.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "skills" / "feature-tracker" / "scripts" / "print-brief.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
EXPECTED = Path(__file__).resolve().parent / "expected"


def run_script(plan_file: Path, display_name: str = "Sample Feature",
               commit: str = "deadbeef") -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "sample-feature",
            "--plan-file",
            str(plan_file),
            "--display-name",
            display_name,
            "--commit",
            commit,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    "fixture_name",
    [
        "full-pass",
        "missing-optimization",
        "multi-round",
        "wrapped-scalars",
        "colon-in-prose",
    ],
)
def test_brief_snapshot(fixture_name: str) -> None:
    plan = FIXTURES / f"{fixture_name}.plan.yaml"
    expected = EXPECTED / f"{fixture_name}.txt"
    result = run_script(plan)
    assert result.returncode == 0, (
        f"script exited {result.returncode}; stderr:\n{result.stderr}"
    )
    assert result.stdout == expected.read_text(), (
        f"snapshot mismatch for {fixture_name}\n"
        f"--- expected ---\n{expected.read_text()}"
        f"--- actual ---\n{result.stdout}"
    )


def test_missing_archive_fails_clearly(tmp_path: Path) -> None:
    """Auto-derived archive path that does not exist must produce a non-zero
    exit and a stderr message naming the missing file. Use a tmp_path-rooted
    --plan-file pointing at a non-existent file to simulate."""
    bogus = tmp_path / "does-not-exist.plan.yaml"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "missing-feature",
            "--plan-file",
            str(bogus),
            "--display-name",
            "Missing",
            "--commit",
            "deadbeef",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert str(bogus) in result.stderr or "not found" in result.stderr.lower()
