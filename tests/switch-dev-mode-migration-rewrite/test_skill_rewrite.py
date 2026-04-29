"""Round 1 evaluation tests for switch-dev-mode-migration-rewrite.

After the rewrite, skills/switch-dev-mode/SKILL.md must:
  1. Drop every artefact of the pre-migration template-copy / drift-
     detection / regenerate workflow.
  2. Contain the field-only toggle vocabulary (sp-harness.json + dev_mode).
  3. Enumerate all four migration cleanup targets (sp-planner.md,
     sp-generator.md, sp-evaluator.md, sp-feedback.md).
  4. Still contain the decision-touchpoint-protocol marker (Cat 9).
  5. Still pass scripts/lint-skill-output.py.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "switch-dev-mode" / "SKILL.md"
LINT = REPO_ROOT / "scripts" / "lint-skill-output.py"


class TestRemovedVocabulary(unittest.TestCase):
    """Vocabulary from the old template-copy workflow must be gone."""

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8").lower()

    def test_no_agent_templates_reference(self):
        self.assertNotIn("agent-templates", self.text)

    def test_no_drift_vocabulary(self):
        self.assertNotIn("drift", self.text)

    def test_no_regenerate_vocabulary(self):
        self.assertNotIn("regenerate", self.text)

    def test_no_task_plan_marker(self):
        self.assertNotIn("task-plan.json", self.text)

    def test_no_eval_report_marker(self):
        self.assertNotIn("eval-report.json", self.text)

    def test_no_use_existing_configuration_phrase(self):
        self.assertNotIn("use existing configuration", self.text)


class TestFieldOnlyToggleVocabulary(unittest.TestCase):
    """The remaining responsibility — toggle the dev_mode field — must
    be described explicitly."""

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_mentions_sp_harness_json(self):
        self.assertIn("sp-harness.json", self.text)

    def test_mentions_dev_mode_field(self):
        self.assertIn("dev_mode", self.text)


class TestCleanupTargetsListed(unittest.TestCase):
    """The migration cleanup section must enumerate all four agent
    files, regardless of which dev_mode the project is in."""

    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_lists_sp_planner_file(self):
        self.assertIn("sp-planner.md", self.text)

    def test_lists_sp_generator_file(self):
        self.assertIn("sp-generator.md", self.text)

    def test_lists_sp_evaluator_file(self):
        self.assertIn("sp-evaluator.md", self.text)

    def test_lists_sp_feedback_file(self):
        self.assertIn("sp-feedback.md", self.text)


class TestProtocolMarkerPreserved(unittest.TestCase):
    """framework-check Cat 9 greps for this literal string."""

    def test_decision_touchpoint_protocol_marker_present(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("decision-touchpoint-protocol", text)


class TestLintClean(unittest.TestCase):
    """scripts/lint-skill-output.py must exit 0 on the rewritten file."""

    def test_lint_exits_zero(self):
        res = subprocess.run(
            [sys.executable, str(LINT), "--no-schema-check", "--paths", str(SKILL)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0, res.stderr or res.stdout)


if __name__ == "__main__":
    unittest.main()
