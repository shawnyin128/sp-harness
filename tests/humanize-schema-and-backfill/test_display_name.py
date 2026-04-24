"""Evaluator tests for derive_display_name heuristic."""
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "skills" / "manage-features" / "scripts"))
from display_name import derive_display_name  # noqa: E402


class TestDeriveDisplayName(unittest.TestCase):
    def test_strips_leading_verb(self):
        self.assertEqual(
            derive_display_name("Add display_name field to features.json"),
            "Display_name field to features.json",
        )
        self.assertEqual(
            derive_display_name("Fix the flaky login test"),
            "The flaky login test",
        )

    def test_verb_match_case_insensitive(self):
        self.assertEqual(
            derive_display_name("REFACTOR the thing"),
            "The thing",
        )

    def test_non_verb_start_unchanged(self):
        self.assertEqual(
            derive_display_name("Humanize sp-harness output"),
            "Humanize sp-harness output",
        )

    def test_trailing_punctuation_stripped(self):
        self.assertEqual(
            derive_display_name("Something important."),
            "Something important",
        )

    def test_caps_at_five_words(self):
        out = derive_display_name(
            "Commit templates feature-tracker listings and manage-star query output"
        )
        self.assertLessEqual(len(out.split()), 5)

    def test_five_word_cap_applies_before_char_cap(self):
        # Description under 50 chars but over 5 words → word cap still trims it
        out = derive_display_name("one two three four five six seven")
        self.assertEqual(len(out.split()), 5)
        self.assertEqual(out, "one two three four five")

    def test_truncate_strips_trailing_connectors_and_commas(self):
        out = derive_display_name(
            "Commit templates, feature-tracker listings, and manage-* query output"
        )
        self.assertLessEqual(len(out), 50)
        for bad in (",", " and", " with", " for", " to", " the", " of"):
            self.assertFalse(out.endswith(bad), f"{out!r} ends with {bad!r}")

    def test_truncates_at_word_boundary(self):
        out = derive_display_name(
            "A very long description that goes way past fifty characters so truncation kicks in here"
        )
        self.assertLessEqual(len(out), 50)
        self.assertFalse(out.endswith(" "))
        self.assertTrue(out.startswith("A very long"))

    def test_short_description_passthrough(self):
        self.assertEqual(derive_display_name("Short desc"), "Short desc")

    def test_empty_and_whitespace(self):
        self.assertEqual(derive_display_name(""), "")
        self.assertEqual(derive_display_name("   "), "")
        self.assertEqual(derive_display_name("..."), "")
        self.assertEqual(derive_display_name(None), "")

    def test_verb_alone_returned_as_is(self):
        # Single-token "add" has no tail to strip to — heuristic leaves it.
        self.assertEqual(derive_display_name("add"), "add")

    def test_idempotent(self):
        inputs = [
            "Add display_name field to features.json",
            "A very long description that goes way past fifty characters for sure",
            "Short desc",
            "Humanize sp-harness output",
        ]
        for x in inputs:
            with self.subTest(x=x):
                once = derive_display_name(x)
                twice = derive_display_name(once)
                self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
