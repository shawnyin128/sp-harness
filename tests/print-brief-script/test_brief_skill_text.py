"""Markdown-grep regressions for the print-brief-script feature.

Snapshot tests in test_print_brief.py cover the script's output. These
tests cover the SKILL.md and plan-file-schema.md edits that mandate the
script call and document the language exception. If a future edit
silently drops the canonical command, the language note, or the version
bump, these tests fail loudly.
"""

from pathlib import Path

import pytest

from _helpers.version_check import assert_min_version

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TRACKER = REPO_ROOT / "skills" / "feature-tracker" / "SKILL.md"
SCHEMA = REPO_ROOT / "docs" / "plan-file-schema.md"


@pytest.fixture(scope="module")
def tracker_text() -> str:
    return TRACKER.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def schema_text() -> str:
    return SCHEMA.read_text(encoding="utf-8")


def test_brief_block_mandates_script_call(tracker_text: str) -> None:
    """feature-tracker Step 5 brief block must explicitly require running
    the script and reference its canonical path."""
    brief_idx = tracker_text.index("MUST: Print Feature Brief")
    block = tracker_text[brief_idx : brief_idx + 4000]
    assert "MUST run this script" in block, (
        "feature-tracker Step 5 brief block must contain 'MUST run this "
        "script' — the prose template is gone, the script is the contract."
    )
    assert "skills/feature-tracker/scripts/print-brief.py" in block, (
        "feature-tracker Step 5 brief block must reference the canonical "
        "script path so the orchestrator knows what to invoke."
    )


def test_brief_block_documents_english_only_exception(tracker_text: str) -> None:
    """The language-exception paragraph must be in the brief block; otherwise
    a future agent reading the SKILL would mistakenly try to translate the
    brief and break determinism."""
    brief_idx = tracker_text.index("MUST: Print Feature Brief")
    block = tracker_text[brief_idx : brief_idx + 4000]
    assert "English-only" in block, (
        "feature-tracker Step 5 brief block must declare the brief is "
        "'English-only' regardless of language config."
    )


def test_schema_cross_references_brief_language_exception(schema_text: str) -> None:
    """plan-file-schema.md must mirror the language-exception note so the
    rule is discoverable from the schema side too."""
    assert "print-brief.py" in schema_text, (
        "docs/plan-file-schema.md must reference print-brief.py to anchor "
        "the language exception note."
    )
    assert "English-only" in schema_text, (
        "docs/plan-file-schema.md must contain the 'English-only' phrase "
        "for the brief script's language exception."
    )


def test_tracker_skill_version_at_or_above_3_3(tracker_text: str) -> None:
    """feature-tracker SKILL.md must be at 3.3.0 or later — this feature's
    bump baseline. Subsequent features may bump further."""
    assert_min_version(
        tracker_text,
        major=3,
        min_minor=3,
        file_label="skills/feature-tracker/SKILL.md",
    )
