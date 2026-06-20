# Taskly — Python CLI Task Manager

A command-line task manager built in pure Python, using a custom
decorator-based command-routing system and JSON-based persistent storage.

## Features

- Add, list, edit, complete, and delete tasks
- Priority levels (`low` / `medium` / `high`) and optional due dates
- Filter task list by priority or completion status
- Bulk-clear completed tasks
- Zero external dependencies — no Click, Typer, or Fire

## Architecture

**Decorator-based command routing.** Instead of manually wiring up an
`argparse` subparser for every command, each command is defined once with
a `@command(...)` decorator that registers the function name, help text,
and its CLI arguments in a single place:

```python
@command(
    "add",
    help="Add a new task",
    arguments=[
        (("title",), {"help": "Task title"}),
        (("-p", "--priority"), {"choices": ["low", "medium", "high"], "default": "medium"}),
    ],
)
def add_task(args):
    ...
```

At startup, `build_parser()` walks the registry and builds the full
`argparse.ArgumentParser` automatically. Adding a new command means
writing one new decorated function — no separate registration step, no
risk of the parser and the implementation drifting apart.

**Persistence.** Tasks are stored as a flat JSON array at `~/taskly.json`.
Each task is a dict with `id`, `title`, `priority`, `due`, `done`, and
`created_at`. The storage layer (`load_tasks` / `save_tasks`) is fully
decoupled from the command logic, so swapping JSON for SQLite later would
only touch two functions.

## Usage

```bash
# Add a task
python3 taskly.py add "Finish project report" -p high -d 2026-07-01

# List pending tasks
python3 taskly.py list

# List everything, including completed tasks
python3 taskly.py list --all

# Filter by priority
python3 taskly.py list -p high

# Mark a task done (use the short ID shown in `list`)
python3 taskly.py done 96e5d4d3

# Edit a task
python3 taskly.py edit 96e5d4d3 -t "New title" -p medium

# Delete a task
python3 taskly.py delete 96e5d4d3

# Remove all completed tasks
python3 taskly.py clear
```

Run `python3 taskly.py -h` or `python3 taskly.py <command> -h` for full
argument details.

