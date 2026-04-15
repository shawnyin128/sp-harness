#!/usr/bin/env python3
"""
Read-only queries against .claude/features.json.

Usage:
  query.py list [--passes=true|false|all] [--format=json|table]
  query.py get <id>
  query.py next [--format=json|table]
  query.py deps <id>
  query.py stats
  query.py validate

`next` returns the feature that feature-tracker should pick next:
topological (depends_on satisfied) filter first, then priority
(high→medium→low), then array order tiebreaker.

Exits non-zero with structured error if:
- all remaining features have unsatisfied deps (deadlock)
- dangling depends_on refs found
- circular deps detected
"""
import argparse
import json
import sys
from pathlib import Path

FEATURES_PATH = Path(".claude/features.json")
PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


def load():
    if not FEATURES_PATH.exists():
        return {"features": []}
    try:
        return json.loads(FEATURES_PATH.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"error: {FEATURES_PATH} is not valid JSON: {e}")


def deps_satisfied(feature, by_id):
    for dep_id in feature.get("depends_on", []):
        dep = by_id.get(dep_id)
        if dep is None:
            return False  # missing dep = unsatisfiable
        if not dep.get("passes"):
            return False
    return True


def find_next(features):
    """Topological + priority selection."""
    by_id = {f["id"]: f for f in features}
    candidates = [f for f in features if not f.get("passes") and deps_satisfied(f, by_id)]
    if not candidates:
        unfinished = [f for f in features if not f.get("passes")]
        if unfinished:
            # deadlock
            deadlock = []
            for f in unfinished:
                unmet = [
                    d
                    for d in f.get("depends_on", [])
                    if d not in by_id or not by_id[d].get("passes")
                ]
                deadlock.append({"id": f["id"], "blocked_by": unmet})
            return None, {"deadlock": True, "blocked_features": deadlock}
        return None, {"all_done": True}
    # Sort by priority rank, then array order (stable sort preserves original)
    # Need to track original index for stable tiebreaker
    indexed = list(enumerate(features))
    ranked = [
        (PRIORITY_RANK.get(f.get("priority", "medium"), 1), i, f)
        for i, f in indexed
        if f in candidates
    ]
    ranked.sort(key=lambda x: (x[0], x[1]))
    return ranked[0][2], None


def format_feature_table(f):
    deps = ", ".join(f.get("depends_on") or []) or "none"
    from_todo = f.get("from_todo") or "(none)"
    steps_list = f.get("steps") or []
    steps_str = "\n".join(f"  {i+1}. {s}" for i, s in enumerate(steps_list))
    return (
        f"Id: {f['id']}\n"
        f"Description: {f.get('description', '')}\n"
        f"Category: {f.get('category', '')}\n"
        f"Priority: {f.get('priority', '')}\n"
        f"Depends on: {deps}\n"
        f"From todo: {from_todo}\n"
        f"Passes: {f.get('passes', False)}\n"
        f"Steps:\n{steps_str}"
    )


def format_list_table(features):
    if not features:
        return "(no matching features)"
    lines = []
    for f in features:
        mark = "✓" if f.get("passes") else "·"
        deps = len(f.get("depends_on") or [])
        dep_str = f" (deps:{deps})" if deps else ""
        lines.append(
            f"{mark} [{f.get('priority', '?')}] {f['id']}{dep_str}\n  {f.get('description', '')}"
        )
    return "\n".join(lines)


def validate(features):
    errors = []
    warnings = []
    ids = [f.get("id") for f in features]

    # Duplicate ids
    seen = set()
    for fid in ids:
        if fid in seen:
            errors.append(f"duplicate id: {fid}")
        seen.add(fid)

    # Dangling depends_on
    id_set = set(ids)
    for f in features:
        for dep in f.get("depends_on") or []:
            if dep not in id_set:
                errors.append(f"{f['id']}: depends_on references missing id '{dep}'")

    # Circular deps (topological sort attempt)
    by_id = {f["id"]: f for f in features}
    visited = {}  # id → 'visiting' or 'done'

    def dfs(fid, path):
        if visited.get(fid) == "done":
            return
        if visited.get(fid) == "visiting":
            cycle = path[path.index(fid):] + [fid]
            errors.append(f"circular dependency: {' → '.join(cycle)}")
            return
        visited[fid] = "visiting"
        for dep in by_id.get(fid, {}).get("depends_on") or []:
            if dep in by_id:
                dfs(dep, path + [fid])
        visited[fid] = "done"

    for fid in ids:
        if fid:
            dfs(fid, [])

    # Required fields
    required = {"id", "category", "priority", "description", "steps", "passes"}
    for f in features:
        missing = required - set(f.keys())
        if missing:
            errors.append(f"{f.get('id', '?')}: missing fields {sorted(missing)}")

    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="op", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--passes", choices=["true", "false", "all"], default="all")
    p_list.add_argument("--format", choices=["json", "table"], default="table")

    p_get = sub.add_parser("get")
    p_get.add_argument("id")
    p_get.add_argument("--format", choices=["json", "table"], default="json")

    p_next = sub.add_parser("next")
    p_next.add_argument("--format", choices=["json", "table"], default="table")

    p_deps = sub.add_parser("deps")
    p_deps.add_argument("id")

    sub.add_parser("stats")
    sub.add_parser("validate")

    args = parser.parse_args()
    data = load()
    features = data.get("features", [])

    if args.op == "list":
        if args.passes == "true":
            filtered = [f for f in features if f.get("passes")]
        elif args.passes == "false":
            filtered = [f for f in features if not f.get("passes")]
        else:
            filtered = features
        if args.format == "json":
            print(json.dumps(filtered, indent=2))
        else:
            print(format_list_table(filtered))
            print(f"\n({len(filtered)} total)")

    elif args.op == "get":
        for f in features:
            if f.get("id") == args.id:
                if args.format == "json":
                    print(json.dumps(f, indent=2))
                else:
                    print(format_feature_table(f))
                return
        sys.exit(f"error: feature '{args.id}' not found")

    elif args.op == "next":
        chosen, err = find_next(features)
        if err:
            print(json.dumps(err, indent=2))
            sys.exit(1 if err.get("deadlock") else 0)
        if args.format == "json":
            print(json.dumps(chosen, indent=2))
        else:
            print(format_feature_table(chosen))

    elif args.op == "deps":
        by_id = {f["id"]: f for f in features}
        target = by_id.get(args.id)
        if target is None:
            sys.exit(f"error: feature '{args.id}' not found")
        deps = target.get("depends_on") or []
        if not deps:
            print(json.dumps({"id": args.id, "depends_on": [], "blocked": False}, indent=2))
            return
        status = []
        for dep_id in deps:
            dep = by_id.get(dep_id)
            status.append(
                {
                    "id": dep_id,
                    "exists": dep is not None,
                    "passes": bool(dep and dep.get("passes")),
                }
            )
        blocked = any(not s["passes"] for s in status)
        print(
            json.dumps(
                {"id": args.id, "depends_on": status, "blocked": blocked}, indent=2
            )
        )

    elif args.op == "stats":
        total = len(features)
        passed = sum(1 for f in features if f.get("passes"))
        remaining = total - passed
        by_priority = {"high": 0, "medium": 0, "low": 0}
        for f in features:
            if not f.get("passes"):
                by_priority[f.get("priority", "medium")] = by_priority.get(f.get("priority", "medium"), 0) + 1
        print(
            json.dumps(
                {
                    "total": total,
                    "passed": passed,
                    "remaining": remaining,
                    "remaining_by_priority": by_priority,
                },
                indent=2,
            )
        )

    elif args.op == "validate":
        errors, warnings = validate(features)
        print(json.dumps({"errors": errors, "warnings": warnings, "valid": not errors}, indent=2))
        if errors:
            sys.exit(1)


if __name__ == "__main__":
    main()
