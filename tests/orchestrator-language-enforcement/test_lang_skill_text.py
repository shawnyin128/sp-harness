"""Markdown-grep regression for the orchestrator-language-enforcement feature.

Three orchestrator SKILLs must each contain the "Session language"
directive that mirrors the subagent-template language rule. sp-feedback
Mode A must contain a checklist line that flags language drift.
Version-frontmatter assertions guard against silent downgrade.
"""

from pathlib import Path

import pytest

from _helpers.version_check import assert_min_version

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TRACKER = REPO_ROOT / "skills" / "feature-tracker" / "SKILL.md"
SINGLE_AGENT = REPO_ROOT / "skills" / "single-agent-development" / "SKILL.md"
THREE_AGENT = REPO_ROOT / "skills" / "three-agent-development" / "SKILL.md"
SP_FEEDBACK = REPO_ROOT / "agent-templates" / "sp-feedback.md"


@pytest.fixture(scope="module")
def tracker_text() -> str:
    return TRACKER.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def single_agent_text() -> str:
    return SINGLE_AGENT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def three_agent_text() -> str:
    return THREE_AGENT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sp_feedback_text() -> str:
    return SP_FEEDBACK.read_text(encoding="utf-8")


# --- "Session language" directive across the three orchestrator SKILLs -------


def _assert_directive(text: str, label: str) -> None:
    assert "Session language" in text, (
        f"{label} must contain the literal 'Session language' declaration "
        f"directive that mirrors the subagent template rule."
    )
    assert "match-input" in text, (
        f"{label} must describe the 'match-input' default behavior."
    )
    assert "no code-mixing" in text, (
        f"{label} must explicitly forbid code-mixing within a single message."
    )


def test_tracker_has_language_directive(tracker_text: str) -> None:
    _assert_directive(tracker_text, "skills/feature-tracker/SKILL.md")


def test_single_agent_has_language_directive(single_agent_text: str) -> None:
    _assert_directive(single_agent_text, "skills/single-agent-development/SKILL.md")


def test_three_agent_has_language_directive(three_agent_text: str) -> None:
    _assert_directive(three_agent_text, "skills/three-agent-development/SKILL.md")


# --- sp-feedback Mode A language-compliance check ---------------------------


def test_sp_feedback_mode_a_has_language_check(sp_feedback_text: str) -> None:
    """sp-feedback Mode A must surface a language-compliance check so that
    a future feature where language=zh produced English orchestrator output
    is automatically flagged for follow-up. Pin the exact section heading
    so removing the new dimension fails this test loudly — the previous
    version of this assertion passed vacuously off pre-existing
    'language' / 'orchestrator' mentions elsewhere in the template."""
    assert "### 8. Language compliance" in sp_feedback_text, (
        "agent-templates/sp-feedback.md must contain the literal heading "
        "'### 8. Language compliance' for the Mode A checklist's "
        "orchestrator-output drift dimension."
    )
    assert "orchestrator-output drift" in sp_feedback_text, (
        "The new dimension's heading must include 'orchestrator-output "
        "drift' so future readers see what the check is for."
    )
    # Header count must match actual section count.
    assert "Structured Checklist (8 dimensions)" in sp_feedback_text, (
        "The Structured Checklist heading must declare 8 dimensions, "
        "matching the section count after this feature."
    )


# --- version frontmatter ----------------------------------------------------


def test_tracker_skill_version_at_or_above_3_4(tracker_text: str) -> None:
    assert_min_version(
        tracker_text,
        major=3,
        min_minor=4,
        file_label="skills/feature-tracker/SKILL.md",
    )


def test_single_agent_version_at_or_above_2_1(single_agent_text: str) -> None:
    assert_min_version(
        single_agent_text,
        major=2,
        min_minor=1,
        file_label="skills/single-agent-development/SKILL.md",
    )


def test_three_agent_version_at_or_above_3_1(three_agent_text: str) -> None:
    assert_min_version(
        three_agent_text,
        major=3,
        min_minor=1,
        file_label="skills/three-agent-development/SKILL.md",
    )
