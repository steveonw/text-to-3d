#!/usr/bin/env python3
"""
worklog.py — Persistent scratchpad for the staged-3d-modeler workflow.

Gives the LLM a place to write things down instead of trying to remember them.
Useful for: decisions made, params locked in, ASCII diagrams, stacking math,
human feedback, things to fix later, cross-check results.

The worklog survives across the entire conversation. When context gets long
and the LLM starts losing track of early decisions, it reads the file back.

Usage:
    # Start a new project log
    python scripts/worklog.py init "Lighthouse v1.0"

    # Add a note under a stage heading
    python scripts/worklog.py add S1 "Object is a classic New England lighthouse, ~20m tall"
    python scripts/worklog.py add S2 "Human confirmed: base diameter 6m, tower height 18m"
    python scripts/worklog.py add S4 "Cross-check passed, all Y ranges match"
    python scripts/worklog.py add S9 "Human approved plan, wants pointed dome not rounded"
    python scripts/worklog.py add TODO "Fix window spacing on north face"
    python scripts/worklog.py add HUMAN "User said dome looks too flat, increase squash to 0.8"

    # Read back the whole log (do this when you need to remember what happened)
    python scripts/worklog.py read

    # Read just one stage's notes
    python scripts/worklog.py read S4

    # Read just human feedback
    python scripts/worklog.py read HUMAN

    # Read TODOs
    python scripts/worklog.py read TODO

    # Dump a summary of what's decided vs uncertain (quick refresh)
    python scripts/worklog.py status
"""

import argparse
import datetime
import re
import sys
from pathlib import Path

DEFAULT_PATH = "worklog.md"

VALID_TAGS = {
    "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9",
    "S10", "S10a", "S11", "S12",
    "HUMAN", "TODO", "DECIDED", "UNCERTAIN", "FIX", "NOTE",
}


def init_log(path: str, title: str):
    """Create a fresh worklog."""
    content = f"""# Worklog: {title}
Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}

---
"""
    Path(path).write_text(content)
    print(f"Created worklog: {path}")


def add_entry(path: str, tag: str, text: str):
    """Append a timestamped entry."""
    tag = tag.upper()
    timestamp = datetime.datetime.now().strftime('%H:%M')
    entry = f"\n**[{tag}]** ({timestamp}) {text}\n"
    with open(path, "a") as f:
        f.write(entry)
    print(f"Added [{tag}] entry to {path}")


def read_log(path: str, filter_tag: str = None):
    """Read back the log, optionally filtered to one tag."""
    text = Path(path).read_text()
    if not filter_tag:
        print(text)
        return

    filter_tag = filter_tag.upper()
    lines = text.split("\n")
    header_printed = False
    for line in lines:
        if f"**[{filter_tag}]**" in line:
            if not header_printed:
                print(f"# Entries tagged [{filter_tag}]\n")
                header_printed = True
            print(line)

    if not header_printed:
        print(f"No entries tagged [{filter_tag}] found.")


def show_status(path: str):
    """Quick summary: count entries per tag, list DECIDED and UNCERTAIN."""
    text = Path(path).read_text()
    counts = {}
    decided = []
    uncertain = []
    todos = []

    for line in text.split("\n"):
        m = re.search(r"\*\*\[([A-Z0-9a-z]+)\]\*\*\s*\([^)]*\)\s*(.*)", line)
        if m:
            tag = m.group(1).upper()
            content = m.group(2).strip()
            counts[tag] = counts.get(tag, 0) + 1
            if tag == "DECIDED":
                decided.append(content)
            elif tag == "UNCERTAIN":
                uncertain.append(content)
            elif tag == "TODO":
                todos.append(content)

    print("# Worklog Status\n")
    print("## Entry counts")
    for tag in sorted(counts):
        print(f"  {tag}: {counts[tag]}")

    if decided:
        print("\n## Decided")
        for d in decided:
            print(f"  - {d}")

    if uncertain:
        print("\n## Uncertain")
        for u in uncertain:
            print(f"  - {u}")

    if todos:
        print("\n## TODO")
        for t in todos:
            print(f"  - {t}")

    if not counts:
        print("  (empty log)")


def main():
    parser = argparse.ArgumentParser(description="Project worklog for staged 3D modeling")
    parser.add_argument("command", choices=["init", "add", "read", "status"])
    parser.add_argument("arg1", nargs="?", default=None)
    parser.add_argument("arg2", nargs="?", default=None)
    parser.add_argument("--file", default=DEFAULT_PATH, help="Worklog file path")
    args = parser.parse_args()

    if args.command == "init":
        title = args.arg1 or "Untitled Project"
        init_log(args.file, title)

    elif args.command == "add":
        if not args.arg1 or not args.arg2:
            print("Usage: worklog.py add TAG \"note text\"")
            sys.exit(1)
        if not Path(args.file).exists():
            init_log(args.file, "Auto-created")
        add_entry(args.file, args.arg1, args.arg2)

    elif args.command == "read":
        if not Path(args.file).exists():
            print("No worklog found. Run: worklog.py init \"Project Name\"")
            sys.exit(1)
        read_log(args.file, args.arg1)

    elif args.command == "status":
        if not Path(args.file).exists():
            print("No worklog found.")
            sys.exit(1)
        show_status(args.file)


if __name__ == "__main__":
    main()
