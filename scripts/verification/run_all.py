"""
Run all verifiers on a SceneResult — one call, three views.

Usage from Python:
    from dropgrid.api import solve_object_scene
    from verification.run_all import verify

    result = solve_object_scene(dsl, seed=42)
    report = verify(result)
    print(report)

Usage from CLI:
    python scripts/verification/run_all.py --example shrine
    python scripts/verification/run_all.py --dsl-file scene.dsl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


_REPO_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_SCRIPTS))


def verify(result, *, write_layout_to: str | None = None) -> Dict[str, Any]:
    """Run all three verifiers against a SceneResult.

    Returns a dict with keys:
        - 'ascii'   : str — dropgrid's native top-down view
        - 'braille' : str — braille top-down silhouette
        - 'inventory': dict — piece counts by type
        - 'warnings': list[str] — any issues spotted during conversion

    If write_layout_to is given, the layout JSON used for braille is also
    saved to that path for inspection.
    """
    out: Dict[str, Any] = {"warnings": []}

    # 1. dropgrid ASCII (always works — native to SceneResult)
    try:
        out["ascii"] = result.to_ascii(include_legend=True)
    except Exception as e:
        out["ascii"] = ""
        out["warnings"].append(f"ascii view failed: {e}")

    # 2. Braille via to_layout('parts') adapter
    try:
        layout = result.to_layout("parts")
        if write_layout_to:
            Path(write_layout_to).write_text(json.dumps(layout, indent=2))
        from verification.braille_view import render_top  # type: ignore
        out["braille"] = render_top(layout, zoom=1.0)
    except Exception as e:
        out["braille"] = ""
        out["warnings"].append(f"braille view failed: {e}")

    # 3. Piece inventory by type — cheap and high-signal
    type_counts: Dict[str, int] = {}
    for p in result.pieces:
        type_counts[p.type] = type_counts.get(p.type, 0) + 1
    out["inventory"] = type_counts

    # 4. Spatial sanity checks (basic — overlaps via world-cell collision).
    # p.cells are LOCAL offsets, so we add (gx, gy, gz) to get world cells.
    cell_owners: Dict[tuple, int] = {}
    overlaps = []
    for p in result.pieces:
        for cx, cy, cz in p.cells:
            world_cell = (p.gx + cx, p.gy + cy, p.gz + cz)
            if world_cell in cell_owners and cell_owners[world_cell] != p.id:
                overlaps.append((world_cell, cell_owners[world_cell], p.id))
            cell_owners[world_cell] = p.id
    if overlaps:
        out["warnings"].append(
            f"spatial: {len(overlaps)} cell overlap(s) — first: {overlaps[0]}"
        )

    return out


def format_report(report: Dict[str, Any]) -> str:
    """Pretty-print a verify() report for terminal display."""
    lines = []
    lines.append("=" * 60)
    lines.append("VERIFICATION REPORT")
    lines.append("=" * 60)

    lines.append("\n[1] Dropgrid ASCII layout:")
    lines.append(report.get("ascii", "(failed)"))

    lines.append("\n[2] Braille silhouette:")
    lines.append(report.get("braille", "(failed)"))

    lines.append("\n[3] Piece inventory:")
    inv = report.get("inventory", {})
    if inv:
        for t, n in sorted(inv.items(), key=lambda x: -x[1]):
            lines.append(f"  {t:12s}  {n}")
    else:
        lines.append("  (no pieces)")

    warnings = report.get("warnings", [])
    if warnings:
        lines.append("\n[!] Warnings:")
        for w in warnings:
            lines.append(f"  - {w}")
    else:
        lines.append("\n[✓] No warnings.")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Run all verifiers on a scene.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--example", choices=["shrine", "village", "graveyard",
                                            "walled_city", "campsite"],
                     help="Built-in example DSL")
    src.add_argument("--dsl-file", type=Path, help="Path to a DSL file")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--save-layout", type=Path,
                    help="Save the parts-format layout JSON to this path")
    args = ap.parse_args()

    from dropgrid.api import solve_object_scene  # type: ignore
    from dropgrid_run import EXAMPLES  # type: ignore

    if args.example:
        dsl = EXAMPLES[args.example]["intent"]
    else:
        dsl = args.dsl_file.read_text()

    result = solve_object_scene(dsl, seed=args.seed)
    report = verify(result, write_layout_to=str(args.save_layout) if args.save_layout else None)
    print(format_report(report))
    return 0 if not report["warnings"] else 1


if __name__ == "__main__":
    sys.exit(main())
