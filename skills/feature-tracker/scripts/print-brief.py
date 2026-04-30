#!/usr/bin/env python3
"""Print the canonical Feature Brief for a completed feature.

Reads the archived plan YAML and emits the deterministic brief on stdout.
Replaces the prose-template instruction in feature-tracker SKILL.md Step 5
to eliminate format drift and guarantee the brief actually prints.

Usage:
    print-brief.py <feature-id>
        [--plan-file PATH]      override auto-derived plan path (test-only)
        [--display-name NAME]   override features.json lookup (test-only)
        [--commit HASH]         override `git rev-parse --short HEAD`

Output is English-only by design — see feature-tracker SKILL.md and
docs/plan-file-schema.md for the language-exception rationale.

YAML support is intentionally narrow. The bundled loader handles the
plan-file-schema subset: block mappings (2-space indent), block
sequences with "- " items, "- |" sequence-item literal block scalars,
literal "|" block scalars in mapping values, simple flow sequences
"[a, b]", and identifier-keyed mappings. It does NOT handle: anchors,
aliases, folded scalars (">"), JSON-style flow mappings ("{a: b}"),
multi-doc streams, explicit type tags, or mapping keys that contain
spaces or non-identifier characters. Sequence-item scalars MAY contain
arbitrary punctuation including ": " — the loader uses a strict
identifier-key regex to distinguish "- key: value" mapping items from
plain prose items that merely happen to contain a colon.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Import the centralized id renderer from skills/_lib/.
# This script lives at skills/feature-tracker/scripts/print-brief.py;
# parents[2] is skills/, where _lib/ sits as a sibling package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _lib.format_id import get_display_name  # noqa: E402

# Sequence-item mapping detector: "- <ident>: ..." where <ident> is a
# bare identifier-like key (letters/digits/underscore/hyphen). This
# excludes prose items like "- File rename: collision" because the key
# part contains a space.
_MAPPING_ITEM_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")

# Identifier-style keys that legitimately appear as the head of a
# sequence-item mapping in plan-file-schema.md. Without this gate, any
# bare-identifier prose item like "- Edge: collision case" matches the
# regex above and is misclassified as a mapping, dropping the wrapped
# continuation line and desyncing the indent stack downstream. The set
# is co-located here rather than parsed from the schema doc because the
# schema is Markdown prose, the key set is small, and changes to the
# schema warrant a deliberate edit here anyway. Sources, by section:
#   decisions[]                                 — id, question, planner_view,
#                                                 confidence, rationale,
#                                                 alternatives, ask_user,
#                                                 user_decision
#   decisions[].alternatives[]                  — option, rejected_because
#   unplanned_changes[]                         — loc, what, reason
#   eval.rounds[]                               — round, closure_check,
#                                                 tests, blockers, verdict
#   closure_check.user_decisions_honored[]      — verified, evidence
#   closure_check.confidence_mismatches[]       — step, claimed, actual
#   eval.optimization.suggestions[]             — kind, text
# (id and confidence appear in multiple sections; deduped below.)
_MAPPING_KEYS = frozenset({
    "id", "question", "planner_view", "confidence", "rationale",
    "alternatives", "ask_user", "user_decision",
    "option", "rejected_because",
    "loc", "what", "reason",
    "round", "closure_check", "tests", "blockers", "verdict",
    "verified", "evidence",
    "step", "claimed", "actual",
    "kind", "text",
})


# ---------------------------------------------------------------------------
# Minimal YAML loader (focused on plan-file-schema.md subset)
#
# Supports: block-style mappings (2-space indent), block-style sequences
# (- item), literal block scalars (key: |), flow sequences ([a, b, "c"]),
# scalar autotyping (int, null, true, false, quoted/bare strings). Comments
# (#) and blank lines are stripped.
#
# Does NOT support: anchors, aliases, multi-doc streams, folded scalars (>),
# JSON-style flow mappings ({a: b}), explicit type tags. Plan files don't
# need any of those.
# ---------------------------------------------------------------------------


def load_yaml(text: str):
    raw_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        raw_lines.append((indent, line[indent:]))
    pos = [0]
    return _parse_node(raw_lines, pos, 0)


def _parse_node(lines, pos, indent):
    if pos[0] >= len(lines):
        return None
    cur_indent, content = lines[pos[0]]
    if cur_indent < indent:
        return None
    if content.startswith("- "):
        return _parse_sequence(lines, pos, indent)
    return _parse_mapping(lines, pos, indent)


def _parse_mapping(lines, pos, indent):
    result = {}
    while pos[0] < len(lines):
        cur_indent, content = lines[pos[0]]
        if cur_indent < indent or cur_indent > indent:
            break
        if content.startswith("- "):
            break
        if ":" not in content:
            break
        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()
        pos[0] += 1
        result[key] = _parse_value(lines, pos, indent, rest)
    return result


def _parse_sequence(lines, pos, indent):
    result = []
    while pos[0] < len(lines):
        cur_indent, content = lines[pos[0]]
        if cur_indent != indent or not content.startswith("- "):
            break
        item_content = content[2:]
        pos[0] += 1
        if item_content == "|":
            # Literal block scalar as a sequence item: "- |" followed by
            # indented block content.
            result.append(_parse_block_scalar(lines, pos, indent))
        elif (
            (m := _MAPPING_ITEM_RE.match(item_content))
            and m.group(1) in _MAPPING_KEYS
            and not _looks_like_quoted(item_content)
        ):
            # Mapping item — first kv inline, rest at indent+2 (column where "- " ended).
            child_indent = indent + 2
            item = {}
            key = m.group(1)
            rest = m.group(2).strip()
            item[key] = _parse_value(lines, pos, child_indent, rest)
            while pos[0] < len(lines):
                ci, cc = lines[pos[0]]
                if ci != child_indent or cc.startswith("- "):
                    break
                kv = _MAPPING_ITEM_RE.match(cc)
                if not kv:
                    break
                pos[0] += 1
                item[kv.group(1)] = _parse_value(lines, pos, child_indent, kv.group(2).strip())
            result.append(item)
        else:
            # Plain scalar item. Consume continuation lines (indent > the
            # item indent and not a new sibling). Authors writing wrapped
            # YAML by hand or by LLM commonly produce this shape:
            #   - first line of the item
            #     continuation of the same item
            scalar_parts = [item_content]
            while pos[0] < len(lines):
                ci, cc = lines[pos[0]]
                if ci <= indent:
                    break
                if cc.startswith("- "):
                    break
                pos[0] += 1
                scalar_parts.append(cc.strip())
            result.append(_parse_scalar(" ".join(scalar_parts)))
    return result


def _parse_value(lines, pos, parent_indent, rest):
    if rest == "":
        nested = _parse_node(lines, pos, parent_indent + 2)
        return nested if nested is not None else {}
    if rest == "|":
        return _parse_block_scalar(lines, pos, parent_indent)
    if rest.startswith("[") and rest.endswith("]"):
        return _parse_flow_seq(rest)
    return _parse_scalar(rest)


def _parse_block_scalar(lines, pos, parent_indent):
    block_indent = parent_indent + 2
    parts = []
    while pos[0] < len(lines):
        ci, cc = lines[pos[0]]
        if ci < block_indent:
            break
        prefix = " " * (ci - block_indent)
        parts.append(prefix + cc)
        pos[0] += 1
    return "\n".join(parts)


def _parse_flow_seq(text):
    inner = text[1:-1].strip()
    if not inner:
        return []
    return [_parse_scalar(x.strip()) for x in inner.split(",")]


def _parse_scalar(text):
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    if len(text) >= 2 and text[0] == "'" and text[-1] == "'":
        return text[1:-1]
    if text == "null":
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    return text


def _looks_like_quoted(text):
    # crude guard so '"foo: bar"' as a sequence item isn't treated as mapping
    return text.startswith('"') or text.startswith("'")


# ---------------------------------------------------------------------------
# Brief generator
# ---------------------------------------------------------------------------


SEPARATOR = "─────────────────────────────────────────────────────────"


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def collapse_whitespace(text: str) -> str:
    return " ".join(text.split())


def build_brief(plan: dict, display_name: str, feature_id: str, commit: str) -> str:
    problem_raw = plan.get("problem")
    problem = collapse_whitespace(problem_raw) if problem_raw else "—"

    steps = plan.get("steps") or []
    n_steps = len(steps)

    files: set[str] = set()
    for step in steps:
        files_block = step.get("files") or {}
        for path in (files_block.get("modify") or []):
            files.add(path)
        for path in (files_block.get("create") or []):
            files.add(path)
    for change in (plan.get("unplanned_changes") or []):
        loc = change.get("loc")
        if loc:
            files.add(loc)

    execution = plan.get("execution") or {}
    seen_commits: list[str] = []
    for exec_data in execution.values():
        if not isinstance(exec_data, dict):
            continue
        for c in (exec_data.get("commits") or []):
            if c == "pending":  # placeholder before sed substitution; ignore
                continue
            if c not in seen_commits:
                seen_commits.append(c)
    n_commits = len(seen_commits)

    eval_data = plan.get("eval") or {}
    rounds = eval_data.get("rounds") or []
    n_rounds = len(rounds)
    pass_round: str = "—"
    n_tests = 0
    coverage_avg_str = "—"
    if rounds:
        for r in rounds:
            if r.get("verdict") == "PASS":
                pr = r.get("round")
                pass_round = str(pr) if pr is not None else "—"
                break
        last = rounds[-1] or {}
        tests = last.get("tests") or {}
        total_pass = 0
        total_fail = 0
        coverages = []
        for t in tests.values():
            if not isinstance(t, dict):
                continue
            p = t.get("pass") or 0
            f = t.get("fail") or 0
            total_pass += p
            total_fail += f
            cov = t.get("coverage")
            if cov is not None:
                coverages.append(cov)
        n_tests = total_pass + total_fail
        if coverages:
            avg = sum(coverages) / len(coverages)
            coverage_avg_str = f"{round(avg, 1):g}"

    suggestions = ((eval_data.get("optimization") or {}).get("suggestions")) or []
    n_followups = len(suggestions)

    files_str = ", ".join(sorted(files)) if files else "—"
    followups_str = plural(n_followups, "suggestion") if n_followups else "—"

    lines = [
        f'─── Feature complete: "{display_name}" ({feature_id}) ───',
        f"**What:**      {problem}",
        f"**Steps:**     {plural(n_steps, 'step')} · {plural(n_commits, 'commit')}",
        f"**Files:**     {files_str}",
        f"**Tests:**     {plural(n_tests, 'test')} · avg {coverage_avg_str}% coverage",
        f"**Rounds:**    {n_rounds} (PASS in round {pass_round})",
        f"**Followups:** {followups_str}",
        f"**Commit:**    {commit}",
        SEPARATOR,
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def derive_plan_path(feature_id: str) -> Path:
    return (
        Path(".claude")
        / "agents"
        / "state"
        / "archive"
        / feature_id
        / f"{feature_id}.plan.yaml"
    )


def lookup_display_name(feature_id: str) -> str:
    """Resolve display_name via the centralized _lib.format_id helper.

    Raises ValueError if the feature is missing or has empty display_name —
    no fallback to bare id. The schema invariant (display_name required and
    non-empty) is enforced by mutate.py and backfill scripts, so a real
    failure here means an upstream bug worth seeing.
    """
    return get_display_name(feature_id, "feature")


def lookup_commit_hash() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return "—"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("feature_id")
    parser.add_argument("--plan-file", type=Path, default=None)
    parser.add_argument("--display-name", default=None)
    parser.add_argument("--commit", default=None)
    args = parser.parse_args()

    plan_path = args.plan_file or derive_plan_path(args.feature_id)
    if not plan_path.exists():
        print(f"plan file not found: {plan_path}", file=sys.stderr)
        return 1

    plan = load_yaml(plan_path.read_text())
    if not isinstance(plan, dict):
        print(f"plan file is not a mapping: {plan_path}", file=sys.stderr)
        return 1

    display_name = args.display_name or lookup_display_name(args.feature_id)
    commit = args.commit or lookup_commit_hash()

    sys.stdout.write(build_brief(plan, display_name, args.feature_id, commit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
