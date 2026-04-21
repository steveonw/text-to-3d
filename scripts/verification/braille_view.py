#!/usr/bin/env python3
"""
braille_view.py — Render spatial layouts as braille text for cheap verification.

Usage:
    python scripts/braille_view.py top layout.json [--zoom 1]
    python scripts/braille_view.py front layout.json [--zoom 1]
    python scripts/braille_view.py side layout.json [--zoom 1]
    python scripts/braille_view.py curve "FLAT(3) GENTLE-ARC(4) POINTED(1) mirror"
    python scripts/braille_view.py shape <name>
    python scripts/braille_view.py shapes

Layout JSON format:
{
    "unit": "m",
    "room": {"width": 14, "depth": 10, "height": 8},
    "parts": [
        {"name": "base", "x": 0, "z": 0, "y": 1.0, "w": 14, "d": 10, "h": 2.0},
        {"name": "walls", "x": 0, "z": 0, "y": 4.5, "w": 12, "d": 8, "h": 5.0}
    ]
}
"""

import json
import sys
import math
import argparse

# ─── Braille encoding ────────────────────────────────
# Braille cell: 2 columns × 4 rows
# Dot numbering:  1 4    Bit values:  1   8
#                 2 5                  2  16
#                 3 6                  4  32
#                 7 8                 64 128

BRAILLE_BASE = 0x2800
DOT_BITS = [
    [1, 8],      # row 0 (top)
    [2, 16],     # row 1
    [4, 32],     # row 2
    [64, 128],   # row 3 (bottom)
]


def make_braille_char(dots):
    """dots is a 4×2 array of booleans (rows × cols). Returns a braille unicode char."""
    val = 0
    for r in range(4):
        for c in range(2):
            if r < len(dots) and c < len(dots[r]) and dots[r][c]:
                val |= DOT_BITS[r][c]
    return chr(BRAILLE_BASE + val)


class BrailleCanvas:
    """Pixel canvas that renders to braille characters."""

    def __init__(self, pixel_w, pixel_h):
        self.pw = pixel_w
        self.ph = pixel_h
        # Ensure dimensions align to braille cell size
        self.cw = math.ceil(pixel_w / 2)   # char columns
        self.ch = math.ceil(pixel_h / 4)   # char rows
        self.pixels = [[False] * pixel_w for _ in range(pixel_h)]

    def set(self, x, y):
        """Set a pixel. Origin is bottom-left."""
        fy = self.ph - 1 - int(y)
        fx = int(x)
        if 0 <= fx < self.pw and 0 <= fy < self.ph:
            self.pixels[fy][fx] = True

    def fill_rect(self, x, y, w, h):
        """Fill a rectangle. Origin is bottom-left."""
        for dy in range(int(h)):
            for dx in range(int(w)):
                self.set(x + dx, y + dy)

    def line(self, x0, y0, x1, y1):
        """Bresenham line."""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0)
            if abs(x0 - x1) < 1 and abs(y0 - y1) < 1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def render(self):
        """Return braille string."""
        lines = []
        for cr in range(self.ch):
            row_chars = []
            for cc in range(self.cw):
                dots = []
                for dr in range(4):
                    dot_row = []
                    for dc in range(2):
                        py = cr * 4 + dr
                        px = cc * 2 + dc
                        if py < self.ph and px < self.pw:
                            dot_row.append(self.pixels[py][px])
                        else:
                            dot_row.append(False)
                    dots.append(dot_row)
                row_chars.append(make_braille_char(dots))
            lines.append(''.join(row_chars))
        return '\n'.join(lines)


# ─── View generators ─────────────────────────────────

def load_layout(path):
    with open(path) as f:
        return json.load(f)


def render_top(layout, zoom=1):
    """Top-down view: X horizontal, Z vertical."""
    room = layout.get('room', {})
    rw = room.get('width', 20)
    rd = room.get('depth', 20)
    scale = 2 / zoom  # pixels per unit
    pw = int(rw * scale)
    ph = int(rd * scale)
    canvas = BrailleCanvas(pw, ph)

    # Draw room boundary
    canvas.line(0, 0, pw - 1, 0)
    canvas.line(pw - 1, 0, pw - 1, ph - 1)
    canvas.line(pw - 1, ph - 1, 0, ph - 1)
    canvas.line(0, ph - 1, 0, 0)

    # Draw parts as filled rectangles
    cx, cz = rw / 2, rd / 2
    for part in layout.get('parts', []):
        px = (part['x'] + cx - part['w'] / 2) * scale
        pz = (part['z'] + cz - part['d'] / 2) * scale
        pw_p = part['w'] * scale
        ph_p = part['d'] * scale
        canvas.fill_rect(px, pz, pw_p, ph_p)

    header = f"TOP (X×Z) zoom={zoom}x  1char≈{1/scale:.1f}u"
    return f"{header}\n{canvas.render()}"


def render_front(layout, zoom=1):
    """Front elevation: X horizontal, Y vertical."""
    room = layout.get('room', {})
    rw = room.get('width', 20)
    rh = room.get('height', 10)
    scale = 2 / zoom
    pw = int(rw * scale)
    ph = int(rh * scale)
    canvas = BrailleCanvas(pw, ph)

    # Ground line
    canvas.line(0, 0, pw - 1, 0)

    cx = rw / 2
    for part in layout.get('parts', []):
        px = (part['x'] + cx - part['w'] / 2) * scale
        py = (part['y'] - part['h'] / 2) * scale  # y is center
        pw_p = part['w'] * scale
        ph_p = part['h'] * scale
        canvas.fill_rect(px, py, pw_p, ph_p)

    header = f"FRONT (X×Y) zoom={zoom}x  1char≈{1/scale:.1f}u"
    return f"{header}\n{canvas.render()}"


def render_side(layout, zoom=1):
    """Side elevation: Z horizontal, Y vertical."""
    room = layout.get('room', {})
    rd = room.get('depth', 20)
    rh = room.get('height', 10)
    scale = 2 / zoom
    pw = int(rd * scale)
    ph = int(rh * scale)
    canvas = BrailleCanvas(pw, ph)

    canvas.line(0, 0, pw - 1, 0)

    cz = rd / 2
    for part in layout.get('parts', []):
        px = (part['z'] + cz - part.get('d', part.get('w', 1)) / 2) * scale
        py = (part['y'] - part['h'] / 2) * scale
        pw_p = part.get('d', part.get('w', 1)) * scale
        ph_p = part['h'] * scale
        canvas.fill_rect(px, py, pw_p, ph_p)

    header = f"SIDE (Z×Y) zoom={zoom}x  1char≈{1/scale:.1f}u"
    return f"{header}\n{canvas.render()}"


# ─── Piecewise curve → coordinates ───────────────────
#
# Each segment is a circular arc defined by:
#   - length: distance traveled along the arc
#   - turn: how many degrees the heading changes over this segment
#
# The cursor carries a position (cx, cy) and heading angle.
# Heading 0° = rightward (+x), 90° = upward (+y).
#
# This produces clean, continuous curves suitable for
# Three.js LatheGeometry and ExtrudeGeometry profiles.

SEGMENT_DEFS = {
    # name:         (turn_degrees,)
    # turn > 0 curves upward (counterclockwise), < 0 curves downward
    'FLAT':         (0,),        # straight in current direction
    'GENTLE-ARC':   (15,),       # 15° turn over the segment length
    'MEDIUM-ARC':   (30,),       # 30° turn
    'STEEP-ARC':    (60,),       # 60° turn
    'SHARP-ARC':    (80,),       # near-right-angle turn
    'POINTED':      (0,),        # straight up — special: forces heading to 90°
    'STRAIGHT':     (0,),        # alias for FLAT
    'DOWN-GENTLE':  (-15,),      # 15° turn downward
    'DOWN-MEDIUM':  (-30,),      # 30° turn downward
    'DOWN-STEEP':   (-60,),      # 60° turn downward
}


def _arc_points(cx, cy, heading_deg, length, turn_deg, steps):
    """Generate points along a circular arc.

    Args:
        cx, cy: start position
        heading_deg: current direction in degrees (0=right, 90=up)
        length: arc length
        turn_deg: total heading change over the arc (positive = counterclockwise)
        steps: number of sample points

    Returns:
        list of (x, y) points, new_heading
    """
    points = []
    h0 = math.radians(heading_deg)
    dh = math.radians(turn_deg)

    if abs(turn_deg) < 0.01:
        # Straight line — no curvature
        for i in range(1, steps + 1):
            t = i / steps
            d = length * t
            px = cx + d * math.cos(h0)
            py = cy + d * math.sin(h0)
            points.append((round(px, 4), round(py, 4)))
        new_heading = heading_deg
    else:
        # Circular arc: radius = length / |dh|
        radius = length / abs(dh)
        for i in range(1, steps + 1):
            t = i / steps
            h_t = h0 + dh * t
            # Integrate position along the arc
            # Using exact formula: center of curvature + radius offset
            # Simpler: accumulate small steps
            px = cx
            py = cy
            substeps = max(steps * 2, 20)
            for j in range(1, int(substeps * t) + 1):
                st = j / substeps
                h_s = h0 + dh * st
                ds = length / substeps
                px += ds * math.cos(h_s)
                py += ds * math.sin(h_s)
            points.append((round(px, 4), round(py, 4)))
        new_heading = heading_deg + turn_deg

    return points, new_heading


def parse_curve(desc):
    """Parse piecewise curve description into coordinate array.

    Format: "FLAT(3) GENTLE-ARC(4) STEEP-ARC(2) POINTED(1) mirror"

    Each segment is NAME(length). Segments connect end-to-end with
    continuous heading. 'mirror' reflects the curve around its final X.

    For profiles (rooflines, domes, arches):
        Starting heading is 0° (rightward).
        FLAT keeps it horizontal. ARC segments curve upward.
        POINTED forces the heading to 90° for a vertical finish.

    Returns: list of [x, y] coordinate pairs.
    """
    tokens = desc.strip().split()
    points = [[0, 0]]
    cx, cy = 0.0, 0.0
    heading = 0.0  # degrees, 0 = rightward, 90 = upward

    do_mirror = False
    segments = []

    for tok in tokens:
        tok_clean = tok.strip('→ ')
        if tok_clean.lower() == 'mirror':
            do_mirror = True
            continue
        if '(' in tok_clean:
            name = tok_clean[:tok_clean.index('(')].upper()
            length = float(tok_clean[tok_clean.index('(') + 1:tok_clean.index(')')])
            segments.append((name, length))

    for name, length in segments:
        seg_def = SEGMENT_DEFS.get(name)
        if not seg_def:
            # Unknown segment, treat as flat
            seg_def = (0,)

        turn = seg_def[0]

        # POINTED is special: force heading to 90° (straight up)
        if name == 'POINTED':
            heading = 90.0
            turn = 0

        steps = max(int(length * 4), 4)
        arc_pts, new_heading = _arc_points(cx, cy, heading, length, turn, steps)

        for pt in arc_pts:
            points.append([pt[0], pt[1]])

        if arc_pts:
            cx, cy = arc_pts[-1]
        heading = new_heading

    if do_mirror:
        max_x = max(p[0] for p in points)
        mirrored = [[round(2 * max_x - p[0], 4), p[1]] for p in reversed(points[1:])]
        points.extend(mirrored)

    return points


# ─── Shape vocabulary display ────────────────────────

SHAPE_VOCAB = {
    'triangle-equilateral': '⠀⠀⠊⠀⠀\n⠀⠠⣿⠄⠀\n⣀⣿⣿⣿⣀',
    'triangle-tall':        '⠀⠀⠊⠀⠀\n⠀⠀⣿⠀⠀\n⠀⠠⣿⠄⠀\n⣀⣿⣿⣿⣀',
    'triangle-wide':        '⠀⠀⠀⠊⠀⠀⠀\n⠀⣠⣿⣿⣿⣄⠀\n⣿⣿⣿⣿⣿⣿⣿',
    'arch-round':           '⠀⣠⣤⣤⣄⠀\n⢸⠀⠀⠀⠀⡇\n⢸⠀⠀⠀⠀⡇',
    'arch-pointed':         '⠀⠀⠀⡆⠀⠀⠀\n⠀⢀⡴⠁⠳⡀⠀\n⢸⠉⠀⠀⠀⠈⡇\n⢸⠀⠀⠀⠀⠀⡇',
    'arch-flat':            '⣤⣤⣤⣤⣤⣤\n⢸⠀⠀⠀⠀⡇\n⢸⠀⠀⠀⠀⡇',
    'dome-round':           '⠀⣠⣴⣦⣄⠀\n⣰⣿⣿⣿⣿⣆\n⣿⣿⣿⣿⣿⣿',
    'dome-onion':           '⠀⠀⢀⡀⠀⠀\n⠀⢀⣿⡀⠀⠀\n⠀⣾⣿⣷⠀⠀\n⢸⣿⣿⣿⡇⠀\n⠀⣿⣿⣿⠀⠀',
    'box':                  '⣿⣿⣿⣿\n⣿⣿⣿⣿\n⣿⣿⣿⣿',
    'cylinder':             '⠀⣤⣤⠀\n⠀⣿⣿⠀\n⠀⣿⣿⠀\n⠀⣿⣿⠀\n⠀⣤⣤⠀',
    'cross-section-I':      '⣿⣿⣿⣿⣿⣿\n⠀⠀⣿⣿⠀⠀\n⠀⠀⣿⣿⠀⠀\n⣿⣿⣿⣿⣿⣿',
    'cross-section-L':      '⣿⣿⠀⠀\n⣿⣿⠀⠀\n⣿⣿⠀⠀\n⣿⣿⣿⣿',
    'buttress':             '⣿⠀\n⣿⡀\n⣿⣧\n⣿⣿',
}


def show_shapes():
    """Print all shapes in the vocabulary."""
    print("SHAPE VOCABULARY")
    print("=" * 40)
    for name, art in SHAPE_VOCAB.items():
        print(f"\n  {name}:")
        for line in art.split('\n'):
            print(f"    {line}")
    print()


def show_shape(name):
    """Print a single shape."""
    art = SHAPE_VOCAB.get(name)
    if art:
        print(f"  {name}:")
        for line in art.split('\n'):
            print(f"    {line}")
    else:
        print(f"  Unknown shape: {name}")
        print(f"  Available: {', '.join(SHAPE_VOCAB.keys())}")


# ─── Verification: diff planes + scoring ────────────

def _render_to_grid(layout, view, zoom):
    """Render layout to a 2D boolean grid for comparison."""
    room = layout.get('room', {})
    if view == 'top':
        rw, rh = room.get('width', 20), room.get('depth', 20)
    elif view == 'front':
        rw, rh = room.get('width', 20), room.get('height', 10)
    else:  # side
        rw, rh = room.get('depth', 20), room.get('height', 10)

    scale = 2 / zoom
    pw, ph = int(rw * scale), int(rh * scale)
    grid = [[False] * pw for _ in range(ph)]
    cx = rw / 2
    cz_or_h = rh / 2 if view == 'top' else 0

    for part in layout.get('parts', []):
        if view == 'top':
            px = int((part['x'] + cx - part['w'] / 2) * scale)
            py = int((part['z'] + cz_or_h - part['d'] / 2) * scale)
            pw_p, ph_p = int(part['w'] * scale), int(part['d'] * scale)
        elif view == 'front':
            px = int((part['x'] + cx - part['w'] / 2) * scale)
            py = int((part['y'] - part['h'] / 2) * scale)
            pw_p, ph_p = int(part['w'] * scale), int(part['h'] * scale)
        else:
            px = int((part['z'] + cx - part.get('d', part.get('w', 1)) / 2) * scale)
            py = int((part['y'] - part['h'] / 2) * scale)
            pw_p = int(part.get('d', part.get('w', 1)) * scale)
            ph_p = int(part['h'] * scale)

        for dy in range(max(0, ph_p)):
            for dx in range(max(0, pw_p)):
                gy = ph - 1 - (py + dy)
                gx = px + dx
                if 0 <= gx < pw and 0 <= gy < ph:
                    grid[gy][gx] = True
    return grid, pw, ph


def _grid_to_braille(grid, pw, ph):
    """Convert boolean grid to braille string."""
    canvas = BrailleCanvas(pw, ph)
    for y in range(ph):
        for x in range(pw):
            if y < len(grid) and x < len(grid[y]) and grid[y][x]:
                # grid is top-down, canvas set expects bottom-up
                canvas.pixels[y][x] = True
    return canvas.render()


def _diff_grids(shape_grid, target_grid, pw, ph):
    """Compute diff grids: missing (in target not shape), extra (in shape not target)."""
    missing = [[False] * pw for _ in range(ph)]
    extra = [[False] * pw for _ in range(ph)]
    for y in range(ph):
        for x in range(pw):
            s = shape_grid[y][x] if y < len(shape_grid) and x < len(shape_grid[y]) else False
            t = target_grid[y][x] if y < len(target_grid) and x < len(target_grid[y]) else False
            if t and not s:
                missing[y][x] = True
            if s and not t:
                extra[y][x] = True
    return missing, extra


def _compute_alignment(shape_grid, target_grid, pw, ph):
    """Compute alignment score (IoU) between two grids."""
    intersection = 0
    union = 0
    for y in range(ph):
        for x in range(pw):
            s = shape_grid[y][x] if y < len(shape_grid) and x < len(shape_grid[y]) else False
            t = target_grid[y][x] if y < len(target_grid) and x < len(target_grid[y]) else False
            if s or t:
                union += 1
            if s and t:
                intersection += 1
    return intersection / max(union, 1)


def _count_cells(grid, pw, ph):
    """Count occupied cells."""
    count = 0
    for y in range(ph):
        for x in range(pw):
            if y < len(grid) and x < len(grid[y]) and grid[y][x]:
                count += 1
    return count


def _compute_support(shape_grid, pw, ph):
    """Check how many occupied cells have support (occupied cell below or on bottom row)."""
    occupied = 0
    supported = 0
    for y in range(ph):
        for x in range(pw):
            if y < len(shape_grid) and x < len(shape_grid[y]) and shape_grid[y][x]:
                occupied += 1
                if y == ph - 1:  # bottom row = ground
                    supported += 1
                elif y + 1 < ph and shape_grid[y + 1][x]:
                    supported += 1
    return supported / max(occupied, 1)


def _compute_symmetry(shape_grid, pw, ph):
    """Compute L/R symmetry deviation (0 = perfectly symmetric)."""
    mismatches = 0
    total = 0
    for y in range(ph):
        for x in range(pw // 2):
            mx = pw - 1 - x
            s_left = shape_grid[y][x] if y < len(shape_grid) and x < len(shape_grid[y]) else False
            s_right = shape_grid[y][mx] if y < len(shape_grid) and mx < len(shape_grid[y]) else False
            if s_left or s_right:
                total += 1
            if s_left != s_right:
                mismatches += 1
    return mismatches / max(total, 1)


def verify(shape_layout, target_layout, view='front', zoom=1.0, name='object', template='unknown'):
    """Full verification: render both, compute diff planes, score, recommend patches."""
    shape_grid, pw, ph = _render_to_grid(shape_layout, view, zoom)
    target_grid, tpw, tph = _render_to_grid(target_layout, view, zoom)

    # Ensure same dimensions
    max_w = max(pw, tpw)
    max_h = max(ph, tph)

    missing, extra = _diff_grids(shape_grid, target_grid, max_w, max_h)

    alignment = _compute_alignment(shape_grid, target_grid, max_w, max_h)
    support = _compute_support(shape_grid, max_w, max_h)
    symmetry_dev = _compute_symmetry(shape_grid, max_w, max_h)
    missing_count = _count_cells(missing, max_w, max_h)
    extra_count = _count_cells(extra, max_w, max_h)
    patch_cost = 0
    if missing_count > 0:
        patch_cost += 1
    if extra_count > 0:
        patch_cost += 1
    if symmetry_dev > 0.15:
        patch_cost += 1

    # Determine status
    if alignment >= 0.90 and support >= 0.95 and extra_count == 0 and missing_count == 0:
        status = 'pass'
    elif alignment >= 0.75:
        status = 'needs_patch'
    else:
        status = 'needs_rebuild'

    # Build output
    lines = []
    lines.append(f"inspect: {name}")
    lines.append(f"template: {template}")
    lines.append(f"status: {status}")
    lines.append(f"")
    lines.append(f"view: {view}")
    lines.append(f"bounds: {max_w}×{max_h} cells")
    lines.append(f"zoom: {zoom}x")
    lines.append(f"")
    lines.append(f"scores:")
    lines.append(f"  {view}_profile_alignment: {alignment:.2f}")
    lines.append(f"  support_integrity: {support:.2f}")
    lines.append(f"  symmetry_deviation: {symmetry_dev:.2f}")
    lines.append(f"  missing_cells: {missing_count}")
    lines.append(f"  extra_cells: {extra_count}")
    lines.append(f"  estimated_patch_cost: {patch_cost}")
    lines.append(f"")

    # Dominant failures
    failures = []
    if missing_count > 0:
        failures.append(f"missing {missing_count} cells from target profile")
    if extra_count > 0:
        failures.append(f"extra {extra_count} cells not in target")
    if symmetry_dev > 0.15:
        failures.append(f"symmetry deviation {symmetry_dev:.2f} exceeds threshold")
    if support < 0.95:
        failures.append(f"support integrity {support:.2f} below threshold")

    if failures:
        lines.append("dominant_failures:")
        for i, f in enumerate(failures, 1):
            lines.append(f"  {i}. {f}")
        lines.append("")

    # Planes
    lines.append(f"shape_{view}:")
    lines.append(f"  {_grid_to_braille(shape_grid, max_w, max_h)}")
    lines.append(f"")
    lines.append(f"target_{view}:")
    lines.append(f"  {_grid_to_braille(target_grid, max_w, max_h)}")
    lines.append(f"")

    if missing_count > 0:
        lines.append(f"missing_{view}:")
        lines.append(f"  {_grid_to_braille(missing, max_w, max_h)}")
        lines.append(f"")

    if extra_count > 0:
        lines.append(f"extra_{view}:")
        lines.append(f"  {_grid_to_braille(extra, max_w, max_h)}")
        lines.append(f"")

    # Patches
    patches = []
    if extra_count > 0:
        patches.append("remove excess volume from extra mask region")
    if missing_count > 0:
        patches.append("add volume in missing mask region")
    if symmetry_dev > 0.15:
        patches.append("mirror dominant side to fix asymmetry")
    if support < 0.95:
        patches.append("add support elements below floating mass")

    if patches:
        lines.append("recommended_patches:")
        for i, p in enumerate(patches, 1):
            lines.append(f"  {i}. {p}")

    return '\n'.join(lines)


# ─── CLI ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Braille spatial view generator and verifier')
    parser.add_argument('command', choices=['top', 'front', 'side', 'curve', 'shape', 'shapes', 'verify'])
    parser.add_argument('input', nargs='?', default=None)
    parser.add_argument('--target', type=str, default=None, help='Target layout JSON for verify mode')
    parser.add_argument('--view', type=str, default='front', help='View direction for verify (top/front/side)')
    parser.add_argument('--zoom', type=float, default=1.0)
    parser.add_argument('--name', type=str, default='object')
    parser.add_argument('--template', type=str, default='unknown')
    args = parser.parse_args()

    if args.command in ('top', 'front', 'side'):
        if not args.input:
            print("Error: layout JSON path required")
            sys.exit(1)
        layout = load_layout(args.input)
        if args.command == 'top':
            print(render_top(layout, args.zoom))
        elif args.command == 'front':
            print(render_front(layout, args.zoom))
        elif args.command == 'side':
            print(render_side(layout, args.zoom))

    elif args.command == 'verify':
        if not args.input or not args.target:
            print("Usage: verify shape.json --target target.json [--view front] [--zoom 1]")
            sys.exit(1)
        shape_layout = load_layout(args.input)
        target_layout = load_layout(args.target)
        print(verify(shape_layout, target_layout, args.view, args.zoom, args.name, args.template))

    elif args.command == 'curve':
        if not args.input:
            print("Error: curve description required")
            print('Example: "FLAT(3) GENTLE-ARC(4) POINTED(1) mirror"')
            sys.exit(1)
        pts = parse_curve(args.input)
        print(json.dumps(pts, indent=2))

    elif args.command == 'shapes':
        show_shapes()

    elif args.command == 'shape':
        if not args.input:
            show_shapes()
        else:
            show_shape(args.input)


if __name__ == '__main__':
    main()
