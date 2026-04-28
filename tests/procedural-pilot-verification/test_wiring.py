"""Wiring regressions for the procedural-pilot-verification feature.

Asserts that:
  - skills/framework-check/SKILL.md has a 'Skill procedural lint' subsection
  - The subsection sits after 'Skill output lint'
  - The subsection references P1, P2, P3 and the lint script
  - .gitignore excludes tests/skill-procedural/
  - The 'Internal-only tooling' comment block in .gitignore is intact

The pilot-result artifacts (baseline.md, pilot.md, verdict.md) are
gitignored and not asserted on here. Their existence is verified
manually by the agent that ran the pilot.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FRAMEWORK_CHECK = REPO_ROOT / "skills" / "framework-check" / "SKILL.md"
GITIGNORE = REPO_ROOT / ".gitignore"


@pytest.fixture(scope="module")
def framework_text() -> str:
    return FRAMEWORK_CHECK.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def gitignore_text() -> str:
    return GITIGNORE.read_text(encoding="utf-8")


def test_procedural_lint_subsection_present(framework_text: str) -> None:
    assert "### Skill procedural lint" in framework_text


def test_procedural_lint_after_output_lint(framework_text: str) -> None:
    output_idx = framework_text.index("### Skill output lint")
    procedural_idx = framework_text.index("### Skill procedural lint")
    assert procedural_idx > output_idx, (
        "'Skill procedural lint' subsection must sit after "
        "'Skill output lint' to read top-to-bottom as a pair."
    )


def test_procedural_subsection_references_three_rules(framework_text: str) -> None:
    proc_idx = framework_text.index("### Skill procedural lint")
    next_section = framework_text.index("---", proc_idx)
    block = framework_text[proc_idx:next_section]
    for rule in ("P1", "P2", "P3"):
        assert rule in block, (
            f"'Skill procedural lint' subsection must reference rule "
            f"{rule!r}"
        )


def test_procedural_subsection_invokes_lint_script(framework_text: str) -> None:
    proc_idx = framework_text.index("### Skill procedural lint")
    next_section = framework_text.index("---", proc_idx)
    block = framework_text[proc_idx:next_section]
    assert "lint-skill-procedural.py" in block, (
        "subsection must name the lint script so a maintainer can run it"
    )
    assert "--check" in block, (
        "subsection must show the --check flag for machine-readable output"
    )


def test_gitignore_excludes_skill_procedural(gitignore_text: str) -> None:
    assert "tests/skill-procedural/" in gitignore_text, (
        ".gitignore must exclude tests/skill-procedural/ — the pilot "
        "results and runner are maintainer-local, not distributed"
    )


def test_gitignore_skill_procedural_under_internal_block(gitignore_text: str) -> None:
    """Regression: keep the new entry under the 'Internal-only tooling'
    comment, not stranded elsewhere in the file."""
    block_marker = "# Internal-only tooling (not distributed with the plugin)"
    block_idx = gitignore_text.index(block_marker)
    block_end = gitignore_text.index("\n\n", block_idx)
    block = gitignore_text[block_idx:block_end]
    assert "tests/skill-procedural/" in block, (
        "tests/skill-procedural/ must sit under the 'Internal-only "
        "tooling' comment block alongside skill-routing/skill-pruning"
    )
