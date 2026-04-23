"""
Evaluator tests for tests/skill-routing/tally.py.

Runs under plain stdlib unittest. No external deps. Covers:
  - extract_skill: first-match, nested braces, multiple blocks, unparseable paths
  - classify: 6 verdict combinations per spec
  - main: exit codes + summary line via subprocess
"""
import json
import pathlib
import subprocess
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
TALLY_PY = REPO_ROOT / "tests" / "skill-routing" / "tally.py"

sys.path.insert(0, str(TALLY_PY.parent))
import tally  # noqa: E402


def _run_tally(results: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TALLY_PY)],
        input=json.dumps(results),
        capture_output=True,
        text=True,
    )


def _vote(skill: str) -> dict:
    return {"output": f'```json\n{{"primary_skill": "{skill}", "rationale": "r"}}\n```', "exit_code": 0}


class ExtractSkillTests(unittest.TestCase):
    def test_first_match_wins_when_multiple_json_blocks(self):
        text = (
            "preamble\n"
            "```json\n"
            '{"primary_skill": "feedback", "rationale": "first"}\n'
            "```\n"
            "and here is a different block for reference:\n"
            "```json\n"
            '{"primary_skill": "brainstorming", "rationale": "second"}\n'
            "```\n"
        )
        self.assertEqual(tally.extract_skill(text), "feedback")

    def test_handles_nested_braces_inside_json(self):
        text = '```json\n{"primary_skill": "x", "meta": {"nested": true}}\n```'
        self.assertEqual(tally.extract_skill(text), "x")

    def test_empty_output_is_unparseable(self):
        self.assertEqual(tally.extract_skill(""), "unparseable")

    def test_no_fenced_block_is_unparseable(self):
        self.assertEqual(tally.extract_skill("just prose, no code block"), "unparseable")

    def test_malformed_json_inside_block_is_unparseable(self):
        text = "```json\n{this is not json}\n```"
        self.assertEqual(tally.extract_skill(text), "unparseable")

    def test_missing_primary_skill_field_is_unparseable(self):
        text = '```json\n{"rationale": "nope"}\n```'
        self.assertEqual(tally.extract_skill(text), "unparseable")

    def test_empty_primary_skill_string_is_unparseable(self):
        text = '```json\n{"primary_skill": "   ", "rationale": "x"}\n```'
        self.assertEqual(tally.extract_skill(text), "unparseable")

    def test_whitespace_around_skill_is_stripped(self):
        text = '```json\n{"primary_skill": "  feedback  "}\n```'
        self.assertEqual(tally.extract_skill(text), "feedback")


class ClassifyTests(unittest.TestCase):
    def test_three_of_three_matching_is_pass(self):
        self.assertEqual(tally.classify(["a", "a", "a"], "a"), "PASS")

    def test_two_of_three_matching_is_pass_weak(self):
        self.assertEqual(tally.classify(["a", "a", "b"], "a"), "PASS-WEAK")
        self.assertEqual(tally.classify(["a", "a", "unparseable"], "a"), "PASS-WEAK")

    def test_one_of_three_matching_is_fail(self):
        self.assertEqual(tally.classify(["a", "b", "c"], "a"), "FAIL")

    def test_zero_matching_with_disagreement_is_flaky(self):
        self.assertEqual(tally.classify(["b", "c", "d"], "a"), "FLAKY")

    def test_zero_matching_all_unparseable_is_fail(self):
        self.assertEqual(
            tally.classify(["unparseable", "unparseable", "unparseable"], "a"),
            "FAIL",
        )

    def test_zero_matching_consensus_on_wrong_skill_is_fail(self):
        self.assertEqual(tally.classify(["b", "b", "b"], "a"), "FAIL")

    def test_zero_matching_two_wrong_one_unparseable_is_fail(self):
        # one distinct valid vote → not FLAKY → FAIL
        self.assertEqual(tally.classify(["b", "b", "unparseable"], "a"), "FAIL")


class MainExitCodeTests(unittest.TestCase):
    def test_all_pass_exits_zero(self):
        data = {
            "scenarios": [
                {"id": "s1", "expected": "feedback", "votes": [_vote("feedback")] * 3},
            ]
        }
        r = _run_tally(data)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("PASS", r.stdout)

    def test_fail_exits_nonzero(self):
        data = {
            "scenarios": [
                {"id": "s1", "expected": "feedback",
                 "votes": [_vote("brainstorming"), _vote("brainstorming"), _vote("brainstorming")]},
            ]
        }
        r = _run_tally(data)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL", r.stdout)

    def test_flaky_exits_nonzero(self):
        data = {
            "scenarios": [
                {"id": "s1", "expected": "feedback",
                 "votes": [_vote("a"), _vote("b"), _vote("c")]},
            ]
        }
        r = _run_tally(data)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FLAKY", r.stdout)

    def test_pass_weak_exits_zero(self):
        data = {
            "scenarios": [
                {"id": "s1", "expected": "feedback",
                 "votes": [_vote("feedback"), _vote("feedback"), _vote("other")]},
            ]
        }
        r = _run_tally(data)
        self.assertEqual(r.returncode, 0)
        self.assertIn("PASS-WEAK", r.stdout)

    def test_empty_scenarios_exits_zero(self):
        r = _run_tally({"scenarios": []})
        self.assertEqual(r.returncode, 0)
        self.assertIn("No scenarios to tally", r.stdout)

    def test_malformed_stdin_exits_nonzero_with_clear_error(self):
        r = subprocess.run(
            [sys.executable, str(TALLY_PY)],
            input="this is not json",
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invalid results JSON", r.stderr)

    def test_summary_line_counts_correct(self):
        data = {
            "scenarios": [
                {"id": "a", "expected": "x", "votes": [_vote("x")] * 3},
                {"id": "b", "expected": "x", "votes": [_vote("x"), _vote("x"), _vote("y")]},
                {"id": "c", "expected": "x", "votes": [_vote("y")] * 3},
                {"id": "d", "expected": "x", "votes": [_vote("a"), _vote("b"), _vote("c")]},
            ]
        }
        r = _run_tally(data)
        self.assertEqual(r.returncode, 1)
        self.assertIn("1 PASS", r.stdout)
        self.assertIn("1 PASS-WEAK", r.stdout)
        self.assertIn("1 FAIL", r.stdout)
        self.assertIn("1 FLAKY", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
