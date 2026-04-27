"""Tests for tightened display_name validation in manage-todos mutate.py."""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MUTATE = REPO_ROOT / "skills" / "manage-todos" / "scripts" / "mutate.py"


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

    def todos(self):
        path = self.tmp / ".claude" / "todos.json"
        return json.loads(path.read_text()) if path.exists() else None

    def add(self, *extra, description="Investigate the flaky login test path"):
        return run(
            ["add", description, "--category=tech-debt", *extra],
            self.tmp,
        )


class TestAddRejectsBlank(_TempRepo):
    def test_add_with_valid_derive_passes(self):
        res = self.add()
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue(self.todos()["todos"][0]["display_name"].strip())

    def test_add_with_empty_display_name_rejected(self):
        res = self.add("--display-name=")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("display_name", res.stderr.lower())
        self.assertIsNone(self.todos())

    def test_add_with_whitespace_display_name_rejected(self):
        res = self.add("--display-name=   ")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("display_name", res.stderr.lower())

    def test_add_when_derive_returns_empty_rejected(self):
        res = self.add(description="   ")
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("display_name", res.stderr.lower())


class TestUpdateRejectsBlank(_TempRepo):
    def _added_id(self):
        self.assertEqual(self.add().returncode, 0)
        return self.todos()["todos"][0]["id"]

    def test_update_to_empty_rejected(self):
        tid = self._added_id()
        res = run(["update", tid, "--display-name="], self.tmp)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("display_name", res.stderr.lower())

    def test_update_to_whitespace_rejected(self):
        tid = self._added_id()
        res = run(["update", tid, "--display-name=   "], self.tmp)
        self.assertNotEqual(res.returncode, 0)

    def test_update_to_valid_succeeds(self):
        tid = self._added_id()
        res = run(["update", tid, "--display-name=Renamed clearly"], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(self.todos()["todos"][0]["display_name"], "Renamed clearly")


if __name__ == "__main__":
    unittest.main()
