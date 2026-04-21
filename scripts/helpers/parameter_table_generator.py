#!/usr/bin/env python3
"""Generate a parameter table from JSON for 3D modeling workflows.

Input JSON shape:
{
  "unit": "m",
  "parameters": {
    "baseWidth": {"value": 12, "status": "confirmed", "notes": "from front photo"},
    "domeRadius": {"value": 3.2, "status": "inferred", "depends_on": ["baseWidth"]}
  }
}

Also accepts a flat dict under "parameters" or top-level numeric keys.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from typing import Any

VALID_STATUS = {"confirmed", "inferred", "placeholder"}


def normalize(data: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    unit = data.get("unit", "unit")
    raw = data.get("parameters", data)
    rows = []
    for name, value in raw.items():
        if name == "unit":
            continue
        if isinstance(value, dict):
            row = {
                "name": name,
                "value": value.get("value", ""),
                "status": value.get("status", "placeholder"),
                "notes": value.get("notes", ""),
                "depends_on": value.get("depends_on", []),
            }
        else:
            row = {
                "name": name,
                "value": value,
                "status": "placeholder",
                "notes": "",
                "depends_on": [],
            }
        if row["status"] not in VALID_STATUS:
            row["status"] = "placeholder"
        rows.append(row)
    return unit, rows


def to_markdown(unit: str, rows: list[dict[str, Any]]) -> str:
    lines = [f"# Parameter Table ({unit})", "", "| Name | Value | Status | Depends On | Notes |", "|---|---:|---|---|---|"]
    status_order = {"confirmed": 0, "inferred": 1, "placeholder": 2}
    for row in sorted(rows, key=lambda r: (status_order.get(r["status"], 9), r["name"].lower())):
        deps = ", ".join(row.get("depends_on", []))
        lines.append(f"| {row['name']} | {row['value']} | {row['status']} | {deps} | {row['notes']} |")
    counts = {k: sum(1 for r in rows if r['status'] == k) for k in VALID_STATUS}
    lines += ["", f"Confirmed: {counts['confirmed']}  ", f"Inferred: {counts['inferred']}  ", f"Placeholder: {counts['placeholder']}"]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input_json")
    ap.add_argument("--out", help="output markdown path")
    args = ap.parse_args()
    data = json.loads(Path(args.input_json).read_text())
    unit, rows = normalize(data)
    out = to_markdown(unit, rows)
    if args.out:
        Path(args.out).write_text(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
