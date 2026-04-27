"""Regression test for stop-shipping-dev-tools feature.

Maintainer-only tooling (release pipeline + sp-harness's own Python
script regression suite) must NOT be git-tracked. They stay on the
maintainer's working tree but should never land in user plugin
installs via marketplace `source: "./"`. If a future commit
re-introduces any of these paths to git tracking, this test fails.
"""

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

DEV_TOOL_PATH_PREFIXES = [
    # Release-pipeline tooling
    "scripts/bump-version.sh",
    ".version-bump.json",
    ".githooks/",
    # Plugin's own regression test corpora (maintainer-internal)
    "tests/humanize-",
    # Redundant version anchor (canonical version lives in
    # .claude-plugin/plugin.json)
    "package.json",
]


def _git_tracked_files() -> list[str]:
    out = subprocess.check_output(
        ["git", "ls-files"], cwd=REPO_ROOT, text=True
    )
    return [line for line in out.splitlines() if line]


def test_dev_tools_not_tracked() -> None:
    """No git-tracked path may match any of the dev-tool prefixes."""
    tracked = _git_tracked_files()
    offenders = [
        path
        for path in tracked
        for prefix in DEV_TOOL_PATH_PREFIXES
        if path == prefix or path.startswith(prefix)
    ]
    assert offenders == [], (
        "Dev-only tooling returned to git tracking — these paths "
        "must stay untracked so they don't ship to user plugin "
        "installs:\n  " + "\n  ".join(offenders)
    )


def test_dev_tools_still_on_disk() -> None:
    """Untracking must NOT delete the maintainer's local copy. The
    files stay on disk for local use."""
    expected_local_files = [
        "scripts/bump-version.sh",
        ".version-bump.json",
        ".githooks/pre-push",
    ]
    missing = [
        p for p in expected_local_files if not (REPO_ROOT / p).exists()
    ]
    assert missing == [], (
        "Untracking accidentally deleted maintainer-local files:\n  "
        + "\n  ".join(missing)
    )
