"""Regression tests for the hygiene -> feature-tracker control-return chain.

The bug being guarded against: when feature-tracker dispatches code-hygiene
at Step 5d, an LLM orchestrator may treat hygiene's report+commit as the end
of the entire feature loop and skip the rest of Step 5 (counter update,
Feature Brief, loop-back to Step 2). Two skill files install textual signals
that fight that failure mode; if any of those markers gets removed during a
future edit, the silent regression returns. These tests grep the live
SKILL.md files for the exact markers so removal fails CI loudly.

This is intentionally a presence-of-marker test, not a behavioral test.
LLM behavior under prompt isn't unit-testable; missing-marker is.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HYGIENE = REPO_ROOT / "skills" / "code-hygiene" / "SKILL.md"
TRACKER = REPO_ROOT / "skills" / "feature-tracker" / "SKILL.md"


@pytest.fixture(scope="module")
def hygiene_text() -> str:
    return HYGIENE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def tracker_text() -> str:
    return TRACKER.read_text(encoding="utf-8")


# --- code-hygiene SKILL.md markers -------------------------------------------

def test_hygiene_has_return_control_section(hygiene_text: str) -> None:
    """Step 5 heading must exist and follow Step 4."""
    assert "## Step 5: Return control to caller" in hygiene_text
    step4_idx = hygiene_text.index("## Step 4")
    step5_idx = hygiene_text.index("## Step 5: Return control to caller")
    assert step4_idx < step5_idx
    rules_idx = hygiene_text.index("## Rules")
    assert step5_idx < rules_idx, "Step 5 must sit between Step 4 and Rules"


def test_hygiene_has_sentinel_string(hygiene_text: str) -> None:
    """The verbatim sentinel line is what the orchestrator scans for."""
    sentinel = (
        "CONTROL RETURNS TO feature-tracker Step 5d.d "
        "— orchestrator must continue, this skill is not the terminal step"
    )
    assert sentinel in hygiene_text


def test_hygiene_result_has_next_action(hygiene_text: str) -> None:
    """The JSON example must include the next_action field."""
    assert '"next_action": "continue_step_5d_d"' in hygiene_text


def test_hygiene_prose_mentions_next_action_required(hygiene_text: str) -> None:
    """Surrounding prose must declare next_action mandatory so a reader of
    the schema knows it's not optional."""
    assert "next_action" in hygiene_text
    # Must appear outside the JSON block too — i.e. at least twice.
    assert hygiene_text.count("next_action") >= 2


# --- feature-tracker SKILL.md markers ----------------------------------------

def test_tracker_step5_has_single_unit_banner(tracker_text: str) -> None:
    """The top-of-Step-5 banner declares the whole step runs as one unit."""
    # Find Step 5 region.
    step5_idx = tracker_text.index("## Step 5:")
    rules_idx = tracker_text.index("\n## Rules", step5_idx)
    step5_block = tracker_text[step5_idx:rules_idx]
    assert "single unit" in step5_block, (
        "Step 5 must contain a banner phrase 'single unit' (or rename the "
        "marker and update this test)"
    )


def test_tracker_5dd_has_do_not_stop_reminder(tracker_text: str) -> None:
    """After 'Hygiene complete. Counter updated.' the orchestrator must be
    told explicitly not to stop."""
    # The reminder must appear somewhere after the 'Counter updated' line.
    counter_idx = tracker_text.index("Counter updated to")
    after = tracker_text[counter_idx:]
    assert "DO NOT STOP" in after, (
        "feature-tracker Step 5d.d must contain a 'DO NOT STOP' continuation "
        "reminder after the 'Counter updated' line"
    )


def test_tracker_brief_block_reaffirms_order(tracker_text: str) -> None:
    """The Print Feature Brief block must reaffirm it prints AFTER hygiene
    (not substituted by hygiene's output)."""
    brief_idx = tracker_text.index("MUST: Print Feature Brief")
    # Look in the brief block + a generous window for the reaffirmation.
    block = tracker_text[brief_idx : brief_idx + 4000]
    # Accept either of the two natural phrasings.
    assert ("after hygiene" in block.lower()) or (
        "follows hygiene" in block.lower()
    ), "Brief block must reaffirm it prints AFTER hygiene's output"
