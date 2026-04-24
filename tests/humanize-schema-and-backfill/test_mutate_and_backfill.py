"""End-to-end tests for mutate.py --display-name and backfill scripts."""
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FEATURES_MUTATE = REPO_ROOT / "skills" / "manage-features" / "scripts" / "mutate.py"
FEATURES_BACKFILL = REPO_ROOT / "skills" / "manage-features" / "scripts" / "backfill_display_names.py"
TODOS_MUTATE = REPO_ROOT / "skills" / "manage-todos" / "scripts" / "mutate.py"
TODOS_BACKFILL = REPO_ROOT / "skills" / "manage-todos" / "scripts" / "backfill_display_names.py"


def run(script, args, cwd):
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


class TempRepo(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / ".claude").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestFeaturesMutate(TempRepo):
    def _add(self, *extra):
        return run(
            FEATURES_MUTATE,
            ["add", "--id=f1", "--category=infrastructure", "--priority=high",
             "--description=Add a shiny new thing to the codebase",
             "--steps=a;;b", *extra],
            self.tmp,
        )

    def test_add_auto_derives(self):
        res = self._add()
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads((self.tmp / ".claude" / "features.json").read_text())
        self.assertEqual(data["features"][0]["display_name"],
                         "A shiny new thing")

    def test_add_explicit_overrides(self):
        res = self._add("--display-name=Custom Label")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads((self.tmp / ".claude" / "features.json").read_text())
        self.assertEqual(data["features"][0]["display_name"], "Custom Label")

    def test_update_display_name(self):
        self._add()
        res = run(FEATURES_MUTATE, ["update", "f1", "--display-name=Renamed"], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads((self.tmp / ".claude" / "features.json").read_text())
        self.assertEqual(data["features"][0]["display_name"], "Renamed")

    def test_update_no_args_errors(self):
        self._add()
        res = run(FEATURES_MUTATE, ["update", "f1"], self.tmp)
        self.assertNotEqual(res.returncode, 0)


class TestTodosMutate(TempRepo):
    def _add(self, *extra):
        return run(
            TODOS_MUTATE,
            ["add", "Fix the flaky login test", "--category=tech-debt", *extra],
            self.tmp,
        )

    def test_add_auto_derives(self):
        res = self._add()
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads((self.tmp / ".claude" / "todos.json").read_text())
        self.assertEqual(data["todos"][0]["display_name"],
                         "The flaky login test")

    def test_add_explicit(self):
        res = self._add("--display-name=My Label")
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads((self.tmp / ".claude" / "todos.json").read_text())
        self.assertEqual(data["todos"][0]["display_name"], "My Label")

    def test_update_display_name(self):
        self._add()
        data = json.loads((self.tmp / ".claude" / "todos.json").read_text())
        tid = data["todos"][0]["id"]
        res = run(TODOS_MUTATE, ["update", tid, "--display-name=Renamed"], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads((self.tmp / ".claude" / "todos.json").read_text())
        self.assertEqual(data["todos"][0]["display_name"], "Renamed")

    def test_update_empty_args_errors(self):
        self._add()
        data = json.loads((self.tmp / ".claude" / "todos.json").read_text())
        tid = data["todos"][0]["id"]
        res = run(TODOS_MUTATE, ["update", tid], self.tmp)
        self.assertNotEqual(res.returncode, 0)


class TestFeaturesBackfill(TempRepo):
    def test_fills_and_is_idempotent(self):
        seed = {"features": [
            {"id": "a", "description": "Add the thing", "display_name": "Keeper"},
            {"id": "b", "description": "Refactor the other thing"},
        ]}
        (self.tmp / ".claude" / "features.json").write_text(json.dumps(seed))

        res = run(FEATURES_BACKFILL, [], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("1 filled", res.stdout)

        data = json.loads((self.tmp / ".claude" / "features.json").read_text())
        self.assertEqual(data["features"][0]["display_name"], "Keeper")
        self.assertEqual(data["features"][1]["display_name"], "The other thing")

        before = (self.tmp / ".claude" / "features.json").read_text()
        res2 = run(FEATURES_BACKFILL, [], self.tmp)
        self.assertEqual(res2.returncode, 0)
        self.assertIn("0 filled", res2.stdout)
        self.assertEqual(before, (self.tmp / ".claude" / "features.json").read_text())

    def test_missing_file_errors(self):
        res = run(FEATURES_BACKFILL, [str(self.tmp / "no.json")], self.tmp)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("does not exist", res.stderr)

    def test_empty_entries(self):
        (self.tmp / ".claude" / "features.json").write_text('{"features": []}')
        res = run(FEATURES_BACKFILL, [], self.tmp)
        self.assertEqual(res.returncode, 0)


class TestTodosBackfill(TempRepo):
    def test_fills_and_is_idempotent(self):
        seed = {"todos": [
            {"id": "x", "description": "Investigate something"},
        ]}
        (self.tmp / ".claude" / "todos.json").write_text(json.dumps(seed))
        res = run(TODOS_BACKFILL, [], self.tmp)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads((self.tmp / ".claude" / "todos.json").read_text())
        self.assertTrue(data["todos"][0]["display_name"])

        res2 = run(TODOS_BACKFILL, [], self.tmp)
        self.assertIn("0 filled", res2.stdout)


if __name__ == "__main__":
    unittest.main()
