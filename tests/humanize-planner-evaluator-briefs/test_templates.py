"""Evaluator checks for humanized planner / evaluator terminal templates."""
import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PLANNER = REPO_ROOT / "agent-templates" / "sp-planner.md"
EVALUATOR = REPO_ROOT / "agent-templates" / "sp-evaluator.md"


def phase3_block(content: str) -> str:
    m = re.search(r"## Phase 3:.*?(?=^## )", content, re.DOTALL | re.MULTILINE)
    assert m, "could not locate Phase 3 section in sp-planner.md"
    return m.group(0)


def terminal_block(content: str) -> str:
    m = re.search(r"## Terminal Output.*?(?=^## )", content, re.DOTALL | re.MULTILINE)
    assert m, "could not locate Terminal Output section in sp-evaluator.md"
    return m.group(0)


class TestPlannerTemplate(unittest.TestCase):
    def setUp(self):
        self.full = PLANNER.read_text()
        self.block = phase3_block(self.full)

    def test_no_ds_coordinate_prefixes_in_brief(self):
        self.assertNotRegex(self.block, r"\bS\d\s*·")
        self.assertNotRegex(self.block, r"\bD\d\s*·")

    def test_numbered_step_list_present(self):
        self.assertRegex(self.block, r"\n\s*1\.\s+<desc>")
        self.assertRegex(self.block, r"\n\s*2\.\s+<desc>")

    def test_checkmark_decision_lines_present(self):
        self.assertIn("✓ <question>", self.block)

    def test_warning_still_marks_ask_user(self):
        self.assertIn("⚠️ <question>", self.block)

    def test_your_call_prompt_drops_d1(self):
        self.assertNotIn("Your call on D1", self.block)
        self.assertIn("Your call on the ⚠️ decisions", self.block)

    def test_yaml_schema_ids_still_present(self):
        # The YAML example block still defines id fields; only the printed
        # brief drops the coordinate prefix.
        self.assertRegex(self.full, r"- id: D1")
        self.assertRegex(self.full, r"- id: S1")
        self.assertIn("user_decision: null", self.full)


class TestEvaluatorTemplate(unittest.TestCase):
    def setUp(self):
        self.full = EVALUATOR.read_text()
        self.block = terminal_block(self.full)

    def test_no_s_coordinate_prefix_in_unit_tests(self):
        self.assertNotRegex(self.block, r"^\s*S\d\s*\(", )

    def test_closure_uses_question_text(self):
        self.assertRegex(self.block, r"✓ <decision \d question text>")

    def test_yaml_schema_id_refs_still_present_elsewhere_in_file(self):
        # YAML example block still shows id: D1, user_decisions_honored, etc.
        self.assertIn("- id: D1", self.full)
        self.assertIn("user_decisions_honored", self.full)


if __name__ == "__main__":
    unittest.main()
