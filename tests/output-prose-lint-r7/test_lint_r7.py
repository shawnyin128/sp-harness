"""Tests for R7 (self-check block presence) in scripts/lint-skill-output.py."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LINT = REPO_ROOT / "scripts" / "lint-skill-output.py"
FIXTURES = pathlib.Path(__file__).resolve().parent / "lint-fixtures"


def fixture(name, *extra):
    return subprocess.run(
        [
            sys.executable,
            str(LINT),
            "--no-schema-check",
            "--paths",
            str(FIXTURES / name),
            *extra,
        ],
        capture_output=True,
        text=True,
    )


class TestR7SelfCheckPresence(unittest.TestCase):
    def test_self_check_above_passes(self):
        res = fixture("valid_r7_self_check_above.md")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("[R7]", res.stderr)

    def test_self_check_below_passes(self):
        res = fixture("valid_r7_self_check_below.md")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("[R7]", res.stderr)

    def test_no_self_check_fails(self):
        res = fixture("invalid_r7_no_self_check.md")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[R7]", res.stderr)
        self.assertIn("missing self-check block", res.stderr)

    def test_disable_comment_passes(self):
        res = fixture("valid_r7_disable_comment.md")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("[R7]", res.stderr)


if __name__ == "__main__":
    unittest.main()
