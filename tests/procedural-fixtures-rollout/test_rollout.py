"""Phase 2 rollout regressions for the procedural-skill-fixtures design.

Asserts:
  - brainstorming/SKILL.md has exactly 2 procedural-instruction fences
    (Phase 1 'Presenting the design' + Phase 2 'Exploring approaches')
  - The original 3 directive bullets of Exploring approaches are
    preserved verbatim inside the new fence
  - All four other candidate SKILL.md files (writing-plans,
    executing-plans, code-hygiene, framework-check) have ZERO
    procedural-instruction fences — locks the audit decision so a
    future author cannot quietly add a fence without revisiting
  - Both lint scripts exit 0 on the full skills/ tree

Fence detection uses a line-start regex matching the lint script's
extraction rule, so prose mentions of "```procedural-instruction"
(e.g. as inline code in a documentation paragraph) are not counted.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

# Mirrors lint-skill-procedural.py's _FENCE_OPEN_RE: line starts with
# optional whitespace, then ```procedural-instruction or ```worked-example.
_PROCEDURAL_FENCE_RE = re.compile(
    r"^\s*```procedural-instruction\s*$", re.MULTILINE
)
_WORKED_EXAMPLE_FENCE_RE = re.compile(
    r"^\s*```worked-example\s*$", re.MULTILINE
)

REPO_ROOT = Path(__file__).resolve().parents[2]
LINT_OUTPUT = REPO_ROOT / "scripts" / "lint-skill-output.py"
LINT_PROCEDURAL = REPO_ROOT / "scripts" / "lint-skill-procedural.py"
SKILLS_DIR = REPO_ROOT / "skills"

BRAINSTORMING = SKILLS_DIR / "brainstorming" / "SKILL.md"
AUDIT_NEGATIVES = [
    "writing-plans",
    "executing-plans",
    "code-hygiene",
    "framework-check",
]

EXPLORING_APPROACHES_BULLETS = [
    "- Propose 2-3 different approaches with trade-offs",
    "- Present options conversationally with your recommendation and reasoning",
    "- Lead with your recommended option and explain why",
]


@pytest.fixture(scope="module")
def brainstorming_text() -> str:
    return BRAINSTORMING.read_text(encoding="utf-8")


def test_brainstorming_has_exactly_two_procedural_fences(brainstorming_text: str) -> None:
    count = len(_PROCEDURAL_FENCE_RE.findall(brainstorming_text))
    assert count == 2, (
        f"brainstorming/SKILL.md should have exactly 2 "
        f"procedural-instruction fences after Phase 2 (Presenting the "
        f"design + Exploring approaches); found {count}"
    )


def test_brainstorming_has_exactly_two_worked_examples(brainstorming_text: str) -> None:
    count = len(_WORKED_EXAMPLE_FENCE_RE.findall(brainstorming_text))
    assert count == 2, (
        f"brainstorming/SKILL.md should have exactly 2 worked-example "
        f"fences after Phase 2; found {count}"
    )


def test_exploring_approaches_bullets_preserved(brainstorming_text: str) -> None:
    """Phase 2 fixture must wrap original directive bullets verbatim."""
    for bullet in EXPLORING_APPROACHES_BULLETS:
        assert bullet in brainstorming_text, f"missing bullet: {bullet!r}"


@pytest.mark.parametrize("skill_dir", AUDIT_NEGATIVES)
def test_audit_negatives_have_no_procedural_fence(skill_dir: str) -> None:
    """Locks the Phase 2 audit decision: these files have no procedural-
    instruction fence. Adding one without first revisiting the audit
    fails this test, forcing the author to justify the addition."""
    path = SKILLS_DIR / skill_dir / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    matches = _PROCEDURAL_FENCE_RE.findall(text)
    assert not matches, (
        f"skills/{skill_dir}/SKILL.md must NOT contain a real "
        f"procedural-instruction fence per the Phase 2 audit. If you "
        f"believe a section here qualifies, update the audit in "
        f"docs/design-docs/2026-04-27-procedural-skill-fixtures-design.md "
        f"first, then update this test. (Prose mentions of the fence "
        f"name as inline code are fine — only line-start fences count.)"
    )


def test_lint_skill_procedural_passes_full_tree() -> None:
    res = subprocess.run(
        [sys.executable, str(LINT_PROCEDURAL), "--quiet"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, (
        f"full skills/ tree fails lint-skill-procedural.py: {res.stderr}"
    )


def test_lint_skill_output_passes_full_tree() -> None:
    res = subprocess.run(
        [sys.executable, str(LINT_OUTPUT), "--quiet", "--no-schema-check"],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, (
        f"full skills/ tree fails lint-skill-output.py: {res.stderr}"
    )
