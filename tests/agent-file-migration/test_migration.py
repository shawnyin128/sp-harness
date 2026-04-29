"""Agent-file-migration test (feature: role-skills-test-suite-update, S2).

Two layers, both static (no live skill execution):

* **Layer A — structural assertions** on
  ``skills/switch-dev-mode/SKILL.md`` re-confirm that the cleanup
  section enumerates all four stale per-project agent filenames
  and that the decision-touchpoint-protocol marker is preserved.
  Overlap with ``tests/switch-dev-mode-migration-rewrite/`` is
  intentional: kept narrow so a future SKILL rewrite cannot
  silently shrink the cleanup target list.

* **Layer B — behavior simulation** on a tmpdir fixture. A small
  Python helper mirrors the cleanup algorithm documented in the
  SKILL (read sp-harness.json, glob the four exact filenames,
  delete those that exist, flip dev_mode preserving every other
  field). The simulator lives in this test file, NOT in
  production code — its job is to codify the contract so a
  future re-implementation can be diffed against it.

  Layer B's post-state assertions:
    1. The four stale agent files are gone.
    2. ``.claude/agents/state/`` is preserved untouched.
    3. Unrelated ``.claude/agents/sp-other.md`` decoy is preserved.
    4. ``.claude/sp-harness.json`` has dev_mode flipped, every
       other field byte-identical to the seed.
    5. Edge: empty stale set → simulator is a no-op, JSON
       byte-identical (modulo dev_mode flip).
    6. Edge: only some stale files exist → simulator deletes only
       those, no FileNotFoundError, others left as-is.
"""
from __future__ import annotations

import json
import pathlib
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "switch-dev-mode" / "SKILL.md"

# The four exact filenames the SKILL enumerates as cleanup targets.
STALE_FILENAMES = (
    "sp-planner.md",
    "sp-generator.md",
    "sp-evaluator.md",
    "sp-feedback.md",
)


# ---------------------------------------------------------------------------
# Layer A — structural assertions on the SKILL.md prose
# ---------------------------------------------------------------------------


class TestSwitchDevModeSkillPreservesCleanupContract(unittest.TestCase):
    """Lock the SKILL.md surface so a future rewrite cannot drop a
    cleanup target, drop the dev_mode toggle, or drop the
    decision-touchpoint-protocol marker."""

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text(encoding="utf-8")

    def test_all_four_stale_filenames_enumerated(self):
        for fname in STALE_FILENAMES:
            self.assertIn(
                f".claude/agents/{fname}",
                self.text,
                f"switch-dev-mode SKILL.md no longer enumerates "
                f"{fname} as a cleanup target",
            )

    def test_dev_mode_field_referenced(self):
        self.assertIn("dev_mode", self.text)

    def test_sp_harness_json_path_referenced(self):
        self.assertIn(".claude/sp-harness.json", self.text)

    def test_decision_touchpoint_protocol_marker_present(self):
        self.assertIn(
            "decision-touchpoint-protocol",
            self.text,
            "switch-dev-mode SKILL.md missing the canonical "
            "decision-touchpoint-protocol marker (framework-check Cat 9)",
        )

    def test_state_subdirectory_marked_off_limits(self):
        # The SKILL must NOT recurse into .claude/agents/state/. The
        # current prose says so explicitly; lock that semantics.
        self.assertIn("state/", self.text)


# ---------------------------------------------------------------------------
# Layer B — behavior simulation against a tmpdir fixture
# ---------------------------------------------------------------------------


def _seed_project(root: pathlib.Path, *,
                  initial_mode: str = "single-agent",
                  stale_files: tuple[str, ...] = STALE_FILENAMES,
                  extra_json_fields: dict | None = None) -> dict:
    """Seed ``root`` with a project layout that mirrors a real
    sp-harness project enough for the cleanup simulator to run.

    Returns the JSON dict that was written, for diffing later.
    """
    if extra_json_fields is None:
        extra_json_fields = {
            "last_hygiene_at_completed": 7,
            "external_codebase": False,
            "language": "match-input",
        }
    config = {"dev_mode": initial_mode, **extra_json_fields}

    claude_dir = root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "sp-harness.json").write_text(
        json.dumps(config, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    agents_dir = claude_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    for fname in stale_files:
        (agents_dir / fname).write_text(
            f"# stub for {fname} (pre-role-skill residue)\n",
            encoding="utf-8",
        )

    # Decoy 1: state/ subdirectory must be preserved (skill must NOT
    # recurse into it).
    state_dir = agents_dir / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "active-placeholder.txt").write_text(
        "active state placeholder\n", encoding="utf-8"
    )

    # Decoy 2: an unrelated agent file that the cleanup MUST NOT touch.
    (agents_dir / "sp-other.md").write_text(
        "# unrelated custom agent\n", encoding="utf-8"
    )
    return config


def _simulate_cleanup(root: pathlib.Path) -> tuple[int, str]:
    """Mirror the cleanup algorithm documented in the SKILL.

    Steps, in order:
      1. Read ``.claude/sp-harness.json``.
      2. Compute ``other_mode`` as the opposite of the current
         ``dev_mode`` value (single-agent <-> three-agent).
      3. Glob the four exact filenames under ``.claude/agents/``,
         deleting those that exist. Do NOT recurse.
      4. Re-write ``.claude/sp-harness.json`` with ``dev_mode``
         set to ``other_mode``, preserving every other field
         byte-identical (key order included).

    Returns ``(num_deleted, other_mode)``.
    """
    config_path = root / ".claude" / "sp-harness.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    current_mode = config.get("dev_mode", "single-agent")
    other_mode = (
        "three-agent" if current_mode == "single-agent" else "single-agent"
    )

    agents_dir = root / ".claude" / "agents"
    deleted = 0
    for fname in STALE_FILENAMES:
        target = agents_dir / fname
        if target.exists():
            target.unlink()
            deleted += 1

    # Preserve key order: rebuild dict by walking original keys.
    new_config = {
        k: (other_mode if k == "dev_mode" else v) for k, v in config.items()
    }
    config_path.write_text(
        json.dumps(new_config, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return deleted, other_mode


class TestCleanupSimulatorAllFourStaleFiles(unittest.TestCase):
    """Happy path: all four stale files exist; simulator removes
    every one of them and flips dev_mode."""

    def test_post_state_matches_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            seed = _seed_project(root, initial_mode="single-agent")

            deleted, other_mode = _simulate_cleanup(root)

            self.assertEqual(deleted, 4)
            self.assertEqual(other_mode, "three-agent")

            # Stale files gone.
            for fname in STALE_FILENAMES:
                self.assertFalse(
                    (root / ".claude" / "agents" / fname).exists(),
                    f"{fname} should have been deleted",
                )

            # Decoys preserved.
            self.assertTrue(
                (root / ".claude" / "agents" / "state" /
                 "active-placeholder.txt").exists(),
                "state/ subtree must be preserved",
            )
            self.assertTrue(
                (root / ".claude" / "agents" / "sp-other.md").exists(),
                "unrelated sp-other.md must be preserved",
            )

            # JSON: dev_mode flipped, every other field byte-identical.
            after = json.loads(
                (root / ".claude" / "sp-harness.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(after["dev_mode"], "three-agent")
            for k, v in seed.items():
                if k == "dev_mode":
                    continue
                self.assertEqual(
                    after[k], v,
                    f"unrelated field {k!r} was mutated by cleanup",
                )
            # Same key set (no fields added or removed).
            self.assertEqual(set(after.keys()), set(seed.keys()))


class TestCleanupSimulatorEmptyStaleSet(unittest.TestCase):
    """Edge: no stale files present. Cleanup is a no-op for the
    filesystem, but dev_mode still flips per the contract."""

    def test_empty_set_is_filesystem_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _seed_project(
                root, initial_mode="three-agent", stale_files=()
            )

            deleted, other_mode = _simulate_cleanup(root)

            self.assertEqual(deleted, 0)
            self.assertEqual(other_mode, "single-agent")
            self.assertTrue(
                (root / ".claude" / "agents" / "state" /
                 "active-placeholder.txt").exists()
            )
            self.assertTrue(
                (root / ".claude" / "agents" / "sp-other.md").exists()
            )


class TestCleanupSimulatorPartialStaleSet(unittest.TestCase):
    """Edge: only some of the four files exist; simulator deletes
    only those, no FileNotFoundError, others left as-is."""

    def test_partial_set_deletes_only_existing(self):
        partial = ("sp-planner.md", "sp-feedback.md")
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            _seed_project(
                root, initial_mode="single-agent", stale_files=partial
            )

            deleted, _ = _simulate_cleanup(root)

            self.assertEqual(deleted, 2)
            # Deleted ones gone, never-existed ones still don't exist.
            for fname in STALE_FILENAMES:
                self.assertFalse(
                    (root / ".claude" / "agents" / fname).exists(),
                    f"{fname} unexpectedly present after cleanup",
                )
            # Decoys preserved.
            self.assertTrue(
                (root / ".claude" / "agents" / "sp-other.md").exists()
            )


class TestCleanupSimulatorPreservesJsonKeyOrder(unittest.TestCase):
    """The SKILL says dev_mode is the only field touched. The
    simulator must preserve the original key insertion order so
    diff tools see a single-line change."""

    def test_key_order_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            extra = {
                "alpha": 1,
                "beta": [1, 2, 3],
                "gamma": {"nested": True},
                "language": "zh",
            }
            _seed_project(
                root, initial_mode="single-agent",
                extra_json_fields=extra,
            )

            _simulate_cleanup(root)

            after_text = (root / ".claude" / "sp-harness.json").read_text(
                encoding="utf-8"
            )
            after = json.loads(after_text)
            self.assertEqual(
                list(after.keys()),
                ["dev_mode", "alpha", "beta", "gamma", "language"],
                "JSON key order changed by cleanup simulator",
            )


if __name__ == "__main__":
    unittest.main()
