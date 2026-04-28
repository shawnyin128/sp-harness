"""Markdown-grep regressions for the procedural-rules-chapter feature.

Asserts that writing-skills/SKILL.md contains the new 'Procedural
Section Rules' chapter, the cross-link from 'Output Template Rules',
and the chapter does not contain anti-example markers (which would
violate its own no-anti-example rule). Also runs both lint scripts
against the file as a regression guard.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "writing-skills" / "SKILL.md"
LINT_OUTPUT = REPO_ROOT / "scripts" / "lint-skill-output.py"
LINT_PROCEDURAL = REPO_ROOT / "scripts" / "lint-skill-procedural.py"


@pytest.fixture(scope="module")
def skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def chapter_text(skill_text: str) -> str:
    """Slice writing-skills/SKILL.md to just the new chapter body."""
    start = skill_text.index("## Procedural Section Rules")
    end = skill_text.index("## The Bottom Line", start)
    return skill_text[start:end]


def test_chapter_present(chapter_text: str) -> None:
    assert chapter_text.startswith("## Procedural Section Rules")


def test_chapter_lists_three_rule_names(chapter_text: str) -> None:
    for rule in ("P1", "P2", "P3"):
        assert rule in chapter_text, (
            f"Procedural Section Rules chapter must reference rule {rule!r}"
        )


def test_chapter_required_subheadings(chapter_text: str) -> None:
    required = [
        "### When to use the procedural-instruction fence",
        "### Authoring the worked-example",
        "### The three lint rules",
        "### No anti-examples in the worked-example",
        "### Self-check step",
        "### Wiring lint into your project",
    ]
    for heading in required:
        assert heading in chapter_text, f"missing sub-heading {heading!r}"


def test_chapter_contains_no_anti_example_marker(chapter_text: str) -> None:
    """The chapter teaches a no-anti-example rule and must follow it."""
    assert "❌" not in chapter_text, (
        "Procedural Section Rules chapter must not contain '❌' "
        "anti-example markers — the chapter teaches the rule and "
        "must follow it."
    )
    assert "BAD" not in chapter_text, (
        "Procedural Section Rules chapter must not include 'BAD' "
        "anti-example labels."
    )


def test_chapter_contains_worked_example_demo(chapter_text: str) -> None:
    """The chapter must self-anchor by showing one good worked-example."""
    assert "```procedural-instruction" in chapter_text
    assert "```worked-example" in chapter_text


def test_output_template_chapter_cross_links(skill_text: str) -> None:
    output_idx = skill_text.index("## Output Template Rules")
    next_chapter = skill_text.index("## Procedural Section Rules")
    block = skill_text[output_idx:next_chapter]
    assert "Procedural Section Rules" in block, (
        "'Output Template Rules' chapter must forward-link to "
        "'Procedural Section Rules' so authors finding one chapter "
        "can find the other."
    )
    assert "lint-skill-procedural.py" in block, (
        "Cross-link must name the procedural lint script so authors "
        "know the second mechanism exists."
    )


def test_lint_skill_output_passes(skill_text: str) -> None:
    """Regression: the file still passes the existing output-template lint."""
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
        f"writing-skills/SKILL.md broke lint-skill-output.py: {res.stderr}"
    )


def test_lint_skill_procedural_passes() -> None:
    """Regression: the file passes the new procedural lint.

    The chapter shows the fences inside a 4-backtick wrapper, so they
    are not parsed as real procedural-instruction / worked-example
    blocks. The lint must therefore find no real fences and exit 0.
    """
    res = subprocess.run(
        [sys.executable, str(LINT_PROCEDURAL), "--paths", str(SKILL)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, (
        f"writing-skills/SKILL.md fails lint-skill-procedural.py: "
        f"{res.stderr}"
    )
