#!/usr/bin/env python3
"""
Read-only queries against .claude/todos.json.

Usage:
  query.py list [--status=s1,s2] [--category=c] [--format=json|table]
  query.py get <id>
  query.py count [--status=s]
  query.py pending    # shortcut for list --status=pending

Default status filter for `list`: pending,in_brainstorm,in_feature
(excludes done + dropped, which are historical).
"""
import argparse
import json
import sys
from pathlib import Path

TODOS_PATH = Path(".claude/todos.json")
VALID_STATUSES = {"pending", "in_brainstorm", "in_feature", "done", "dropped"}
VALID_CATEGORIES = {"feature-idea", "tech-debt", "investigation", "ux-improvement"}


def load():
    if not TODOS_PATH.exists():
        return {"todos": []}
    try:
        return json.loads(TODOS_PATH.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"error: {TODOS_PATH} is not valid JSON: {e}")


def list_todos(statuses, category):
    data = load()
    results = data["todos"]
    if statuses:
        results = [t for t in results if t.get("status") in statuses]
    if category:
        results = [t for t in results if t.get("category") == category]
    return results


def get_todo(todo_id):
    data = load()
    for t in data["todos"]:
        if t.get("id") == todo_id:
            return t
    return None


def format_table(todos):
    if not todos:
        return "(no matching todos)"
    lines = []
    for t in todos:
        linked = len(t.get("linked_feature_ids", []))
        linked_str = f" [{linked} linked]" if linked else ""
        lines.append(
            f"[{t['status']}] [{t['category']}] {t['id']}{linked_str}\n  {t['description']}"
        )
    return "\n".join(lines)


def parse_status_arg(s):
    if not s:
        return None
    statuses = set(x.strip() for x in s.split(","))
    invalid = statuses - VALID_STATUSES
    if invalid:
        sys.exit(f"error: invalid status(es): {invalid}")
    return statuses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="op", required=True)

    p_list = sub.add_parser("list", help="List todos (filtered)")
    p_list.add_argument("--status", default="pending,in_brainstorm,in_feature")
    p_list.add_argument("--category")
    p_list.add_argument("--format", choices=["json", "table"], default="table")

    p_get = sub.add_parser("get", help="Get one todo by id")
    p_get.add_argument("id")

    p_count = sub.add_parser("count", help="Count matching todos")
    p_count.add_argument("--status", default="pending")

    p_pending = sub.add_parser("pending", help="List pending todos (table)")

    args = parser.parse_args()

    if args.op == "list":
        statuses = parse_status_arg(args.status)
        todos = list_todos(statuses, args.category)
        if args.format == "json":
            print(json.dumps(todos, indent=2))
        else:
            print(format_table(todos))
            print(f"\n({len(todos)} total)")

    elif args.op == "get":
        todo = get_todo(args.id)
        if todo is None:
            sys.exit(f"error: todo '{args.id}' not found")
        print(json.dumps(todo, indent=2))

    elif args.op == "count":
        statuses = parse_status_arg(args.status)
        print(len(list_todos(statuses, None)))

    elif args.op == "pending":
        todos = list_todos({"pending"}, None)
        print(format_table(todos))
        print(f"\n({len(todos)} pending)")


if __name__ == "__main__":
    main()
