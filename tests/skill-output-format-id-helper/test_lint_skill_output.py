"""Tests for scripts/lint-skill-output.py."""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
LINT = REPO_ROOT / "scripts" / "lint-skill-output.py"
FIXTURES = pathlib.Path(__file__).resolve().parent / "lint-fixtures"


def run(args, cwd=None):
    return subprocess.run(
        [sys.executable, str(LINT), *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )


class _NoSchemaCheck(unittest.TestCase):
    """Mixin: most tests use --no-schema-check so we don't depend on
    the project's .claude/ state."""

    def lint_fixture(self, name, *extra):
        return run([
            "--no-schema-check",
            "--paths", str(FIXTURES / name),
            *extra,
        ])


class TestValidFixtures(_NoSchemaCheck):
    def test_valid_simple_passes(self):
        res = self.lint_fixture("valid_simple.md")
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_valid_with_id_placeholder_passes(self):
        res = self.lint_fixture("valid_with_id_placeholder.md")
        self.assertEqual(res.returncode, 0, res.stderr)
        # Regression guard: <feature-id|format> placeholder must not
        # trip the R3 'feature-id' denylist (the literal hides inside
        # an angle-bracket placeholder, not in prose).
        self.assertNotIn("[R3]", res.stderr)

    def test_valid_with_phase_in_gloss_passes(self):
        res = self.lint_fixture("valid_with_phase_in_gloss.md")
        self.assertEqual(res.returncode, 0, res.stderr)
        # Regression guard: a properly glossed codename like
        # 'Phase 3(...)' must not trip the R3 'Phase' denylist —
        # it IS the codename role the rule is exempting.
        self.assertNotIn("[R3]", res.stderr)

    def test_valid_quality_disable_passes(self):
        # The fixture has snake_case + Title Case in a gloss but R3 disabled.
        res = self.lint_fixture("valid_quality_disable.md")
        self.assertEqual(res.returncode, 0, res.stderr)
        # No R3 warnings should be emitted
        self.assertNotIn("[R3]", res.stderr)


class TestInvalidFixtures(_NoSchemaCheck):
    def test_invalid_naked_codename_fails_r1(self):
        res = self.lint_fixture("invalid_naked_codename.md")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[R1]", res.stderr)
        self.assertIn("D1", res.stderr)
        self.assertIn("Phase 3", res.stderr)

    def test_invalid_naked_id_fails_r2(self):
        res = self.lint_fixture("invalid_naked_id.md")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[R2]", res.stderr)
        self.assertIn("feature-id", res.stderr)

    def test_invalid_quality_warns_r3_but_does_not_fail(self):
        res = self.lint_fixture("invalid_quality_warn.md")
        # R3 is warn-only; exit must be 0
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("[R3]", res.stderr)


class TestCliFlags(_NoSchemaCheck):
    def test_check_flag_emits_json_summary(self):
        res = self.lint_fixture("valid_simple.md", "--check")
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["errors"], 0)
        self.assertGreaterEqual(data["files_scanned"], 1)

    def test_quiet_suppresses_pass_lines(self):
        res = self.lint_fixture("valid_simple.md", "--quiet")
        self.assertEqual(res.returncode, 0)
        self.assertNotIn("PASS", res.stdout)
        self.assertNotIn("OK", res.stdout)

    def test_quiet_does_not_suppress_failures(self):
        res = self.lint_fixture("invalid_naked_codename.md", "--quiet")
        self.assertEqual(res.returncode, 1)
        self.assertIn("[R1]", res.stderr)

    def test_paths_scopes_to_listed_files(self):
        # Pass two fixtures, expect only those two scanned
        res = run([
            "--no-schema-check",
            "--check",
            "--paths",
            str(FIXTURES / "valid_simple.md"),
            str(FIXTURES / "invalid_naked_codename.md"),
        ])
        self.assertEqual(res.returncode, 1)  # naked_codename fails
        data = json.loads(res.stdout)
        self.assertEqual(data["files_scanned"], 2)


class TestSchemaCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / ".claude").mkdir()
        (self.tmp / "skills").mkdir()  # so default scan finds nothing odd

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_schema_pass_when_all_have_display_name(self):
        (self.tmp / ".claude" / "features.json").write_text(json.dumps({
            "features": [{"id": "f1", "display_name": "Real label"}]
        }))
        # Run from a tmp cwd; the script always reads from REPO_ROOT/.claude
        # so this exercises the actual repo data. Use --no-schema-check
        # variant of test below for independent assertion.
        res = run([
            "--paths", str(FIXTURES / "valid_simple.md"),
            "--check",
        ])
        # Just verify the script doesn't crash with --check; specific
        # schema pass/fail covered by unit-level test below.
        self.assertIn("errors", res.stdout)


class TestSchemaIntegration(unittest.TestCase):
    """Run the lint module in-process with monkeypatched REPO_ROOT to
    isolate from the project's real .claude/ data."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        (self.tmp / ".claude").mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _import_module(self):
        # Re-import the script as a module. Must register in sys.modules
        # BEFORE exec_module — @dataclass needs to look up cls.__module__
        # via sys.modules and a hyphenated filename otherwise leaves it
        # unregistered.
        import importlib.util
        spec = importlib.util.spec_from_file_location("lint_skill_output", LINT)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["lint_skill_output"] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_check_schema_passes_with_valid_data(self):
        mod = self._import_module()
        (self.tmp / ".claude" / "features.json").write_text(json.dumps({
            "features": [{"id": "f1", "display_name": "Good"}]
        }))
        (self.tmp / ".claude" / "todos.json").write_text(json.dumps({
            "todos": [{"id": "t1", "display_name": "Good"}]
        }))
        fails = mod.check_schema(self.tmp)
        self.assertEqual(fails, [])

    def test_check_schema_fails_with_empty_display_name(self):
        mod = self._import_module()
        (self.tmp / ".claude" / "features.json").write_text(json.dumps({
            "features": [{"id": "f1", "display_name": ""}]
        }))
        fails = mod.check_schema(self.tmp)
        self.assertEqual(len(fails), 1)
        self.assertIn("f1", fails[0])
        self.assertIn("display_name", fails[0])

    def test_check_schema_fails_with_missing_display_name_key(self):
        mod = self._import_module()
        (self.tmp / ".claude" / "todos.json").write_text(json.dumps({
            "todos": [{"id": "t1"}]
        }))
        fails = mod.check_schema(self.tmp)
        self.assertEqual(len(fails), 1)
        self.assertIn("t1", fails[0])

    def test_check_schema_skips_when_files_absent(self):
        mod = self._import_module()
        # No json files written
        fails = mod.check_schema(self.tmp)
        self.assertEqual(fails, [])


if __name__ == "__main__":
    unittest.main()
