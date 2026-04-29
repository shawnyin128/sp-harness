"""Regression tests for framework-check-cat4-removal.

Asserts that framework-check SKILL.md no longer carries Cat 4
(Agent templates) content while preserving sparse numbering for
the remaining categories.
"""
from __future__ import annotations

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "framework-check" / "SKILL.md"


class TestCat4HeadingGone(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_no_cat4_section_heading(self):
        # The "### 4. Agent templates" section heading must be fully removed.
        self.assertNotRegex(
            self.text,
            r"^### 4\. Agent templates\b",
            "Cat 4 section heading still present",
        )

    def test_no_cat4_old_format_marker_lines(self):
        # Old-format marker checklist lines from the deleted Cat 4 body
        # must be gone. These three strings appeared as old-format markers
        # in the Cat 4 body; their disappearance signals the body went too.
        for needle in (
            "sp-planner.md does NOT contain `task-plan.json`",
            "sp-generator.md does NOT contain `implementation.md`",
            "sp-evaluator.md does NOT contain `eval-report.json`",
        ):
            self.assertNotIn(needle, self.text, f"residual Cat 4 marker: {needle}")

    def test_remaining_categories_sparse_sequence(self):
        # The remaining "### N. ..." numbered category headings must be
        # 1, 2, 3, 5, 6, 7, 8, 9 (slot 4 absent, rest sparse-but-monotonic).
        nums = [
            int(m.group(1))
            for m in re.finditer(r"^### (\d+)\.", self.text, re.MULTILINE)
        ]
        self.assertEqual(nums, [1, 2, 3, 5, 6, 7, 8, 9])


class TestCardinalityDeclarations(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_check_categories_heading_count_is_8(self):
        self.assertIn("## Check Categories (8)", self.text)
        self.assertNotIn("## Check Categories (9)", self.text)

    def test_frontmatter_description_count_is_8(self):
        # Frontmatter description should declare 8 active check categories,
        # not the historical 7 or 9.
        self.assertIn("Runs 8 check categories", self.text)
        self.assertNotIn("Runs 7 check categories", self.text)
        self.assertNotIn("Runs 9 check categories", self.text)


class TestReportTemplateStub(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_report_template_carries_retired_stub(self):
        # Per D1(a): the [4/9] slot in the report template must be a
        # one-line retired stub, not the old "Agent templates" entry.
        self.assertIn("[4/9] (slot retired — see CHANGELOG)", self.text)

    def test_report_template_no_agent_templates_entry(self):
        # The old "[4/9] Agent templates" label should no longer appear.
        self.assertNotIn("[4/9] Agent templates", self.text)


class TestCriticalFixPathsCat4Gone(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_no_cat4_fix_path_headings(self):
        for needle in (
            "### Agent files missing configurable-language rule",
            "### Agent files missing decision touch-point protocol marker",
            "### Agent template drift",
        ):
            self.assertNotIn(needle, self.text, f"residual Cat 4 fix path: {needle}")

    def test_other_fix_paths_still_present(self):
        for needle in (
            "### CLAUDE.md missing",
            "### CLAUDE.md old format",
            "### CLAUDE.md missing v0.8.5 humanization rules",
            "### CLAUDE.md missing Principle 5",
            "### Legacy `.claude/mem/*.md` files",
            "### Features.json invalid",
            "### sp-harness.json missing or incomplete",
            "### Git conventions",
        ):
            self.assertIn(needle, self.text, f"missing fix path: {needle}")


if __name__ == "__main__":
    unittest.main()
