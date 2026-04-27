"""Tests for tightened backfill scripts: refuse empty derive output."""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FEATURES_BACKFILL = REPO_ROOT / "skills" / "manage-features" / "scripts" / "backfill_display_names.py"
TODOS_BACKFILL = REPO_ROOT / "skills" / "manage-todos" / "scripts" / "backfill_display_names.py"


def run(script, args, cwd):
    return subprocess.run(
        [sys.executable, str(script), *args],
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


class TestFeaturesBackfillRefusesEmptyDerive(_TempRepo):
    def test_empty_description_causes_failure_naming_id(self):
        seed = {"features": [
            {"id": "ok", "description": "Add a thing", "display_name": "Keep"},
            {"id": "broken-entry", "description": "   "},
        ]}
        (self.tmp / ".claude" / "features.json").write_text(json.dumps(seed))
        res = run(FEATURES_BACKFILL, [], self.tmp)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("broken-entry", res.stderr + res.stdout)
        # File must remain unchanged on failure
        data = json.loads((self.tmp / ".claude" / "features.json").read_text())
        self.assertNotIn("display_name", data["features"][1])

    def test_normal_data_still_passes(self):
        seed = {"features": [
            {"id": "ok-1", "description": "Add the thing", "display_name": "Keep"},
            {"id": "ok-2", "description": "Refactor the other thing"},
        ]}
        (self.tmp / ".claude" / "features.json").write_text(json.dumps(seed))
        res = run(FEATURES_BACKFILL, [], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads((self.tmp / ".claude" / "features.json").read_text())
        for entry in data["features"]:
            self.assertTrue(entry["display_name"].strip())

    def test_idempotent_when_all_filled(self):
        seed = {"features": [
            {"id": "ok-1", "description": "x", "display_name": "Keeper"},
        ]}
        (self.tmp / ".claude" / "features.json").write_text(json.dumps(seed))
        before = (self.tmp / ".claude" / "features.json").read_text()
        res = run(FEATURES_BACKFILL, [], self.tmp)
        self.assertEqual(res.returncode, 0)
        self.assertIn("0 filled", res.stdout)


class TestTodosBackfillRefusesEmptyDerive(_TempRepo):
    def test_empty_description_causes_failure_naming_id(self):
        seed = {"todos": [
            {"id": "broken-todo", "description": "   "},
        ]}
        (self.tmp / ".claude" / "todos.json").write_text(json.dumps(seed))
        res = run(TODOS_BACKFILL, [], self.tmp)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("broken-todo", res.stderr + res.stdout)

    def test_normal_data_still_passes(self):
        seed = {"todos": [
            {"id": "ok", "description": "Investigate the flaky test"},
        ]}
        (self.tmp / ".claude" / "todos.json").write_text(json.dumps(seed))
        res = run(TODOS_BACKFILL, [], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads((self.tmp / ".claude" / "todos.json").read_text())
        self.assertTrue(data["todos"][0]["display_name"].strip())


if __name__ == "__main__":
    unittest.main()
