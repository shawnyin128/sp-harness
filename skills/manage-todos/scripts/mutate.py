#!/usr/bin/env python3
"""
Mutate .claude/todos.json via structured operations.

Usage:
  mutate.py add <description> --category=<c> [--notes=<n>]
  mutate.py mark-in-brainstorm <id>
  mutate.py link-features <id> <feature_id> [<feature_id> ...]
  mutate.py check-done <id>
  mutate.py drop <id> --reason=<r>
  mutate.py update <id> [--description=<d>] [--category=<c>] [--notes=<n>]

All ops validate the schema and state machine. Invalid transitions exit
non-zero with an error message.

check-done reads .claude/features.json. If ALL linked features have
passes:true, transitions todo to done, sets archived_feature_paths, and
returns {"done": true}. Otherwise returns {"done": false, "remaining": [...]}.

Valid state transitions:
  pending → in_brainstorm | dropped
  in_brainstorm → in_feature | pending (re-plan) | dropped
  in_feature → done (auto via check-done) | in_brainstorm (re-plan) | dropped
  done → (terminal)
  dropped → (terminal)
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

TODOS_PATH = Path(".claude/todos.json")
FEATURES_PATH = Path(".claude/features.json")
VALID_STATUSES = {"pending", "in_brainstorm", "in_feature", "done", "dropped"}
VALID_CATEGORIES = {"feature-idea", "tech-debt", "investigation", "ux-improvement"}

TRANSITIONS = {
    "pending": {"in_brainstorm", "dropped"},
    "in_brainstorm": {"in_feature", "pending", "dropped"},
    "in_feature": {"done", "in_brainstorm", "dropped"},
    "done": set(),
    "dropped": set(),
}


def load_todos():
    if not TODOS_PATH.exists():
        return {"todos": []}
    try:
        return json.loads(TODOS_PATH.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"error: {TODOS_PATH} is not valid JSON: {e}")


def save_todos(data):
    TODOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TODOS_PATH.write_text(json.dumps(data, indent=2) + "\n")


def load_features():
    if not FEATURES_PATH.exists():
        return {"features": []}
    try:
        return json.loads(FEATURES_PATH.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"error: {FEATURES_PATH} is not valid JSON: {e}")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def slugify(text):
    """Turn description into kebab-case id."""
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    # Cap length
    if len(s) > 60:
        s = s[:60].rstrip("-")
    return s or "todo"


def unique_id(base, existing_ids):
    if base not in existing_ids:
        return base
    n = 2
    while f"{base}-{n}" in existing_ids:
        n += 1
    return f"{base}-{n}"


def find_todo(data, todo_id):
    for i, t in enumerate(data["todos"]):
        if t.get("id") == todo_id:
            return i, t
    return None, None


def transition(todo, new_status):
    current = todo.get("status", "pending")
    if new_status == current:
        return  # no-op
    allowed = TRANSITIONS.get(current, set())
    if new_status not in allowed:
        sys.exit(
            f"error: invalid transition {current} → {new_status} for '{todo['id']}'. "
            f"Allowed from {current}: {sorted(allowed) or '(none, terminal state)'}"
        )
    todo["status"] = new_status


def op_add(args):
    data = load_todos()
    existing_ids = {t["id"] for t in data["todos"]}
    if args.category not in VALID_CATEGORIES:
        sys.exit(f"error: category must be one of {sorted(VALID_CATEGORIES)}")
    todo = {
        "id": unique_id(slugify(args.description), existing_ids),
        "description": args.description,
        "category": args.category,
        "status": "pending",
        "notes": args.notes or "",
        "created_at": now_iso(),
        "linked_feature_ids": [],
        "archived_feature_paths": [],
    }
    data["todos"].append(todo)
    save_todos(data)
    print(json.dumps({"created": todo["id"]}, indent=2))


def op_mark_in_brainstorm(args):
    data = load_todos()
    _, todo = find_todo(data, args.id)
    if todo is None:
        sys.exit(f"error: todo '{args.id}' not found")
    transition(todo, "in_brainstorm")
    save_todos(data)
    print(json.dumps({"id": todo["id"], "status": todo["status"]}, indent=2))


def op_link_features(args):
    data = load_todos()
    _, todo = find_todo(data, args.id)
    if todo is None:
        sys.exit(f"error: todo '{args.id}' not found")
    existing = set(todo.get("linked_feature_ids", []))
    added = [f for f in args.feature_ids if f not in existing]
    todo["linked_feature_ids"] = sorted(existing | set(args.feature_ids))
    # Auto-transition in_brainstorm → in_feature
    if todo.get("status") == "in_brainstorm":
        transition(todo, "in_feature")
    save_todos(data)
    print(
        json.dumps(
            {
                "id": todo["id"],
                "linked_feature_ids": todo["linked_feature_ids"],
                "status": todo["status"],
                "added": added,
            },
            indent=2,
        )
    )


def op_check_done(args):
    data = load_todos()
    _, todo = find_todo(data, args.id)
    if todo is None:
        sys.exit(f"error: todo '{args.id}' not found")

    linked = todo.get("linked_feature_ids", [])
    if not linked:
        print(json.dumps({"done": False, "reason": "no linked features"}, indent=2))
        return

    features = load_features()
    by_id = {f["id"]: f for f in features.get("features", [])}
    remaining = []
    missing = []
    for fid in linked:
        if fid not in by_id:
            missing.append(fid)
        elif not by_id[fid].get("passes"):
            remaining.append(fid)

    if missing:
        print(
            json.dumps(
                {
                    "done": False,
                    "error": "linked features not in features.json",
                    "missing": missing,
                },
                indent=2,
            )
        )
        sys.exit(1)

    if remaining:
        print(json.dumps({"done": False, "remaining": remaining}, indent=2))
        return

    # All passed — transition
    transition(todo, "done")
    todo["archived_feature_paths"] = [
        f".claude/agents/state/archive/{fid}/" for fid in linked
    ]
    save_todos(data)
    print(
        json.dumps(
            {
                "done": True,
                "id": todo["id"],
                "archived_feature_paths": todo["archived_feature_paths"],
            },
            indent=2,
        )
    )


def op_drop(args):
    data = load_todos()
    _, todo = find_todo(data, args.id)
    if todo is None:
        sys.exit(f"error: todo '{args.id}' not found")
    transition(todo, "dropped")
    existing_notes = todo.get("notes") or ""
    sep = "\n\n" if existing_notes else ""
    todo["notes"] = f"{existing_notes}{sep}DROPPED: {args.reason}"
    save_todos(data)
    print(json.dumps({"id": todo["id"], "status": "dropped"}, indent=2))


def op_update(args):
    data = load_todos()
    _, todo = find_todo(data, args.id)
    if todo is None:
        sys.exit(f"error: todo '{args.id}' not found")
    updates = {}
    if args.description is not None:
        todo["description"] = args.description
        updates["description"] = args.description
    if args.category is not None:
        if args.category not in VALID_CATEGORIES:
            sys.exit(f"error: category must be one of {sorted(VALID_CATEGORIES)}")
        todo["category"] = args.category
        updates["category"] = args.category
    if args.notes is not None:
        todo["notes"] = args.notes
        updates["notes"] = args.notes
    if not updates:
        sys.exit("error: provide at least one of --description, --category, --notes")
    save_todos(data)
    print(json.dumps({"id": todo["id"], "updated": list(updates.keys())}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="op", required=True)

    p_add = sub.add_parser("add")
    p_add.add_argument("description")
    p_add.add_argument("--category", required=True, choices=sorted(VALID_CATEGORIES))
    p_add.add_argument("--notes")
    p_add.set_defaults(func=op_add)

    p_mark = sub.add_parser("mark-in-brainstorm")
    p_mark.add_argument("id")
    p_mark.set_defaults(func=op_mark_in_brainstorm)

    p_link = sub.add_parser("link-features")
    p_link.add_argument("id")
    p_link.add_argument("feature_ids", nargs="+")
    p_link.set_defaults(func=op_link_features)

    p_check = sub.add_parser("check-done")
    p_check.add_argument("id")
    p_check.set_defaults(func=op_check_done)

    p_drop = sub.add_parser("drop")
    p_drop.add_argument("id")
    p_drop.add_argument("--reason", required=True)
    p_drop.set_defaults(func=op_drop)

    p_update = sub.add_parser("update")
    p_update.add_argument("id")
    p_update.add_argument("--description")
    p_update.add_argument("--category", choices=sorted(VALID_CATEGORIES))
    p_update.add_argument("--notes")
    p_update.set_defaults(func=op_update)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
