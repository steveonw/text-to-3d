#!/usr/bin/env python3
"""
geo.py — Geometry helpers for the staged-3d-modeler skill.

Run standalone or import individual functions.
Covers: placement arrays, arc/dome/taper profiles, coordinate transforms,
parameter validation, and JSON export for Three.js consumption.

Usage examples (standalone):
    python geo.py grid --nx 4 --nz 3 --sx 2.5 --sz 2.5
    python geo.py ring --n 12 --r 5.0
    python geo.py arc --r 3.0 --angle 180 --n 24
    python geo.py dome --r 5.0 --n 16
    python geo.py taper --r-bottom 2.0 --r-top 0.5 --h 6.0 --n 12
    python geo.py lathe --points "0,0 1,0 1.2,1 0.8,3 0,3.5"
    python geo.py ogee --w 1.0 --h 0.3 --n 16
    python geo.py validate --json params.json
    python geo.py mirror --points "1,0,2 3,1,4" --axis x

Output format flag (profile commands only):
    --format dict    {r, y} or {x, y} dicts (default)
    --format flat    [[x, y], ...] arrays for direct LatheGeometry / ExtrudeGeometry use
"""

import json
import math
import sys
from typing import Optional


# ---------------------------------------------------------------------------
# Placement generators
# ---------------------------------------------------------------------------

def grid_placements(
    nx: int, nz: int,
    spacing_x: float, spacing_z: float,
    center: bool = True,
    y: float = 0.0,
) -> list[dict]:
    """Rectangular grid of positions on the XZ plane."""
    pts = []
    ox = (nx - 1) * spacing_x / 2 if center else 0
    oz = (nz - 1) * spacing_z / 2 if center else 0
    for ix in range(nx):
        for iz in range(nz):
            pts.append({
                "x": round(ix * spacing_x - ox, 6),
                "y": y,
                "z": round(iz * spacing_z - oz, 6),
            })
    return pts


def ring_placements(
    n: int, radius: float,
    y: float = 0.0,
    start_angle_deg: float = 0.0,
    end_angle_deg: float = 360.0,
    include_end: bool = False,
) -> list[dict]:
    """Points equally spaced around a circular arc on the XZ plane."""
    pts = []
    sa = math.radians(start_angle_deg)
    ea = math.radians(end_angle_deg)
    count = n + 1 if include_end else n
    step = (ea - sa) / max(n, 1)
    for i in range(count):
        a = sa + i * step
        pts.append({
            "x": round(radius * math.cos(a), 6),
            "y": y,
            "z": round(radius * math.sin(a), 6),
            "angle_deg": round(math.degrees(a), 4),
        })
    return pts


def linear_placements(
    n: int,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
) -> list[dict]:
    """Evenly spaced points along a line segment in 3D."""
    pts = []
    for i in range(n):
        t = i / max(n - 1, 1)
        pts.append({
            "x": round(start[0] + t * (end[0] - start[0]), 6),
            "y": round(start[1] + t * (end[1] - start[1]), 6),
            "z": round(start[2] + t * (end[2] - start[2]), 6),
        })
    return pts


def stacked_placements(
    n: int,
    spacing_y: float,
    base_y: float = 0.0,
    x: float = 0.0,
    z: float = 0.0,
) -> list[dict]:
    """Vertically stacked positions."""
    return [
        {"x": x, "y": round(base_y + i * spacing_y, 6), "z": z}
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# Profile / curve generators
# ---------------------------------------------------------------------------

def arc_points(
    radius: float,
    angle_deg: float = 180.0,
    n: int = 24,
    center: tuple[float, float] = (0.0, 0.0),
    start_deg: float = 0.0,
) -> list[dict]:
    """2D arc as (x, y) points. Useful for arched openings, windows, bridges."""
    pts = []
    sa = math.radians(start_deg)
    span = math.radians(angle_deg)
    for i in range(n + 1):
        a = sa + span * i / n
        pts.append({
            "x": round(center[0] + radius * math.cos(a), 6),
            "y": round(center[1] + radius * math.sin(a), 6),
        })
    return pts


def dome_profile(
    radius: float,
    n: int = 16,
    squash_y: float = 1.0,
) -> list[dict]:
    """Half-sphere profile from base to apex as (r, y) for lathe geometry.
    squash_y < 1 makes it flatter, > 1 makes it taller."""
    pts = []
    for i in range(n + 1):
        a = math.pi / 2 * i / n  # 0 to pi/2
        pts.append({
            "r": round(radius * math.cos(a), 6),
            "y": round(radius * math.sin(a) * squash_y, 6),
        })
    return pts


def taper_profile(
    r_bottom: float,
    r_top: float,
    height: float,
    n: int = 12,
    curve_power: float = 1.0,
) -> list[dict]:
    """Tapered cylinder profile as (r, y). curve_power > 1 = concave, < 1 = convex."""
    pts = []
    for i in range(n + 1):
        t = i / n
        r = r_bottom + (r_top - r_bottom) * (t ** curve_power)
        pts.append({
            "r": round(r, 6),
            "y": round(height * t, 6),
        })
    return pts


def lathe_points_from_string(points_str: str) -> list[dict]:
    """Parse 'r,y r,y ...' into lathe-ready profile points."""
    pts = []
    for pair in points_str.strip().split():
        r, y = pair.split(",")
        pts.append({"r": float(r), "y": float(y)})
    return pts


def ogee_profile(
    width: float,
    height: float,
    n: int = 20,
) -> list[dict]:
    """S-curve (ogee) profile — common in moldings and domes.
    Returns (x, y) from (0,0) to (width, height)."""
    pts = []
    for i in range(n + 1):
        t = i / n
        # smooth S via cubic hermite
        s = 3 * t * t - 2 * t * t * t
        pts.append({
            "x": round(width * t, 6),
            "y": round(height * s, 6),
        })
    return pts


# ---------------------------------------------------------------------------
# Transforms
# ---------------------------------------------------------------------------

def mirror_points(
    points: list[dict],
    axis: str = "x",
    include_originals: bool = True,
) -> list[dict]:
    """Mirror 3D points across an axis plane (x mirrors across YZ, etc.)."""
    result = list(points) if include_originals else []
    for p in points:
        mp = dict(p)
        mp[axis] = -mp[axis]
        # avoid duplicates on the plane
        if include_originals and mp[axis] == 0:
            continue
        result.append(mp)
    return result


def rotate_points_y(
    points: list[dict],
    angle_deg: float,
) -> list[dict]:
    """Rotate 3D points around the Y axis."""
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    result = []
    for p in points:
        result.append({
            "x": round(p["x"] * ca + p["z"] * sa, 6),
            "y": p["y"],
            "z": round(-p["x"] * sa + p["z"] * ca, 6),
        })
    return result


def translate_points(
    points: list[dict],
    dx: float = 0, dy: float = 0, dz: float = 0,
) -> list[dict]:
    """Offset all points."""
    return [
        {
            "x": round(p["x"] + dx, 6),
            "y": round(p["y"] + dy, 6),
            "z": round(p["z"] + dz, 6),
        }
        for p in points
    ]


# ---------------------------------------------------------------------------
# Parameter validation
# ---------------------------------------------------------------------------

def validate_params(params: dict) -> list[str]:
    """Check a parameter dict for common issues.
    Returns a list of warnings (empty = all good)."""
    warnings = []
    for k, v in params.items():
        if isinstance(v, (int, float)):
            if v < 0 and any(word in k.lower() for word in
                            ["radius", "width", "height", "depth", "length",
                             "diameter", "thickness", "spacing"]):
                warnings.append(f"'{k}' is negative ({v}) — probably wrong for a dimension.")
            if v == 0 and any(word in k.lower() for word in
                              ["radius", "width", "height", "depth", "length",
                               "diameter", "thickness"]):
                warnings.append(f"'{k}' is zero — degenerate geometry.")
    # check for unit mixing hints
    values = [v for v in params.values() if isinstance(v, (int, float)) and v > 0]
    if values:
        biggest, smallest = max(values), min(values)
        if biggest / max(smallest, 0.001) > 1000:
            warnings.append(
                f"Ratio of largest to smallest value is {biggest/smallest:.0f}:1 "
                f"— possible unit mixing (mm vs m?)."
            )
    return warnings


# ---------------------------------------------------------------------------
# Export helpers
# ---------------------------------------------------------------------------

def to_threejs_positions(points: list[dict]) -> list[list[float]]:
    """Convert to [[x,y,z], ...] for direct use in Three.js Float32Array."""
    return [[p["x"], p["y"], p["z"]] for p in points]


def flatten_profile(points: list[dict]) -> list[list[float]]:
    """Convert profile dicts to [[x, y], ...] arrays for LatheGeometry / ExtrudeGeometry.
    Handles both {r, y} and {x, y} keyed dicts."""
    out = []
    for p in points:
        x = p.get("r", p.get("x", 0.0))
        y = p.get("y", 0.0)
        out.append([round(x, 6), round(y, 6)])
    return out


def to_json(data, pretty: bool = True) -> str:
    return json.dumps(data, indent=2 if pretty else None)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    cmd = sys.argv[1]

    def arg(name, default=None, type_fn=str):
        flag = f"--{name}"
        if flag in sys.argv:
            return type_fn(sys.argv[sys.argv.index(flag) + 1])
        if default is not None:
            return default
        print(f"Missing required arg: {flag}")
        sys.exit(1)

    fmt = arg("format", "dict", str)  # "dict" or "flat"
    profile_commands = {"arc", "dome", "taper", "ogee", "lathe"}

    if cmd == "grid":
        result = grid_placements(
            nx=arg("nx", type_fn=int),
            nz=arg("nz", type_fn=int),
            spacing_x=arg("sx", type_fn=float),
            spacing_z=arg("sz", type_fn=float),
        )
    elif cmd == "ring":
        result = ring_placements(
            n=arg("n", type_fn=int),
            radius=arg("r", type_fn=float),
            start_angle_deg=arg("start", 0, float),
            end_angle_deg=arg("end", 360, float),
            include_end=("--include-end" in sys.argv),
        )
    elif cmd == "arc":
        result = arc_points(
            radius=arg("r", type_fn=float),
            angle_deg=arg("angle", 180, float),
            n=arg("n", 24, int),
        )
    elif cmd == "dome":
        result = dome_profile(
            radius=arg("r", type_fn=float),
            n=arg("n", 16, int),
            squash_y=arg("squash", 1.0, float),
        )
    elif cmd == "taper":
        result = taper_profile(
            r_bottom=arg("r-bottom", type_fn=float),
            r_top=arg("r-top", type_fn=float),
            height=arg("h", type_fn=float),
            n=arg("n", 12, int),
            curve_power=arg("curve", 1.0, float),
        )
    elif cmd == "lathe":
        pts_str = arg("points", type_fn=str)
        result = lathe_points_from_string(pts_str)
    elif cmd == "validate":
        path = arg("json", type_fn=str)
        with open(path) as f:
            params = json.load(f)
        result = validate_params(params)
        if not result:
            result = ["All clear — no warnings."]
    elif cmd == "mirror":
        pts_str = arg("points", type_fn=str)
        axis = arg("axis", "x", str)
        points = []
        for triple in pts_str.strip().split():
            x, y, z = triple.split(",")
            points.append({"x": float(x), "y": float(y), "z": float(z)})
        result = mirror_points(points, axis=axis)
    elif cmd == "ogee":
        result = ogee_profile(
            width=arg("w", type_fn=float),
            height=arg("h", type_fn=float),
            n=arg("n", 20, int),
        )
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: grid, ring, arc, dome, taper, lathe, ogee, validate, mirror")
        sys.exit(1)

    # Apply flat format for profile commands
    if fmt == "flat" and cmd in profile_commands and isinstance(result, list) and result and isinstance(result[0], dict):
        result = flatten_profile(result)

    print(to_json(result))


if __name__ == "__main__":
    _cli()
