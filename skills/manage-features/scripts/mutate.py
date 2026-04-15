#!/usr/bin/env python3
"""
Mutate .claude/features.json via structured operations.

Usage:
  mutate.py add --id=<id> --category=<c> --priority=<p> \\
            --description=<d> --steps=<s1>;;<s2>;;<s3> \\
            [--depends-on=<a>,<b>] [--from-todo=<todo-id>]
  mutate.py mark-passing <id>
  mutate.py update <id> [--description=<d>] [--priority=<p>] \\
            [--steps=<s1>;;<s2>] [--depends-on=<a>,<b>]

Validates schema on every write. Rejects dangling depends_on refs and
circular dependencies.

Note: steps use `;;` as separator (not `;` — too common in shell). Empty
entries stripped.
"""
import argparse
import json
import sys
from pathlib import Path

FEATURES_PATH = Path(".claude/features.json")
TODOS_PATH = Path(".claude/todos.json")
VALID_CATEGORIES = {"functional", "ui", "infrastructure", "testing"}
VALID_PRIORITIES = {"high", "medium", "low"}


def load_features():
    if not FEATURES_PATH.exists():
        return {"features": []}
    try:
        return json.loads(FEATURES_PATH.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"error: {FEATURES_PATH} is not valid JSON: {e}")


def save_features(data):
    FEATURES_PATH.parent.mkdir(parents=True, exist_ok=True)
    FEATURES_PATH.write_text(json.dumps(data, indent=2) + "\n")


def load_todo_ids():
    if not TODOS_PATH.exists():
        return set()
    try:
        data = json.loads(TODOS_PATH.read_text())
        return {t["id"] for t in data.get("todos", [])}
    except json.JSONDecodeError:
        return set()


def parse_steps(raw):
    if not raw:
        return []
    parts = raw.split(";;")
    return [p.strip() for p in parts if p.strip()]


def parse_list(raw):
    if not raw:
        return []
    return [p.strip() for p in raw.split(",") if p.strip()]


def find_feature(data, fid):
    for i, f in enumerate(data["features"]):
        if f.get("id") == fid:
            return i, f
    return None, None


def check_circular(features, new_feature):
    """Check adding/modifying a feature doesn't create a cycle."""
    # Build graph including the new/modified feature
    all_features = [f for f in features if f.get("id") != new_feature.get("id")] + [new_feature]
    by_id = {f["id"]: f for f in all_features}

    def has_cycle_from(fid, visited, path):
        if fid in path:
            return path[path.index(fid):] + [fid]
        if fid in visited:
            return None
        path = path + [fid]
        for dep in by_id.get(fid, {}).get("depends_on") or []:
            if dep in by_id:
                cycle = has_cycle_from(dep, visited, path)
                if cycle:
                    return cycle
        visited.add(fid)
        return None

    visited = set()
    for fid in list(by_id.keys()):
        cycle = has_cycle_from(fid, visited, [])
        if cycle:
            return cycle
    return None


def op_add(args):
    data = load_features()
    existing_ids = {f["id"] for f in data["features"]}

    if args.id in existing_ids:
        sys.exit(f"error: feature id '{args.id}' already exists")

    if args.category not in VALID_CATEGORIES:
        sys.exit(f"error: category must be one of {sorted(VALID_CATEGORIES)}")

    if args.priority not in VALID_PRIORITIES:
        sys.exit(f"error: priority must be one of {sorted(VALID_PRIORITIES)}")

    depends_on = parse_list(args.depends_on) if args.depends_on else []
    # Validate depends_on
    for dep in depends_on:
        if dep not in existing_ids:
            sys.exit(f"error: depends_on references missing feature '{dep}'")

    steps = parse_steps(args.steps)
    if not steps:
        sys.exit("error: at least one step required (use ;; as separator)")

    from_todo = args.from_todo
    if from_todo:
        todo_ids = load_todo_ids()
        if todo_ids and from_todo not in todo_ids:
            sys.exit(f"error: from_todo references missing todo '{from_todo}'")

    new_feature = {
        "id": args.id,
        "category": args.category,
        "priority": args.priority,
        "depends_on": depends_on,
        "from_todo": from_todo,
        "description": args.description,
        "steps": steps,
        "passes": False,
    }

    cycle = check_circular(data["features"], new_feature)
    if cycle:
        sys.exit(f"error: adding '{args.id}' would create a cycle: {' → '.join(cycle)}")

    data["features"].append(new_feature)
    save_features(data)
    print(json.dumps({"created": args.id}, indent=2))


def op_mark_passing(args):
    data = load_features()
    _, feature = find_feature(data, args.id)
    if feature is None:
        sys.exit(f"error: feature '{args.id}' not found")
    if feature.get("passes"):
        print(json.dumps({"id": args.id, "already_passing": True}, indent=2))
        return
    feature["passes"] = True
    save_features(data)
    print(json.dumps({"id": args.id, "passes": True}, indent=2))


def op_update(args):
    data = load_features()
    _, feature = find_feature(data, args.id)
    if feature is None:
        sys.exit(f"error: feature '{args.id}' not found")

    updates = {}

    if args.description is not None:
        feature["description"] = args.description
        updates["description"] = True

    if args.priority is not None:
        if args.priority not in VALID_PRIORITIES:
            sys.exit(f"error: priority must be one of {sorted(VALID_PRIORITIES)}")
        feature["priority"] = args.priority
        updates["priority"] = True

    if args.steps is not None:
        steps = parse_steps(args.steps)
        if not steps:
            sys.exit("error: at least one step required")
        feature["steps"] = steps
        updates["steps"] = True

    if args.depends_on is not None:
        deps = parse_list(args.depends_on)
        existing_ids = {f["id"] for f in data["features"]}
        for dep in deps:
            if dep not in existing_ids:
                sys.exit(f"error: depends_on references missing feature '{dep}'")
        feature["depends_on"] = deps
        cycle = check_circular(data["features"], feature)
        if cycle:
            sys.exit(f"error: depends_on update would create cycle: {' → '.join(cycle)}")
        updates["depends_on"] = True

    if not updates:
        sys.exit("error: provide at least one field to update")

    save_features(data)
    print(json.dumps({"id": args.id, "updated": sorted(updates.keys())}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="op", required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("--id", required=True)
    p_add.add_argument("--category", required=True, choices=sorted(VALID_CATEGORIES))
    p_add.add_argument("--priority", required=True, choices=sorted(VALID_PRIORITIES))
    p_add.add_argument("--description", required=True)
    p_add.add_argument("--steps", required=True, help="Steps separated by `;;`")
    p_add.add_argument("--depends-on", help="Comma-separated list")
    p_add.add_argument("--from-todo")
    p_add.set_defaults(func=op_add)

    p_mark = sub.add_parser("mark-passing")
    p_mark.add_argument("id")
    p_mark.set_defaults(func=op_mark_passing)

    p_update = sub.add_parser("update")
    p_update.add_argument("id")
    p_update.add_argument("--description")
    p_update.add_argument("--priority", choices=sorted(VALID_PRIORITIES))
    p_update.add_argument("--steps")
    p_update.add_argument("--depends-on")
    p_update.set_defaults(func=op_update)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
