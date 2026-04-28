"""Tests for scripts/lint-skill-procedural.py."""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LINT = REPO_ROOT / "scripts" / "lint-skill-procedural.py"
FIXTURES = pathlib.Path(__file__).resolve().parent / "lint-fixtures"


def run(args, cwd=None):
    return subprocess.run(
        [sys.executable, str(LINT), *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )


def fixture(name, *extra):
    return run(["--paths", str(FIXTURES / name), *extra])


class TestValidFixtures(unittest.TestCase):
    def test_valid_pair_passes(self):
        res = fixture("valid_pair.md")
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_valid_no_fences_passes(self):
        res = fixture("valid_no_fences.md")
        self.assertEqual(res.returncode, 0, res.stderr)


class TestP1Pairing(unittest.TestCase):
    def test_no_pair_fails(self):
        res = fixture("invalid_p1_no_pair.md")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[P1]", res.stderr)
        self.assertIn("not followed by worked-example", res.stderr)

    def test_orphan_example_fails(self):
        res = fixture("invalid_p1_orphan_example.md")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[P1]", res.stderr)
        self.assertIn("not preceded by", res.stderr)

    def test_prose_between_fails(self):
        res = fixture("invalid_p1_prose_between.md")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[P1]", res.stderr)
        self.assertIn("prose between", res.stderr)


class TestP2MinBody(unittest.TestCase):
    def test_short_body_fails(self):
        res = fixture("invalid_p2_short_body.md")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[P2]", res.stderr)
        self.assertIn(">= 100 required", res.stderr)


class TestP3ObservationList(unittest.TestCase):
    def test_no_list_fails(self):
        res = fixture("invalid_p3_no_list.md")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[P3]", res.stderr)

    def test_short_list_fails(self):
        res = fixture("invalid_p3_short_list.md")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[P3]", res.stderr)


class TestAggregation(unittest.TestCase):
    def test_multiple_invalid_fixtures_all_reported(self):
        res = run([
            "--paths",
            str(FIXTURES / "invalid_p2_short_body.md"),
            str(FIXTURES / "invalid_p3_no_list.md"),
        ])
        self.assertEqual(res.returncode, 1)
        self.assertIn("[P2]", res.stderr)
        self.assertIn("[P3]", res.stderr)

    def test_check_mode_emits_json(self):
        res = run(["--paths", str(FIXTURES / "invalid_p2_short_body.md"), "--check"])
        self.assertEqual(res.returncode, 1)
        self.assertIn('"errors"', res.stdout)
        self.assertIn('"files_scanned"', res.stdout)


class TestErrorHandling(unittest.TestCase):
    def test_missing_file_exits_2(self):
        res = run(["--paths", str(FIXTURES / "does_not_exist.md")])
        self.assertEqual(res.returncode, 2)


class TestRealSkillTreePassesTrivially(unittest.TestCase):
    """Regression guard: before any SKILL.md adopts the new fences, the
    full skills/ tree must still lint clean. Otherwise wiring this lint
    into framework-check would break the build before authors have a
    chance to add fixtures."""

    def test_real_skills_tree_passes(self):
        res = run([])  # default scan
        self.assertEqual(res.returncode, 0, res.stderr)


if __name__ == "__main__":
    unittest.main()
