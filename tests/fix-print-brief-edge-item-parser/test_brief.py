"""Regression test for the print-brief.py mapping-item misclassification bug.

The bundled YAML loader used to treat any "- ident: rest" sequence
item as a mapping with head ``ident``. Plain-prose items written as
``- Edge: <description>`` matched that pattern (Edge is a bare
identifier), so the loader entered a mapping-item continuation
branch, dropped the wrapped prose continuation line, and desynced the
indent stack. The host step's mapping then terminated early and every
later step in the steps[] sequence was lost. The role-skills-test-suite-update
archived plan reproduced it: brief reported "2 steps · 0 tests" while
the YAML actually contained 5 steps and 202 tests.

The fix gates the mapping-item branch on an allow-list of canonical
plan-file-schema keys. Anything else (Edge, Bug, Note, ...) falls
through to the scalar branch which already handles wrapped continuations.

Both layers are guarded:
  * parser-level — load_yaml on the verbatim fixture must produce
    five steps and a fully populated last-round tests dict.
  * brief-level — build_brief on that loaded plan must contain the
    canonical "5 steps" and "202 tests" substrings the fix targets.
"""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "skills" / "feature-tracker" / "scripts" / "print-brief.py"
FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "role-skills-yaml.yaml"


def _load_module():
    spec = importlib.util.spec_from_file_location("print_brief_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestEdgeProseItemRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load_module()
        cls.text = FIXTURE.read_text()
        cls.plan = cls.mod.load_yaml(cls.text)

    def test_loader_parses_all_five_steps(self):
        steps = self.plan.get("steps")
        self.assertIsInstance(steps, list)
        self.assertEqual(
            len(steps),
            5,
            f"loader lost steps after Edge: prose items; got {len(steps)} expected 5",
        )

    def test_loader_keeps_last_round_tests_populated(self):
        rounds = (self.plan.get("eval") or {}).get("rounds") or []
        self.assertEqual(len(rounds), 1)
        tests = rounds[-1].get("tests") or {}
        self.assertGreaterEqual(
            len(tests),
            5,
            "last-round tests dict missing entries; loader desync probably truncated it",
        )

    def test_brief_renders_correct_step_and_test_counts(self):
        brief = self.mod.build_brief(
            self.plan,
            display_name="Role skills test suite update",
            feature_id="role-skills-test-suite-update",
            commit="deadbee",
        )
        self.assertIn("5 steps", brief)
        self.assertIn("202 tests", brief)

    def test_canonical_mapping_key_still_parses_as_mapping(self):
        """Guard against over-tightening: a real schema mapping-item must
        still be recognized so decisions[]/rounds[] etc. don't regress."""
        snippet = (
            "decisions:\n"
            "  - id: D1\n"
            "    question: Sample\n"
            "    confidence: 80\n"
        )
        parsed = self.mod.load_yaml(snippet)
        decisions = parsed.get("decisions")
        self.assertIsInstance(decisions, list)
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].get("id"), "D1")
        self.assertEqual(decisions[0].get("confidence"), 80)


if __name__ == "__main__":
    unittest.main()
