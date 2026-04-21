#!/usr/bin/env python3
"""Summarize a Three.js HTML/JS file for refinement work.

Heuristic parser: counts common geometries, materials, lights, helpers, groups,
InstancedMesh, and named functions. Good enough for patch planning.
"""
from __future__ import annotations
import argparse, json, re, sys
from collections import Counter
from pathlib import Path

PATTERNS = {
    "geometries": r"new\s+THREE\.([A-Za-z0-9_]+Geometry)\s*\(",
    "materials": r"new\s+THREE\.([A-Za-z0-9_]+Material)\s*\(",
    "lights": r"new\s+THREE\.([A-Za-z0-9_]+Light)\s*\(",
    "helpers": r"new\s+THREE\.([A-Za-z0-9_]+Helper)\s*\(",
    "objects": r"new\s+THREE\.([A-Za-z0-9_]+)\s*\(",
    "functions": r"function\s+([A-Za-z0-9_]+)\s*\(",
    "mesh_vars": r"const\s+([A-Za-z0-9_]+)\s*=\s*new\s+THREE\.(Mesh|Group|InstancedMesh|Line|Points)",
}


def count_matches(text: str, pattern: str) -> Counter:
    return Counter(re.findall(pattern, text))


def normalize_counter_dict(section: str, counter: Counter) -> dict[str, int]:
    if section == "mesh_vars":
        return {f"{name}:{kind}": count for (name, kind), count in counter.items()}
    return {str(k): v for k, v in counter.items()}


def extract_param_keys(text: str) -> list[str]:
    keys = set(re.findall(r"PARAMS\.([A-Za-z0-9_]+)", text))
    m = re.search(r"const\s+PARAMS\s*=\s*\{(.*?)\}\s*;", text, re.S)
    if m:
        body = m.group(1)
        for key in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*:", body):
            keys.add(key)
    return sorted(keys)


def build_inventory(text: str) -> dict:
    out = {}
    for section, pattern in PATTERNS.items():
        out[section] = normalize_counter_dict(section, count_matches(text, pattern))
    out["instanced_mesh_count"] = len(re.findall(r"new\s+THREE\.InstancedMesh\s*\(", text))
    out["param_keys"] = extract_param_keys(text)
    out["param_key_count"] = len(out["param_keys"])
    out["has_build_model"] = bool(re.search(r"function\s+buildModel\s*\(", text))
    out["has_orbit_controls"] = "OrbitControls" in text
    out["has_grid_helper"] = "GridHelper" in text
    out["has_axes_helper"] = "AxesHelper" in text
    return out


def to_markdown(inv: dict) -> str:
    lines = ["# Scene Inventory", ""]
    lines.append(f"- buildModel present: {inv['has_build_model']}")
    lines.append(f"- OrbitControls present: {inv['has_orbit_controls']}")
    lines.append(f"- Grid helper present: {inv['has_grid_helper']}")
    lines.append(f"- Axes helper present: {inv['has_axes_helper']}")
    lines.append(f"- InstancedMesh count: {inv['instanced_mesh_count']}")
    lines.append(f"- PARAMS keys referenced: {inv['param_key_count']}")
    for section in ["geometries", "materials", "lights", "helpers", "functions", "mesh_vars"]:
        lines += ["", f"## {section.title()}"]
        items = inv.get(section, {})
        if not items:
            lines.append("- none found")
        else:
            for k, v in sorted(items.items()):
                label = k.replace(":", " (type ") + ")" if section == "mesh_vars" and ":" in k else k
                lines.append(f"- {label}: {v}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--format", choices=["json", "md"], default="md")
    ap.add_argument("--out")
    args = ap.parse_args()
    text = Path(args.source).read_text()
    inv = build_inventory(text)
    out = json.dumps(inv, indent=2) if args.format == "json" else to_markdown(inv)
    if args.out:
        Path(args.out).write_text(out + ("" if out.endswith("\n") else "\n"))
    else:
        sys.stdout.write(out + ("" if out.endswith("\n") else "\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
