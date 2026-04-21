#!/usr/bin/env python3
"""design_napkin.py — lightweight external working memory for scene work.

Use as a napkin, not a diary. Store the current scene state, candidate values,
short reasons for changes, and tweakable grouped values.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

DEFAULT_PATH = "design_napkin.json"


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def _blank(title: str = "Untitled Project") -> dict[str, Any]:
    return {
        "title": title,
        "created": _now(),
        "updated": _now(),
        "current": {},
        "candidates": [],
        "reasons": {},
        "notes": [],
    }


def _read(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return _blank()
    return json.loads(p.read_text())


def _write(path: str, data: dict[str, Any]) -> None:
    data["updated"] = _now()
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=False))


def _coerce(value: str) -> Any:
    low = value.lower()
    if low in {"true", "false"}:
        return low == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _set_nested(root: dict[str, Any], dotted_key: str, value: Any) -> None:
    parts = dotted_key.split(".")
    cur = root
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def _get_parent_and_key(root: dict[str, Any], dotted_key: str):
    parts = dotted_key.split(".")
    cur = root
    for part in parts[:-1]:
        if part not in cur or not isinstance(cur[part], dict):
            return None, None
        cur = cur[part]
    return cur, parts[-1]


def init_cmd(path: str, title: str) -> None:
    _write(path, _blank(title))
    print(f"Initialized napkin: {path}")


def note_cmd(path: str, key: str, value: str) -> None:
    data = _read(path)
    data["current"][key] = value
    _write(path, data)
    print(f"Set current[{key}]")


def set_cmd(path: str, dotted_key: str, value: str) -> None:
    data = _read(path)
    _set_nested(data["current"], dotted_key, _coerce(value))
    _write(path, data)
    print(f"Set {dotted_key}")


def set_json_cmd(path: str, dotted_key: str, value_json: str) -> None:
    data = _read(path)
    _set_nested(data["current"], dotted_key, json.loads(value_json))
    _write(path, data)
    print(f"Set {dotted_key} from JSON")


def delete_cmd(path: str, dotted_key: str) -> None:
    data = _read(path)
    parent, key = _get_parent_and_key(data["current"], dotted_key)
    if parent is not None and key in parent:
        del parent[key]
        _write(path, data)
        print(f"Deleted {dotted_key}")
    else:
        print(f"Key not found: {dotted_key}")


def candidate_cmd(path: str, text: str) -> None:
    data = _read(path)
    data.setdefault("candidates", []).append({"time": _now(), "text": text})
    _write(path, data)
    print("Added candidate")


def because_cmd(path: str, key: str, text: str) -> None:
    data = _read(path)
    data.setdefault("reasons", {})[key] = text
    _write(path, data)
    print(f"Set reason for {key}")


def add_note_cmd(path: str, text: str) -> None:
    data = _read(path)
    data.setdefault("notes", []).append({"time": _now(), "text": text})
    _write(path, data)
    print("Added note")


def show_cmd(path: str, section: str | None) -> None:
    data = _read(path)
    print(json.dumps(data.get(section, data) if section else data, indent=2))


def status_cmd(path: str) -> None:
    data = _read(path)
    print(f"# {data.get('title', 'Untitled Project')}\n")
    print(f"updated: {data.get('updated', 'unknown')}\n")
    cur = data.get("current", {})
    if cur:
        print("## current")
        for k, v in cur.items():
            print(f"- {k}: {v}")
    reasons = data.get("reasons", {})
    if reasons:
        print("\n## reasons")
        for k, v in reasons.items():
            print(f"- {k}: {v}")
    candidates = data.get("candidates", [])
    if candidates:
        print("\n## candidates")
        for item in candidates[-5:]:
            print(f"- {item['text']}")
    notes = data.get("notes", [])
    if notes:
        print("\n## notes")
        for item in notes[-5:]:
            print(f"- {item['text']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lightweight scene state napkin")
    parser.add_argument("command", choices=["init", "note", "set", "set-json", "delete", "candidate", "because", "add-note", "show", "status"])
    parser.add_argument("arg1", nargs="?")
    parser.add_argument("arg2", nargs="?")
    parser.add_argument("--file", default=DEFAULT_PATH)
    args = parser.parse_args()

    if args.command == "init":
        init_cmd(args.file, args.arg1 or "Untitled Project")
    elif args.command == "note":
        if not args.arg1 or args.arg2 is None:
            raise SystemExit("Usage: design_napkin.py note <key> <value>")
        note_cmd(args.file, args.arg1, args.arg2)
    elif args.command == "set":
        if not args.arg1 or args.arg2 is None:
            raise SystemExit("Usage: design_napkin.py set <dotted-key> <value>")
        set_cmd(args.file, args.arg1, args.arg2)
    elif args.command == "set-json":
        if not args.arg1 or args.arg2 is None:
            raise SystemExit("Usage: design_napkin.py set-json <dotted-key> <json>")
        set_json_cmd(args.file, args.arg1, args.arg2)
    elif args.command == "delete":
        if not args.arg1:
            raise SystemExit("Usage: design_napkin.py delete <dotted-key>")
        delete_cmd(args.file, args.arg1)
    elif args.command == "candidate":
        if not args.arg1:
            raise SystemExit("Usage: design_napkin.py candidate <text>")
        candidate_cmd(args.file, args.arg1)
    elif args.command == "because":
        if not args.arg1 or args.arg2 is None:
            raise SystemExit("Usage: design_napkin.py because <key> <reason>")
        because_cmd(args.file, args.arg1, args.arg2)
    elif args.command == "add-note":
        if not args.arg1:
            raise SystemExit("Usage: design_napkin.py add-note <text>")
        add_note_cmd(args.file, args.arg1)
    elif args.command == "show":
        show_cmd(args.file, args.arg1)
    elif args.command == "status":
        status_cmd(args.file)


if __name__ == "__main__":
    main()
