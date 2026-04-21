#!/usr/bin/env python3
"""
visualize.py — Generate 2D layout plots from PARAMS for visual self-checking.

Gives the LLM a way to "see" its own layout plan as a PNG before writing
Three.js code. Useful when the LLM has vision capability and can view the
generated image to catch overlaps, spacing errors, and proportion issues
that ASCII diagrams miss.

Usage:
    # From a params JSON file (top-down floor plan)
    python scripts/visualize.py plan params.json --out layout.png

    # From geo.py placement output (plot where things land)
    python scripts/visualize.py placements placements.json --out grid.png

    # From a simple box list (quick bounding box check)
    python scripts/visualize.py boxes boxes.json --out boxes.png

Input format for 'plan' mode (params.json):
{
    "unit": "m",
    "room": {"width": 14, "depth": 10},
    "parts": [
        {"name": "bar", "x": -5, "z": 0, "w": 2, "d": 8, "tier": "hero"},
        {"name": "table1", "x": 2, "z": 2, "w": 1.2, "d": 1.2, "tier": "mid"},
        {"name": "fireplace", "x": 0, "z": 4.5, "w": 3, "d": 0.6, "tier": "hero"}
    ]
}

Input format for 'placements' mode:
    Direct output from geo.py grid/ring commands (list of {x, y, z} dicts)

Input format for 'boxes' mode:
    [{"name": "base", "x": 0, "z": 0, "w": 12, "d": 8},
     {"name": "tower", "x": 0, "z": 0, "w": 4, "d": 4}]
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import matplotlib
    matplotlib.use('Agg')  # headless
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    HAS_MPL = True
except ImportError:
    HAS_MPL = False


# Colors by detail tier
TIER_COLORS = {
    "hero": "#4a90d9",
    "mid": "#7cb342",
    "far": "#bdbdbd",
    "structure": "#8d6e63",
    "default": "#90a4ae",
}


def draw_plan(data: dict, out_path: str):
    """Draw a top-down floor plan from structured params."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    
    unit = data.get("unit", "m")
    room = data.get("room", {})
    parts = data.get("parts", [])
    
    # Draw room outline if provided
    if room:
        rw = room.get("width", 20)
        rd = room.get("depth", 20)
        room_rect = patches.Rectangle(
            (-rw/2, -rd/2), rw, rd,
            linewidth=2, edgecolor='black', facecolor='#f5f5f0',
            linestyle='--', label='room boundary'
        )
        ax.add_patch(room_rect)
        margin = max(rw, rd) * 0.15
        ax.set_xlim(-rw/2 - margin, rw/2 + margin)
        ax.set_ylim(-rd/2 - margin, rd/2 + margin)
    
    # Draw parts
    for part in parts:
        name = part.get("name", "?")
        x = part.get("x", 0)
        z = part.get("z", 0)
        w = part.get("w", 1)
        d = part.get("d", 1)
        tier = part.get("tier", "default")
        color = TIER_COLORS.get(tier, TIER_COLORS["default"])
        
        rect = patches.Rectangle(
            (x - w/2, z - d/2), w, d,
            linewidth=1.5, edgecolor='black',
            facecolor=color, alpha=0.6
        )
        ax.add_patch(rect)
        ax.text(x, z, name, ha='center', va='center',
                fontsize=7, fontweight='bold', color='black')
    
    # Origin crosshair
    ax.axhline(y=0, color='red', linewidth=0.5, alpha=0.3)
    ax.axvline(x=0, color='red', linewidth=0.5, alpha=0.3)
    ax.plot(0, 0, 'r+', markersize=10)
    
    ax.set_aspect('equal')
    ax.set_xlabel(f'X ({unit})')
    ax.set_ylabel(f'Z ({unit})')
    ax.set_title('Top-Down Layout Plan')
    ax.grid(True, alpha=0.2)
    
    # Legend
    from matplotlib.patches import Patch
    legend_items = [Patch(facecolor=c, alpha=0.6, label=t) 
                    for t, c in TIER_COLORS.items() if t != "default"]
    ax.legend(handles=legend_items, loc='upper right', fontsize=8)
    
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Layout plan saved: {out_path}")


def draw_placements(data: list, out_path: str):
    """Plot placement points from geo.py output."""
    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    
    xs = [p.get("x", 0) for p in data]
    zs = [p.get("z", 0) for p in data]
    
    ax.scatter(xs, zs, c='#4a90d9', s=60, zorder=5, edgecolors='black', linewidth=0.5)
    
    for i, p in enumerate(data):
        ax.annotate(str(i), (p.get("x", 0), p.get("z", 0)),
                    textcoords="offset points", xytext=(5, 5), fontsize=7)
    
    ax.axhline(y=0, color='red', linewidth=0.5, alpha=0.3)
    ax.axvline(x=0, color='red', linewidth=0.5, alpha=0.3)
    ax.plot(0, 0, 'r+', markersize=10)
    
    ax.set_aspect('equal')
    ax.set_xlabel('X')
    ax.set_ylabel('Z')
    ax.set_title(f'Placements ({len(data)} points)')
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Placements plot saved: {out_path}")


def draw_boxes(data: list, out_path: str):
    """Draw simple bounding boxes for proportion checking."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    
    colors = ['#4a90d9', '#7cb342', '#ef5350', '#ffa726', '#ab47bc',
              '#26c6da', '#8d6e63', '#78909c']
    
    for i, box in enumerate(data):
        name = box.get("name", f"box{i}")
        x = box.get("x", 0)
        z = box.get("z", 0)
        w = box.get("w", 1)
        d = box.get("d", 1)
        color = colors[i % len(colors)]
        
        rect = patches.Rectangle(
            (x - w/2, z - d/2), w, d,
            linewidth=2, edgecolor=color,
            facecolor=color, alpha=0.25
        )
        ax.add_patch(rect)
        ax.text(x, z, f"{name}\n{w}×{d}",
                ha='center', va='center', fontsize=8, color=color)
    
    ax.axhline(y=0, color='red', linewidth=0.5, alpha=0.3)
    ax.axvline(x=0, color='red', linewidth=0.5, alpha=0.3)
    
    ax.set_aspect('equal')
    ax.autoscale()
    ax.margins(0.15)
    ax.set_xlabel('X')
    ax.set_ylabel('Z')
    ax.set_title('Bounding Box Overview')
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Box plot saved: {out_path}")


def draw_elevation(data: list, out_path: str, view: str = "front"):
    """Draw a side elevation showing vertical stacking — the view that catches
    half-height clips, floating parts, and Y-position errors.
    
    Input: list of {"name", "x", "z", "y" (center), "w", "d", "h"}
    Front elevation: X horizontal, Y vertical
    Side elevation: Z horizontal, Y vertical
    """
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))
    
    colors = ['#4a90d9', '#7cb342', '#ef5350', '#ffa726', '#ab47bc',
              '#26c6da', '#8d6e63', '#78909c']
    
    horiz_key = "x" if view == "front" else "z"
    width_key = "w" if view == "front" else "d"
    
    for i, part in enumerate(data):
        name = part.get("name", f"part{i}")
        pos_h = part.get(horiz_key, 0)
        pos_y = part.get("y", 0)    # CENTER y position
        w = part.get(width_key, 1)
        h = part.get("h", 1)
        color = colors[i % len(colors)]
        
        # Draw from bottom edge (pos_y - h/2)
        bottom = pos_y - h / 2
        rect = patches.Rectangle(
            (pos_h - w/2, bottom), w, h,
            linewidth=2, edgecolor=color,
            facecolor=color, alpha=0.3
        )
        ax.add_patch(rect)
        
        # Label with name + y-center + bottom/top edges
        label = f"{name}\ny={pos_y:.2f}\n[{bottom:.2f}–{pos_y + h/2:.2f}]"
        ax.text(pos_h, pos_y, label,
                ha='center', va='center', fontsize=7, color='black')
        
        # Draw y-center line (helps see alignment)
        ax.axhline(y=pos_y, color=color, linewidth=0.3,
                    alpha=0.4, linestyle=':')
    
    # Ground line
    ax.axhline(y=0, color='#8d6e63', linewidth=2.5, alpha=0.7)
    ax.text(0.02, 0.02, 'ground (y=0)', transform=ax.transAxes,
            fontsize=8, color='#8d6e63')
    
    ax.set_aspect('equal')
    ax.autoscale()
    ax.margins(0.15)
    
    # Light shading below ground (clipped to visible range)
    ylims = ax.get_ylim()
    if ylims[0] < 0:
        xlims = ax.get_xlim()
        ax.fill_between(xlims, ylims[0], 0, color='red', alpha=0.04, zorder=0)
    
    ax.set_xlabel(f'{horiz_key.upper()} (m)')
    ax.set_ylabel('Y (m)')
    title_prefix = "Front" if view == "front" else "Side"
    ax.set_title(f'{title_prefix} Elevation — Stacking Verification')
    ax.grid(True, alpha=0.2)
    
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Elevation plot saved: {out_path}")


def main():
    if not HAS_MPL:
        print("matplotlib not available — visualize.py requires: pip install matplotlib")
        print("This script is optional. The skill works without it.")
        sys.exit(1)
    
    ap = argparse.ArgumentParser(description="2D layout visualization for staged-3d-modeler")
    sub = ap.add_subparsers(dest="mode", required=True)
    
    p_plan = sub.add_parser("plan", help="Top-down floor plan from structured params")
    p_plan.add_argument("input", help="JSON file with room + parts")
    p_plan.add_argument("--out", default="layout.png")
    
    p_place = sub.add_parser("placements", help="Plot geo.py placement output")
    p_place.add_argument("input", help="JSON file from geo.py")
    p_place.add_argument("--out", default="placements.png")
    
    p_boxes = sub.add_parser("boxes", help="Simple bounding box plot")
    p_boxes.add_argument("input", help="JSON file with box list")
    p_boxes.add_argument("--out", default="boxes.png")
    
    p_elev = sub.add_parser("elevation", help="Front or side elevation showing vertical stacking")
    p_elev.add_argument("input", help="JSON file with parts (need name, x, z, y, w, d, h)")
    p_elev.add_argument("--view", choices=["front", "side"], default="front")
    p_elev.add_argument("--out", default="elevation.png")
    
    args = ap.parse_args()
    data = json.loads(Path(args.input).read_text())
    
    if args.mode == "plan":
        draw_plan(data, args.out)
    elif args.mode == "placements":
        draw_placements(data, args.out)
    elif args.mode == "boxes":
        draw_boxes(data, args.out)
    elif args.mode == "elevation":
        draw_elevation(data, args.out, view=args.view)


if __name__ == "__main__":
    main()
