"""Shared version-frontmatter assertion for SKILL.md regression tests.

Each feature that bumps a SKILL's version baseline asserts ">= baseline"
rather than "== baseline" so subsequent features bumping the same skill
don't break the prior feature's regression test.
"""

import re

_VERSION_RE_TEMPLATE = r"^version: {major}\.(\d+)\.(\d+)$"


def assert_min_version(text: str, major: int, min_minor: int, file_label: str) -> None:
    """Assert frontmatter declares `version: <major>.<minor>.<patch>` with
    `minor >= min_minor`. Exact patch level is not constrained.
    """
    m = re.search(_VERSION_RE_TEMPLATE.format(major=major), text, re.MULTILINE)
    assert m, f"{file_label} must declare 'version: {major}.x.y' in frontmatter"
    minor = int(m.group(1))
    assert minor >= min_minor, (
        f"{file_label} version must be >= {major}.{min_minor}.0 "
        f"(version-bump baseline); found {major}.{minor}.{m.group(2)}"
    )
