#!/usr/bin/env python3
"""
Taskly - A command-line task manager.

Architecture
------------
- Custom decorator (`@command`) registers each subcommand function in a
  global COMMANDS registry, along with its argparse argument definitions.
- `build_parser()` reads that registry at startup and wires up an
  `argparse.ArgumentParser` with one subparser per registered command.
  This means adding a new command only requires writing a new
  `@command(...)`-decorated function -- no manual subparser wiring.
- Persistence is a flat JSON file at ~/taskly.json. No external
  dependencies (no Click / Typer / Fire) -- pure Python standard library.
"""

import argparse
import json
import uuid
from datetime import datetime
from pathlib import Path

STORAGE_PATH = Path.home() / "taskly.json"


# ---------------------------------------------------------------------------
# Storage layer
# ---------------------------------------------------------------------------

def load_tasks():
    """Load all tasks from the JSON store. Returns [] if missing/corrupt."""
    if not STORAGE_PATH.exists():
        return []
    try:
        with open(STORAGE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_tasks(tasks):
    """Persist the full task list back to the JSON store."""
    with open(STORAGE_PATH, "w") as f:
        json.dump(tasks, f, indent=2)


# ---------------------------------------------------------------------------
# Decorator-based command routing
# ---------------------------------------------------------------------------

COMMANDS = {}


def command(name, help="", arguments=None):
    """
    Decorator that registers a function as a CLI subcommand.

    Parameters
    ----------
    name : str
        The subcommand name (e.g. "add", "list").
    help : str
        Short help text shown in `taskly -h`.
    arguments : list[tuple[tuple, dict]]
        Each entry is (positional_flags, kwargs) passed straight through
        to argparse's `add_argument(*flags, **kwargs)`. This lets each
        command function declare its own CLI signature right next to its
        implementation, instead of a separate wiring step.
    """
    def decorator(func):
        COMMANDS[name] = {
            "func": func,
            "help": help,
            "arguments": arguments or [],
        }
        return func
    return decorator


def build_parser():
    """Construct the top-level parser from whatever has been registered
    in COMMANDS via the @command decorator."""
    parser = argparse.ArgumentParser(
        prog="taskly",
        description="A simple command-line task manager.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, spec in COMMANDS.items():
        sub = subparsers.add_parser(name, help=spec["help"])
        for flags, kwargs in spec["arguments"]:
            sub.add_argument(*flags, **kwargs)
        sub.set_defaults(_func=spec["func"])

    return parser


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@command(
    "add",
    help="Add a new task",
    arguments=[
        (("title",), {"help": "Task title"}),
        (("-p", "--priority"),
         {"choices": ["low", "medium", "high"], "default": "medium",
          "help": "Task priority (default: medium)"}),
        (("-d", "--due"), {"help": "Due date, e.g. 2026-07-01"}),
    ],
)
def add_task(args):
    tasks = load_tasks()
    task = {
        "id": str(uuid.uuid4())[:8],
        "title": args.title,
        "priority": args.priority,
        "due": args.due,
        "done": False,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    tasks.append(task)
    save_tasks(tasks)
    print(f"Added task [{task['id']}]: {task['title']}")


@command(
    "list",
    help="List tasks",
    arguments=[
        (("-a", "--all"), {"action": "store_true",
                            "help": "Include completed tasks"}),
        (("-p", "--priority"), {"choices": ["low", "medium", "high"],
                                 "help": "Filter by priority"}),
    ],
)
def list_tasks(args):
    tasks = load_tasks()
    if not args.all:
        tasks = [t for t in tasks if not t["done"]]
    if args.priority:
        tasks = [t for t in tasks if t["priority"] == args.priority]

    if not tasks:
        print("No tasks found.")
        return

    for t in sorted(tasks, key=lambda x: x["created_at"]):
        status = "x" if t["done"] else " "
        due = f" (due {t['due']})" if t.get("due") else ""
        print(f"[{status}] {t['id']}  {t['title']}  [{t['priority']}]{due}")


@command(
    "done",
    help="Mark a task as complete",
    arguments=[(("id",), {"help": "Task ID"})],
)
def complete_task(args):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == args.id:
            t["done"] = True
            save_tasks(tasks)
            print(f"Marked task [{args.id}] as done.")
            return
    print(f"No task found with ID {args.id}")


@command(
    "delete",
    help="Delete a task",
    arguments=[(("id",), {"help": "Task ID"})],
)
def delete_task(args):
    tasks = load_tasks()
    remaining = [t for t in tasks if t["id"] != args.id]
    if len(remaining) == len(tasks):
        print(f"No task found with ID {args.id}")
        return
    save_tasks(remaining)
    print(f"Deleted task [{args.id}]")


@command(
    "edit",
    help="Edit a task's title, priority, or due date",
    arguments=[
        (("id",), {"help": "Task ID"}),
        (("-t", "--title"), {"help": "New title"}),
        (("-p", "--priority"), {"choices": ["low", "medium", "high"],
                                 "help": "New priority"}),
        (("-d", "--due"), {"help": "New due date"}),
    ],
)
def edit_task(args):
    tasks = load_tasks()
    for t in tasks:
        if t["id"] == args.id:
            if args.title:
                t["title"] = args.title
            if args.priority:
                t["priority"] = args.priority
            if args.due:
                t["due"] = args.due
            save_tasks(tasks)
            print(f"Updated task [{args.id}]")
            return
    print(f"No task found with ID {args.id}")


@command("clear", help="Delete all completed tasks")
def clear_done(args):
    tasks = load_tasks()
    remaining = [t for t in tasks if not t["done"]]
    removed = len(tasks) - len(remaining)
    save_tasks(remaining)
    print(f"Cleared {removed} completed task(s).")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = build_parser()
    args = parser.parse_args()
    args._func(args)


if __name__ == "__main__":
    main()
