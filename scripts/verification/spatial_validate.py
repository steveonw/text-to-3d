#!/usr/bin/env python3
"""
spatial_validate.py — Draw-and-validate spatial constraint checker.

Placement is measurement. Every object placed is immediately checked against
all constraints. Errors are caught at placement time, not after code generation.

Usage:
    python scripts/spatial_validate.py init 30 20 10        # WxDxH grid
    python scripts/spatial_validate.py place scene.json house_v1 10 0 5 --color red
    python scripts/spatial_validate.py check scene.json
    python scripts/spatial_validate.py query scene.json distance table_01 bar_01
    python scripts/spatial_validate.py query scene.json overlap house_01 house_02
    python scripts/spatial_validate.py query scene.json contents room_01
    python scripts/spatial_validate.py query scene.json fits 3 2.5 3 --at 10 0 5
    python scripts/spatial_validate.py view scene.json [--zoom 1]
"""

import json
import sys
import math
import argparse
from pathlib import Path


# ─── Scene data ──────────────────────────────────────

def init_scene(w, d, h):
    return {
        "grid": {"width": w, "depth": d, "height": h},
        "templates": {},
        "objects": [],
        "zones": [],
        "constraints": {
            "require_support": True,
            "no_overlap": True,
            "within_bounds": True,
            "respect_zones": True
        }
    }


def load_scene(path):
    with open(path) as f:
        return json.load(f)


def save_scene(scene, path):
    with open(path, 'w') as f:
        json.dump(scene, f, indent=2)


# ─── Bounding box helpers ────────────────────────────

def get_bbox(obj):
    """Return (xmin, ymin, zmin, xmax, ymax, zmax) for an object."""
    x, y, z = obj['x'], obj.get('y', 0), obj['z']
    w, h, d = obj['w'], obj.get('h', 1), obj['d']
    return (
        x - w / 2, y, z - d / 2,
        x + w / 2, y + h, z + d / 2
    )


def bboxes_overlap(a, b, margin=0):
    """Check if two bounding boxes overlap with optional margin."""
    ax0, ay0, az0, ax1, ay1, az1 = a
    bx0, by0, bz0, bx1, by1, bz1 = b
    return not (
        ax1 + margin <= bx0 or bx1 + margin <= ax0 or
        ay1 + margin <= by0 or by1 + margin <= ay0 or
        az1 + margin <= bz0 or bz1 + margin <= az0
    )


def bbox_within(inner, outer):
    """Check if inner bbox is fully within outer bbox."""
    return (
        inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] >= outer[2] and
        inner[3] <= outer[3] and inner[4] <= outer[4] and inner[5] <= outer[5]
    )


def distance_3d(a, b):
    """Euclidean distance between two object centers."""
    return math.sqrt(
        (a['x'] - b['x']) ** 2 +
        (a.get('y', 0) - b.get('y', 0)) ** 2 +
        (a['z'] - b['z']) ** 2
    )


# ─── Constraint checking ────────────────────────────

def check_placement(scene, new_obj):
    """Check if a new object can be placed. Returns (ok, issues)."""
    issues = []
    grid = scene['grid']
    constraints = scene.get('constraints', {})
    new_bbox = get_bbox(new_obj)

    # Bounds check
    if constraints.get('within_bounds', True):
        grid_bbox = (0, 0, 0, grid['width'], grid.get('height', 100), grid['depth'])
        if not bbox_within(new_bbox, grid_bbox):
            issues.append({
                "type": "out_of_bounds",
                "severity": "error",
                "message": f"{new_obj['name']} extends outside grid bounds",
                "detail": f"Object bbox: x[{new_bbox[0]:.1f},{new_bbox[3]:.1f}] "
                         f"y[{new_bbox[1]:.1f},{new_bbox[4]:.1f}] "
                         f"z[{new_bbox[2]:.1f},{new_bbox[5]:.1f}]",
                "suggestion": f"Grid is {grid['width']}×{grid['depth']}×{grid.get('height', '?')}. "
                             f"Shift object inward."
            })

    # Overlap check
    if constraints.get('no_overlap', True):
        for existing in scene['objects']:
            ex_bbox = get_bbox(existing)
            if bboxes_overlap(new_bbox, ex_bbox):
                # Calculate overlap amount
                ox = min(new_bbox[3], ex_bbox[3]) - max(new_bbox[0], ex_bbox[0])
                oz = min(new_bbox[5], ex_bbox[5]) - max(new_bbox[2], ex_bbox[2])
                issues.append({
                    "type": "overlap",
                    "severity": "error",
                    "message": f"{new_obj['name']} overlaps with {existing['name']}",
                    "detail": f"Overlap: {ox:.1f}u on X, {oz:.1f}u on Z",
                    "suggestion": f"Shift {new_obj['name']} by {ox:.1f}u on X or {oz:.1f}u on Z"
                })

    # Support check (is something below it, or is it on ground?)
    if constraints.get('require_support', True):
        obj_y = new_obj.get('y', 0)
        if obj_y > 0.01:  # Not on ground
            supported = False
            for existing in scene['objects']:
                ex_bbox = get_bbox(existing)
                # Check if existing object's top is at or near this object's bottom
                if abs(ex_bbox[4] - obj_y) < 0.1:
                    # Check horizontal overlap (is it actually above?)
                    if bboxes_overlap(
                        (new_bbox[0], 0, new_bbox[2], new_bbox[3], 1, new_bbox[5]),
                        (ex_bbox[0], 0, ex_bbox[2], ex_bbox[3], 1, ex_bbox[5])
                    ):
                        supported = True
                        break
            if not supported:
                issues.append({
                    "type": "floating",
                    "severity": "warning",
                    "message": f"{new_obj['name']} has no support at y={obj_y:.1f}",
                    "detail": "No object surface found beneath this object",
                    "suggestion": f"Place on ground (y=0) or on top of another object"
                })

    # Scale sanity check
    all_objs = scene['objects'] + [new_obj]
    if len(all_objs) >= 3:
        volumes = [(o['name'], o['w'] * o.get('h', 1) * o['d']) for o in all_objs]
        volumes.sort(key=lambda x: x[1])
        ratio = volumes[-1][1] / max(volumes[0][1], 0.001)
        if ratio > 1000:
            issues.append({
                "type": "scale_mismatch",
                "severity": "warning",
                "message": f"Extreme scale range: {volumes[0][0]} to {volumes[-1][0]}",
                "detail": f"Volume ratio: {ratio:.0f}x",
                "suggestion": "Check that all objects use the same unit scale"
            })

    # Keepout zone check
    if constraints.get('respect_zones', True):
        for zone in scene.get('zones', []):
            zone_bbox = (
                zone['xmin'], zone.get('ymin', 0), zone['zmin'],
                zone['xmax'], zone.get('ymax', 100), zone['zmax']
            )
            if bboxes_overlap(new_bbox, zone_bbox):
                ox = min(new_bbox[3], zone_bbox[3]) - max(new_bbox[0], zone_bbox[0])
                oz = min(new_bbox[5], zone_bbox[5]) - max(new_bbox[2], zone_bbox[2])
                issues.append({
                    "type": "zone_violation",
                    "severity": "error",
                    "message": f"{new_obj['name']} is inside keepout zone '{zone['name']}'",
                    "detail": f"Overlap with zone: {ox:.1f}u on X, {oz:.1f}u on Z",
                    "suggestion": f"Move {new_obj['name']} outside '{zone['name']}' "
                                 f"(x: {zone['xmin']:.0f}–{zone['xmax']:.0f}, "
                                 f"z: {zone['zmin']:.0f}–{zone['zmax']:.0f})"
                })

    ok = all(i['severity'] != 'error' for i in issues)
    return ok, issues


# ─── Full scene validation ───────────────────────────

def validate_scene(scene):
    """Run all checks on an existing scene. Returns list of issues."""
    all_issues = []
    constraints = scene.get('constraints', {})
    grid = scene['grid']
    grid_bbox = (0, 0, 0, grid['width'], grid.get('height', 100), grid['depth'])

    for i, obj in enumerate(scene['objects']):
        bbox = get_bbox(obj)

        # Bounds
        if constraints.get('within_bounds', True):
            if not bbox_within(bbox, grid_bbox):
                all_issues.append(f"ERROR: {obj['name']} out of bounds")

        # Overlap with others
        if constraints.get('no_overlap', True):
            for j, other in enumerate(scene['objects']):
                if j <= i:
                    continue
                if bboxes_overlap(get_bbox(obj), get_bbox(other)):
                    all_issues.append(f"ERROR: {obj['name']} overlaps {other['name']}")

    # Symmetry check (named error 5)
    if len(scene['objects']) >= 4:
        cx = grid['width'] / 2
        cz = grid['depth'] / 2
        quadrants = [0, 0, 0, 0]  # NW, NE, SW, SE
        for obj in scene['objects']:
            qi = (0 if obj['x'] < cx else 1) + (0 if obj['z'] < cz else 2)
            quadrants[qi] += 1
        filled = sum(1 for q in quadrants if q > 0)
        if filled <= 1:
            all_issues.append("WARNING: All objects in one quadrant — likely layout issue")
        max_q, min_q = max(quadrants), min(q for q in quadrants if q > 0) if any(quadrants) else 0
        if min_q > 0 and max_q > 0 and max_q / min_q > 3:
            all_issues.append(f"WARNING: Unbalanced layout — quadrant counts: {quadrants}")

    # Scale uniformity check (named error 4)
    if len(scene['objects']) >= 3:
        sizes = sorted(scene['objects'], key=lambda o: o['w'] * o.get('h', 1) * o['d'])
        smallest = sizes[0]
        largest = sizes[-1]
        sv = smallest['w'] * smallest.get('h', 1) * smallest['d']
        lv = largest['w'] * largest.get('h', 1) * largest['d']
        if sv > 0 and lv / sv > 500:
            all_issues.append(
                f"WARNING: Scale range very large — "
                f"smallest: {smallest['name']} ({sv:.1f}u³), "
                f"largest: {largest['name']} ({lv:.1f}u³)"
            )

    # Zone violation check
    if constraints.get('respect_zones', True):
        for obj in scene['objects']:
            obj_bbox = get_bbox(obj)
            for zone in scene.get('zones', []):
                zone_bbox = (
                    zone['xmin'], zone.get('ymin', 0), zone['zmin'],
                    zone['xmax'], zone.get('ymax', 100), zone['zmax']
                )
                if bboxes_overlap(obj_bbox, zone_bbox):
                    all_issues.append(
                        f"ERROR: {obj['name']} violates keepout zone '{zone['name']}'"
                    )

    if not all_issues:
        all_issues.append("✓ All checks passed")

    return all_issues


# ─── Queries ─────────────────────────────────────────

def query_distance(scene, name_a, name_b):
    a = next((o for o in scene['objects'] if o['name'] == name_a), None)
    b = next((o for o in scene['objects'] if o['name'] == name_b), None)
    if not a or not b:
        return f"Object not found: {name_a if not a else name_b}"
    d = distance_3d(a, b)
    return f"Distance {name_a} → {name_b}: {d:.2f} units (center to center)"


def query_overlap(scene, name_a, name_b):
    a = next((o for o in scene['objects'] if o['name'] == name_a), None)
    b = next((o for o in scene['objects'] if o['name'] == name_b), None)
    if not a or not b:
        return f"Object not found"
    if bboxes_overlap(get_bbox(a), get_bbox(b)):
        return f"YES: {name_a} and {name_b} overlap"
    else:
        return f"NO: {name_a} and {name_b} do not overlap"


def query_fits(scene, w, h, d, x, y, z):
    """Check if an object of size w×h×d fits at position x,y,z."""
    test_obj = {"name": "_test", "x": x, "y": y, "z": z, "w": w, "h": h, "d": d}
    ok, issues = check_placement(scene, test_obj)
    if ok:
        return f"YES: {w}×{h}×{d} fits at ({x},{y},{z})"
    else:
        msgs = [i['message'] + ' — ' + i['suggestion'] for i in issues]
        return f"NO: {w}×{h}×{d} does not fit at ({x},{y},{z})\n" + '\n'.join(msgs)


# ─── Simple ASCII top view for quick check ───────────

def quick_view(scene, zoom=1):
    """Render a quick top-down character grid view."""
    grid = scene['grid']
    scale = max(1, int(2 / zoom))
    gw = grid['width'] // scale
    gd = grid['depth'] // scale
    view = [['·'] * gw for _ in range(gd)]

    # Draw keepout zones first (background)
    for zone in scene.get('zones', []):
        zx0 = int(zone['xmin'] / scale)
        zx1 = int(zone['xmax'] / scale)
        zz0 = int(zone['zmin'] / scale)
        zz1 = int(zone['zmax'] / scale)
        for dz in range(max(0, zz0), min(gd, zz1)):
            for dx in range(max(0, zx0), min(gw, zx1)):
                view[dz][dx] = '░'

    # Draw objects on top
    for obj in scene['objects']:
        cx = int(obj['x'] / scale)
        cz = int(obj['z'] / scale)
        hw = max(1, int(obj['w'] / scale / 2))
        hd = max(1, int(obj['d'] / scale / 2))
        char = obj.get('char', '█')
        for dz in range(-hd, hd + 1):
            for dx in range(-hw, hw + 1):
                px, pz = cx + dx, cz + dz
                if 0 <= px < gw and 0 <= pz < gd:
                    view[pz][px] = char

    lines = []
    lines.append(f"  TOP VIEW  {grid['width']}×{grid['depth']}  zoom={zoom}x")
    lines.append('  ┌' + '─' * gw + '┐')
    for z in range(gd):
        lines.append(f"{z:2d}│" + ''.join(view[z]) + "│")
    lines.append('  └' + '─' * gw + '┘')
    return '\n'.join(lines)


# ─── CLI ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Spatial constraint validator')
    parser.add_argument('command', choices=['init', 'place', 'zone', 'check', 'query', 'view'])
    parser.add_argument('args', nargs='*')
    parser.add_argument('--zoom', type=float, default=1.0)
    parser.add_argument('--color', type=str, default=None)
    parser.add_argument('--char', type=str, default='█')
    parser.add_argument('--at', nargs=3, type=float, default=None)
    parsed = parser.parse_args()

    if parsed.command == 'init':
        if len(parsed.args) < 3:
            print("Usage: init <width> <depth> <height> [output.json]")
            sys.exit(1)
        w, d, h = int(parsed.args[0]), int(parsed.args[1]), int(parsed.args[2])
        scene = init_scene(w, d, h)
        out = parsed.args[3] if len(parsed.args) > 3 else 'scene.json'
        save_scene(scene, out)
        print(f"Created {w}×{d}×{h} scene → {out}")

    elif parsed.command == 'zone':
        if len(parsed.args) < 6:
            print("Usage: zone <scene.json> <name> <xmin> <zmin> <xmax> <zmax>")
            sys.exit(1)
        scene = load_scene(parsed.args[0])
        zone = {
            "name": parsed.args[1],
            "xmin": float(parsed.args[2]),
            "zmin": float(parsed.args[3]),
            "xmax": float(parsed.args[4]),
            "zmax": float(parsed.args[5]),
        }
        if 'zones' not in scene:
            scene['zones'] = []
        scene['zones'].append(zone)
        save_scene(scene, parsed.args[0])
        print(f"  ✓ Added keepout zone '{zone['name']}' "
              f"x[{zone['xmin']:.0f},{zone['xmax']:.0f}] "
              f"z[{zone['zmin']:.0f},{zone['zmax']:.0f}]")

    elif parsed.command == 'place':
        if len(parsed.args) < 5:
            print("Usage: place <scene.json> <name> <x> <y> <z> [w] [h] [d]")
            sys.exit(1)
        scene = load_scene(parsed.args[0])
        obj = {
            "name": parsed.args[1],
            "x": float(parsed.args[2]),
            "y": float(parsed.args[3]),
            "z": float(parsed.args[4]),
            "w": float(parsed.args[5]) if len(parsed.args) > 5 else 1,
            "h": float(parsed.args[6]) if len(parsed.args) > 6 else 1,
            "d": float(parsed.args[7]) if len(parsed.args) > 7 else 1,
            "char": parsed.char,
        }
        if parsed.color:
            obj['color'] = parsed.color

        ok, issues = check_placement(scene, obj)
        for issue in issues:
            prefix = "✗" if issue['severity'] == 'error' else "⚠"
            print(f"  {prefix} {issue['message']}")
            print(f"    {issue['detail']}")
            print(f"    → {issue['suggestion']}")

        if ok:
            scene['objects'].append(obj)
            save_scene(scene, parsed.args[0])
            print(f"  ✓ Placed {obj['name']} at ({obj['x']}, {obj['y']}, {obj['z']})")
        else:
            print(f"  ✗ Placement rejected — fix issues above")

    elif parsed.command == 'check':
        scene = load_scene(parsed.args[0])
        issues = validate_scene(scene)
        for issue in issues:
            print(f"  {issue}")

    elif parsed.command == 'query':
        scene = load_scene(parsed.args[0])
        qtype = parsed.args[1]
        if qtype == 'distance':
            print(query_distance(scene, parsed.args[2], parsed.args[3]))
        elif qtype == 'overlap':
            print(query_overlap(scene, parsed.args[2], parsed.args[3]))
        elif qtype == 'fits':
            w, h, d = float(parsed.args[2]), float(parsed.args[3]), float(parsed.args[4])
            x, y, z = parsed.at or (0, 0, 0)
            print(query_fits(scene, w, h, d, x, y, z))

    elif parsed.command == 'view':
        scene = load_scene(parsed.args[0])
        print(quick_view(scene, parsed.zoom))


if __name__ == '__main__':
    main()
