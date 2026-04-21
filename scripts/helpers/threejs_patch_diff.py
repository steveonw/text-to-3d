#!/usr/bin/env python3
"""Create a scoped patch-plan for existing Three.js files.

Two modes:
  1. Compare two file versions → structural diff + function-body diffs
  2. One file + change note → structural inventory + scoped edit plan

Usage:
    python threejs_patch_diff.py old.html new.html
    python threejs_patch_diff.py existing.html --note "raise dome and reduce drum height"
    python threejs_patch_diff.py old.html new.html --format json
"""
from __future__ import annotations
import argparse, difflib, json, re, sys
from pathlib import Path

KEY_PATTERNS = [
    ("PARAMS", r"PARAMS\.([A-Za-z0-9_]+)"),
    ("functions", r"function\s+([A-Za-z0-9_]+)\s*\("),
    ("geometries", r"new\s+THREE\.([A-Za-z0-9_]+Geometry)\s*\("),
    ("materials", r"new\s+THREE\.([A-Za-z0-9_]+Material)\s*\("),
]


def extract_symbols(text: str) -> dict[str, list[str]]:
    return {name: sorted(set(re.findall(pattern, text))) for name, pattern in KEY_PATTERNS}


def extract_function_bodies(text: str) -> dict[str, str]:
    """Extract function name → body text using brace counting."""
    bodies = {}
    pattern = re.compile(r'function\s+([A-Za-z0-9_]+)\s*\([^)]*\)\s*\{')
    for m in pattern.finditer(text):
        name = m.group(1)
        start = m.start()
        brace_pos = m.end() - 1
        depth = 1
        i = brace_pos + 1
        while i < len(text) and depth > 0:
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        bodies[name] = text[start:i].strip()
    return bodies


def diff_symbols(a: dict[str, list[str]], b: dict[str, list[str]]) -> dict:
    out = {}
    for key in a:
        sa, sb = set(a[key]), set(b[key])
        out[key] = {
            "added": sorted(sb - sa),
            "removed": sorted(sa - sb),
            "kept": sorted(sa & sb),
        }
    return out


def diff_function_bodies(before: dict[str, str], after: dict[str, str]) -> dict[str, str]:
    """Unified diffs for functions that changed. Skips identical ones."""
    diffs = {}
    all_names = sorted(set(before) | set(after))
    for name in all_names:
        old = before.get(name, "")
        new = after.get(name, "")
        if old == new:
            continue
        if not old:
            diffs[name] = f"+ NEW FUNCTION ({len(new.splitlines())} lines)"
            continue
        if not new:
            diffs[name] = f"- REMOVED FUNCTION ({len(old.splitlines())} lines)"
            continue
        diff_lines = list(difflib.unified_diff(
            old.splitlines(), new.splitlines(),
            fromfile=f"{name} (before)", tofile=f"{name} (after)",
            lineterm="",
        ))
        if diff_lines:
            if len(diff_lines) > 60:
                diff_lines = diff_lines[:55] + [f"... ({len(diff_lines) - 55} more lines)"]
            diffs[name] = "\n".join(diff_lines)
    return diffs


def summarize_comparison(sym_diff: dict, func_diffs: dict[str, str], note: str = "") -> str:
    """Full comparison mode: two files."""
    lines = ["# Patch Diff Report", ""]

    if note:
        lines += ["## Change context", note, ""]

    lines.append("## Symbol changes")
    for category in ["PARAMS", "functions", "geometries", "materials"]:
        d = sym_diff[category]
        parts = []
        if d["added"]:
            parts.append(f"added: {', '.join(d['added'])}")
        if d["removed"]:
            parts.append(f"removed: {', '.join(d['removed'])}")
        if parts:
            lines.append(f"- **{category}**: {'; '.join(parts)}")
    if all(not sym_diff[c]["added"] and not sym_diff[c]["removed"] for c in sym_diff):
        lines.append("- no symbol-level additions or removals detected")
    lines.append("")

    if func_diffs:
        lines.append("## Function changes")
        for name, diff_text in sorted(func_diffs.items()):
            lines.append(f"### {name}")
            lines.append("```diff")
            lines.append(diff_text)
            lines.append("```")
            lines.append("")
    else:
        lines += ["## Function changes", "- no function bodies changed", ""]

    lines.append("## Risks")
    risks = []
    if sym_diff["PARAMS"]["removed"]:
        risks.append(f"Removed PARAMS keys ({', '.join(sym_diff['PARAMS']['removed'])}) may break geometry that references them.")
    if sym_diff["functions"]["removed"]:
        risks.append(f"Removed functions ({', '.join(sym_diff['functions']['removed'])}) may break the assembly chain.")
    changed_count = len(func_diffs)
    if changed_count > 3:
        risks.append(f"{changed_count} functions changed — consider splitting into smaller passes.")
    if not risks:
        risks.append("Low structural risk from detected changes.")
    for r in risks:
        lines.append(f"- {r}")
    lines.append("")

    lines.append("## Preserve")
    if sym_diff["PARAMS"]["kept"]:
        lines.append(f"- {len(sym_diff['PARAMS']['kept'])} existing PARAMS keys unchanged — keep them stable.")
    if sym_diff["functions"]["kept"]:
        lines.append(f"- {len(sym_diff['functions']['kept'])} existing functions unchanged — don't touch them.")
    lines.append("- Preserve controls, helpers, and deliberate dimension relationships unless user asks otherwise.")

    return "\n".join(lines) + "\n"


def summarize_single_file(symbols: dict, note: str = "") -> str:
    """Single-file mode: inventory + edit plan scoped to the note."""
    lines = ["# Patch Plan", ""]

    lines += ["## Requested change", note or "- no change note provided", ""]

    lines.append("## Current structure")
    for category in ["PARAMS", "functions", "geometries", "materials"]:
        items = symbols[category]
        if items:
            lines.append(f"- **{category}** ({len(items)}): {', '.join(items)}")
        else:
            lines.append(f"- **{category}**: none found")
    lines.append("")

    lines.append("## Scoped edit plan")
    if note:
        note_lower = note.lower()
        likely_params = [p for p in symbols["PARAMS"] if p.lower() in note_lower]
        likely_funcs = [f for f in symbols["functions"]
                        if f.lower() != "animate" and any(w in f.lower() for w in note_lower.split() if len(w) > 3)]

        if likely_params:
            lines.append(f"1. Update PARAMS: likely keys → {', '.join(likely_params)}")
        else:
            lines.append("1. Identify which PARAMS keys need to change for this edit.")

        if likely_funcs:
            lines.append(f"2. Edit functions: likely targets → {', '.join(likely_funcs)}")
        else:
            lines.append("2. Identify the narrowest builder function that covers this area.")

        lines.append("3. Re-check placement and proportions after the change.")
        lines.append("4. Review screenshot before any further polish.")
    else:
        lines += [
            "1. Update PARAMS only where required.",
            "2. Edit the narrowest affected builder function.",
            "3. Re-check placement/proportions.",
            "4. Review screenshot before further polish.",
        ]
    lines.append("")

    lines.append("## Preserve")
    safe_funcs = [f for f in symbols["functions"] if f != "animate"]
    lines.append(f"- Existing functions to keep intact unless directly affected: {', '.join(safe_funcs) or 'none'}")
    lines.append(f"- All {len(symbols['PARAMS'])} current PARAMS keys unless the change requires modification.")
    lines.append("- Controls, helpers, and presentation features.")

    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before", help="Source Three.js/HTML file")
    ap.add_argument("after", nargs="?", help="Optional second version to compare against")
    ap.add_argument("--note", default="", help="Description of the intended change")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--out", help="Output file path")
    args = ap.parse_args()

    before_text = Path(args.before).read_text()
    before_syms = extract_symbols(before_text)

    if args.after:
        after_text = Path(args.after).read_text()
        after_syms = extract_symbols(after_text)
        sym_diff = diff_symbols(before_syms, after_syms)
        func_diffs = diff_function_bodies(
            extract_function_bodies(before_text),
            extract_function_bodies(after_text),
        )
        if args.format == "json":
            out = json.dumps({"symbols": sym_diff, "function_diffs": func_diffs}, indent=2)
        else:
            out = summarize_comparison(sym_diff, func_diffs, args.note)
    else:
        if args.format == "json":
            out = json.dumps({"symbols": before_syms}, indent=2)
        else:
            out = summarize_single_file(before_syms, args.note)

    if args.out:
        Path(args.out).write_text(out)
    else:
        sys.stdout.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
