"""Tests for tightened display_name validation in manage-features mutate.py."""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MUTATE = REPO_ROOT / "skills" / "manage-features" / "scripts" / "mutate.py"


def run(args, cwd):
    return subprocess.run(
        [sys.executable, str(MUTATE), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


class _TempRepo(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / ".claude").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def features(self):
        path = self.tmp / ".claude" / "features.json"
        return json.loads(path.read_text()) if path.exists() else None

    def add(self, *extra):
        return run(
            ["add", "--id=f1", "--category=infrastructure", "--priority=high",
             "--description=Add a shiny thing to the codebase",
             "--steps=a;;b", *extra],
            self.tmp,
        )


class TestAddRejectsBlank(_TempRepo):
    def test_add_with_valid_derive_passes(self):
        res = self.add()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(self.features()["features"][0]["display_name"].strip())

    def test_add_with_empty_display_name_rejected(self):
        res = self.add("--display-name=")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("display_name", res.stderr.lower())
        self.assertIsNone(self.features())  # nothing written

    def test_add_with_whitespace_display_name_rejected(self):
        res = self.add("--display-name=   ")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("display_name", res.stderr.lower())
        self.assertIsNone(self.features())

    def test_add_when_derive_returns_empty_rejected(self):
        # Description with only punctuation/whitespace defeats the derive heuristic
        res = run(
            ["add", "--id=f1", "--category=infrastructure", "--priority=high",
             "--description=   ", "--steps=a"],
            self.tmp,
        )
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("display_name", res.stderr.lower())


class TestUpdateRejectsBlank(_TempRepo):
    def test_update_to_empty_rejected(self):
        self.assertEqual(self.add().returncode, 0)
        res = run(["update", "f1", "--display-name="], self.tmp)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("display_name", res.stderr.lower())

    def test_update_to_whitespace_rejected(self):
        self.assertEqual(self.add().returncode, 0)
        res = run(["update", "f1", "--display-name=   "], self.tmp)
        self.assertNotEqual(res.returncode, 0)

    def test_update_to_valid_succeeds(self):
        self.assertEqual(self.add().returncode, 0)
        res = run(["update", "f1", "--display-name=Renamed clearly"], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.features()["features"][0]["display_name"], "Renamed clearly")


if __name__ == "__main__":
    unittest.main()
