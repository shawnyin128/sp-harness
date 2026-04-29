"""Role-skill dispatch smoke test (feature: role-skills-test-suite-update, S1).

Structural assertions (no live subagent dispatch) that lock the
post-orchestrator-refactor contract: every orchestrator entry point
that dispatches a role must invoke
``Skill(sp-harness:sp-<role>-role)`` and (where it dispatches a fresh
subagent) must use ``subagent_type='general-purpose'``. The legacy
``@agent sp-<role>`` verb must be absent everywhere.

Mirrors the precedent set by:

  * tests/refactor-three-agent-orchestrator/
  * tests/refactor-single-agent-orchestrator/
  * tests/refactor-feedback-orchestrator/

This suite exists as an architecture-level guard so a future edit
that drops the role-skill dispatch (e.g. reintroduces inline role
content or ``.claude/agents/sp-<role>.md`` paths) is caught here
even if the per-feature tests above are deleted.
"""
from __future__ import annotations

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SINGLE = REPO_ROOT / "skills" / "single-agent-development" / "SKILL.md"
THREE = REPO_ROOT / "skills" / "three-agent-development" / "SKILL.md"
FEEDBACK = REPO_ROOT / "skills" / "feedback" / "SKILL.md"


def _section(text: str, heading: str, next_heading: str) -> str:
    """Return the slice of ``text`` between ``## heading`` and the
    next ``## next_heading`` (exclusive). Asserts a match exists."""
    m = re.search(
        rf"## {re.escape(heading)}.*?(?=^## {re.escape(next_heading)})",
        text,
        re.DOTALL | re.MULTILINE,
    )
    if m is None:
        raise AssertionError(
            f"section '{heading}' (terminator '{next_heading}') not found"
        )
    return m.group(0)


class TestSingleAgentOrchestratorDispatch(unittest.TestCase):
    """skills/single-agent-development dispatches each role-skill in-
    session via ``Skill(...)`` — there is no subagent boundary, so
    ``subagent_type`` is intentionally absent."""

    @classmethod
    def setUpClass(cls):
        cls.text = SINGLE.read_text(encoding="utf-8")

    def test_planner_phase_invokes_planner_role_skill(self):
        s = _section(self.text, "Step 2: Planner Role", "Step 3:")
        self.assertIn("Skill(sp-harness:sp-planner-role)", s)

    def test_generator_phase_invokes_generator_role_skill(self):
        s = _section(self.text, "Step 3: Generator Role", "Step 4:")
        self.assertIn("Skill(sp-harness:sp-generator-role)", s)

    def test_evaluator_phase_invokes_evaluator_role_skill(self):
        s = _section(self.text, "Step 4: Evaluator Role", "Step 5:")
        self.assertIn("Skill(sp-harness:sp-evaluator-role)", s)

    def test_no_legacy_at_agent_dispatch_verb(self):
        self.assertNotRegex(
            self.text,
            r"@agent\s+sp-(planner|generator|evaluator|feedback)\b",
            "single-agent orchestrator still references legacy "
            "'@agent sp-<role>' dispatch verb",
        )

    def test_no_dot_claude_agents_role_paths(self):
        for role in ("sp-planner", "sp-generator", "sp-evaluator", "sp-feedback"):
            self.assertNotIn(
                f".claude/agents/{role}.md",
                self.text,
                f"single-agent orchestrator still references obsolete "
                f".claude/agents/{role}.md path",
            )


class TestThreeAgentOrchestratorDispatch(unittest.TestCase):
    """skills/three-agent-development dispatches each role-skill via a
    fresh general-purpose subagent. Each per-Step dispatch block must
    contain BOTH ``subagent_type='general-purpose'`` AND the role-skill
    identifier."""

    @classmethod
    def setUpClass(cls):
        cls.text = THREE.read_text(encoding="utf-8")

    def test_planner_dispatch_block_has_general_purpose_and_role_skill(self):
        s = _section(self.text, "Step 2: Dispatch Planner", "Step 3:")
        self.assertIn("subagent_type='general-purpose'", s)
        self.assertIn("sp-harness:sp-planner-role", s)

    def test_generator_dispatch_block_has_general_purpose_and_role_skill(self):
        s = _section(self.text, "Step 3: Dispatch Generator", "Step 4:")
        self.assertIn("subagent_type='general-purpose'", s)
        self.assertIn("sp-harness:sp-generator-role", s)

    def test_evaluator_dispatch_block_has_general_purpose_and_role_skill(self):
        s = _section(self.text, "Step 4: Dispatch Evaluator", "Step 5:")
        self.assertIn("subagent_type='general-purpose'", s)
        self.assertIn("sp-harness:sp-evaluator-role", s)

    def test_no_legacy_at_agent_dispatch_verb(self):
        self.assertNotRegex(
            self.text,
            r"@agent\s+sp-(planner|generator|evaluator|feedback)\b",
            "three-agent orchestrator still references legacy "
            "'@agent sp-<role>' dispatch verb",
        )

    def test_no_dot_claude_agents_role_paths(self):
        for role in ("sp-planner", "sp-generator", "sp-evaluator", "sp-feedback"):
            self.assertNotIn(
                f".claude/agents/{role}.md",
                self.text,
                f"three-agent orchestrator still references obsolete "
                f".claude/agents/{role}.md path",
            )


class TestFeedbackOrchestratorDispatch(unittest.TestCase):
    """skills/feedback dispatches sp-feedback-role via a fresh general-
    purpose subagent. Mirrors the three-agent dispatch block shape."""

    @classmethod
    def setUpClass(cls):
        cls.text = FEEDBACK.read_text(encoding="utf-8")

    def test_feedback_dispatch_block_has_general_purpose_and_role_skill(self):
        s = _section(self.text, "Step 2: Dispatch sp-feedback-role in Mode B", "Step 3:")
        self.assertIn("subagent_type='general-purpose'", s)
        self.assertIn("sp-harness:sp-feedback-role", s)

    def test_no_legacy_at_agent_dispatch_verb(self):
        self.assertNotRegex(
            self.text,
            r"@agent\s+sp-feedback\b",
            "feedback orchestrator still references legacy "
            "'@agent sp-feedback' dispatch verb",
        )

    def test_no_dot_claude_agents_feedback_path(self):
        self.assertNotIn(
            ".claude/agents/sp-feedback.md",
            self.text,
            "feedback orchestrator still references obsolete "
            ".claude/agents/sp-feedback.md path",
        )

    def test_references_canonical_three_agent_dispatch_contract(self):
        # Feedback delegates the dispatch-contract to three-agent (DRY).
        self.assertIn("Subagent Dispatch Contract", self.text)


class TestThreeAgentDispatchContractSection(unittest.TestCase):
    """The canonical ``## Subagent Dispatch Contract`` section in the
    three-agent skill is the single source of truth that every other
    orchestrator references. Lock its surface."""

    @classmethod
    def setUpClass(cls):
        cls.text = THREE.read_text(encoding="utf-8")

    def test_contract_section_exists(self):
        self.assertIn("## Subagent Dispatch Contract", self.text)

    def test_contract_names_general_purpose_subagent_type(self):
        # The contract is what tells the dispatcher to use a
        # general-purpose subagent — that literal must be inside it.
        section = self._contract_section()
        self.assertIn("general-purpose", section)

    def test_contract_documents_role_skill_first_invocation(self):
        # The retry-with-stronger-prompt protocol mandates that
        # Skill(sp-harness:sp-<role>-role) is the FIRST tool call. The
        # literal "FIRST" wording is the canonical phrasing today.
        section = self._contract_section()
        self.assertRegex(
            section,
            r"Skill\(sp-harness:sp-<role>-role\)\s+FIRST",
            "Subagent Dispatch Contract no longer enforces the "
            "'Skill(sp-harness:sp-<role>-role) FIRST' rule",
        )

    def test_contract_lists_role_skill_first_action_template(self):
        # The dispatch prompt template itself must instruct the
        # subagent that its first action is invoking the role skill.
        section = self._contract_section()
        self.assertIn("Skill(sp-harness:sp-<role>-role)", section)

    def test_contract_no_legacy_at_agent_dispatch_verb(self):
        section = self._contract_section()
        self.assertNotRegex(
            section,
            r"@agent\s+sp-(planner|generator|evaluator|feedback)\b",
            "Subagent Dispatch Contract still references legacy "
            "'@agent sp-<role>' dispatch verb",
        )

    def _contract_section(self) -> str:
        # The contract section runs from "## Subagent Dispatch
        # Contract" until the next "## " heading at column 0.
        m = re.search(
            r"## Subagent Dispatch Contract.*?(?=^## )",
            self.text,
            re.DOTALL | re.MULTILINE,
        )
        if m is None:
            # Fallback: contract may run to end of file.
            idx = self.text.find("## Subagent Dispatch Contract")
            self.assertNotEqual(
                idx, -1, "Subagent Dispatch Contract section missing entirely"
            )
            return self.text[idx:]
        return m.group(0)


if __name__ == "__main__":
    unittest.main()
