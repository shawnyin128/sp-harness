"""Markdown-grep regressions for the procedural-brainstorm-pilot feature.

Asserts the Phase 1 pilot fixture in skills/brainstorming/SKILL.md:
the 'Presenting the design' section is wrapped in the new fence pair,
the original 5 bullets are preserved verbatim, the worked-example body
satisfies P2/P3, and Phase 1 stops at exactly one fence pair.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "brainstorming" / "SKILL.md"
LINT_OUTPUT = REPO_ROOT / "scripts" / "lint-skill-output.py"
LINT_PROCEDURAL = REPO_ROOT / "scripts" / "lint-skill-procedural.py"

ORIGINAL_BULLETS = [
    "- Once you believe you understand what you're building, present the design",
    "- Scale each section to its complexity: a few sentences if straightforward, up to 200-300 words if nuanced",
    "- Ask after each section whether it looks right so far",
    "- Cover: architecture, components, data flow, error handling, testing",
    "- Be ready to go back and clarify if something doesn't make sense",
]


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_header_preserved(skill_text: str) -> None:
    """Bold-style header is unchanged (no upgrade to ### per D3)."""
    assert "**Presenting the design:**" in skill_text


def test_procedural_instruction_fence_present(skill_text: str) -> None:
    """The fence wrapping the directive bullets opens after the header."""
    header_idx = skill_text.index("**Presenting the design:**")
    after_header = skill_text[header_idx:header_idx + 200]
    assert "```procedural-instruction" in after_header, (
        "procedural-instruction fence must follow the section header "
        "within a small window (no other content between)"
    )


def test_original_bullets_preserved_verbatim(skill_text: str) -> None:
    """All 5 original directive bullets must appear verbatim inside
    the procedural-instruction fence — D1 says directive content is
    untouched, the fixture is the only addition."""
    for bullet in ORIGINAL_BULLETS:
        assert bullet in skill_text, f"missing original bullet: {bullet!r}"


def test_worked_example_fence_follows(skill_text: str) -> None:
    """Worked-example must immediately follow the procedural-instruction
    fence (only blank lines between, per P1)."""
    proc_idx = skill_text.index("```procedural-instruction")
    proc_close = skill_text.index("\n```\n", proc_idx)
    tail = skill_text[proc_close + 5:proc_close + 200]
    # Only blank lines may separate; the next non-blank thing must be
    # the worked-example fence open.
    next_non_blank = next(
        (line for line in tail.splitlines() if line.strip()),
        None,
    )
    assert next_non_blank == "```worked-example", (
        f"expected next non-blank line to be ```worked-example, got "
        f"{next_non_blank!r}"
    )


def test_worked_example_body_satisfies_p2_min_words(skill_text: str) -> None:
    """Body must contain >= 100 whitespace-separated words (P2)."""
    body = _extract_worked_example_body(skill_text)
    word_count = sum(len(line.split()) for line in body.splitlines())
    assert word_count >= 100, (
        f"worked-example body has {word_count} words; P2 requires >= 100"
    )


def test_worked_example_body_satisfies_p3_observation_list(skill_text: str) -> None:
    """Body must contain >= 3 numbered list items (P3)."""
    body = _extract_worked_example_body(skill_text)
    items = [
        line for line in body.splitlines()
        if re.match(r"^\s*\d+\.\s+\S", line)
    ]
    assert len(items) >= 3, (
        f"worked-example body has {len(items)} numbered items; "
        f"P3 requires >= 3"
    )


def test_phase_1_stops_at_one_pair(skill_text: str) -> None:
    """Phase 1 wraps exactly ONE section. Phase 2 owns rollout."""
    proc_count = skill_text.count("```procedural-instruction")
    assert proc_count == 1, (
        f"expected exactly 1 procedural-instruction fence in "
        f"brainstorming/SKILL.md (Phase 1 single-section pilot); "
        f"found {proc_count}"
    )
    we_count = skill_text.count("```worked-example")
    assert we_count == 1, (
        f"expected exactly 1 worked-example fence; found {we_count}"
    )


def test_lint_skill_procedural_passes() -> None:
    res = subprocess.run(
        [sys.executable, str(LINT_PROCEDURAL), "--paths", str(SKILL)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, (
        f"brainstorming/SKILL.md fails procedural lint: {res.stderr}"
    )


def test_lint_skill_output_passes() -> None:
    res = subprocess.run(
        [
            sys.executable,
            str(LINT_OUTPUT),
            "--paths",
            str(SKILL),
            "--no-schema-check",
        ],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, (
        f"brainstorming/SKILL.md fails output-template lint: {res.stderr}"
    )


def _extract_worked_example_body(text: str) -> str:
    """Return the body of the single worked-example fence in the file."""
    open_idx = text.index("```worked-example")
    body_start = text.index("\n", open_idx) + 1
    body_end = text.index("\n```", body_start)
    return text[body_start:body_end]
