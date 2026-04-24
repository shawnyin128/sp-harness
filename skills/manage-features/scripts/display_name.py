"""Deterministic heuristic to derive a short display_name from a description.

Kept standalone (no imports from sibling skill dirs) because each skill
directory is independently distributable in the plugin bundle.
"""
from __future__ import annotations

import re

LEADING_VERBS = frozenset({
    "add", "build", "fix", "write", "create", "update", "implement",
    "refactor", "remove", "support", "make", "author", "introduce",
    "enable", "extend",
})

MAX_LEN = 50
MAX_WORDS = 5

TRAILING_CONNECTORS = frozenset({
    "and", "or", "with", "for", "to", "the", "a", "an", "of", "in",
    "on", "by", "at", "as", "but", "so", "via",
})

_PUNCT_STRIP = " ,.;:-–—"


def _strip_trailing_connectors(s: str) -> str:
    while True:
        s2 = s.rstrip(_PUNCT_STRIP)
        if not s2:
            return s2
        parts = s2.rsplit(None, 1)
        if len(parts) == 2 and parts[1].lower() in TRAILING_CONNECTORS:
            s = parts[0]
            continue
        return s2


def derive_display_name(description: str) -> str:
    if description is None:
        return ""
    s = description.strip()
    s = re.sub(r"[\s\.;:,!?\-–—]+$", "", s)
    if not s:
        return ""

    tokens = s.split(None, 1)
    if len(tokens) == 2 and tokens[0].lower() in LEADING_VERBS:
        stripped = tokens[1].lstrip()
        if stripped:
            s = stripped[:1].upper() + stripped[1:]

    words = s.split()
    if len(words) > MAX_WORDS:
        s = " ".join(words[:MAX_WORDS])

    if len(s) > MAX_LEN:
        cut = s[:MAX_LEN]
        last_space = cut.rfind(" ")
        if last_space > 0:
            cut = cut[:last_space]
        s = cut

    s = _strip_trailing_connectors(s)
    return s or description.strip()[:MAX_LEN]
