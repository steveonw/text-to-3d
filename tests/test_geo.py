#!/usr/bin/env python3
"""Tests for geo.py — run with: python scripts/test_geo.py"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts', 'helpers'))
from geo import *


def test_grid_count():
    pts = grid_placements(3, 3, 2.0, 2.0)
    assert len(pts) == 9, f"Expected 9, got {len(pts)}"

def test_grid_centered():
    pts = grid_placements(3, 3, 2.0, 2.0)
    xs = sorted(set(p["x"] for p in pts))
    assert xs == [-2.0, 0.0, 2.0], f"Expected [-2, 0, 2], got {xs}"

def test_ring_count():
    pts = ring_placements(8, 5.0)
    assert len(pts) == 8, f"Expected 8, got {len(pts)}"

def test_ring_include_end():
    pts = ring_placements(8, 5.0, include_end=True)
    assert len(pts) == 9, f"Expected 9 with include_end, got {len(pts)}"

def test_ring_half_arc():
    pts = ring_placements(4, 5.0, start_angle_deg=0, end_angle_deg=180)
    angles = [p["angle_deg"] for p in pts]
    assert angles[0] == 0.0, f"First angle should be 0, got {angles[0]}"
    assert angles[-1] < 180.0, f"Last angle should be < 180 without include_end, got {angles[-1]}"

def test_ring_half_arc_include_end():
    pts = ring_placements(4, 5.0, start_angle_deg=0, end_angle_deg=180, include_end=True)
    angles = [p["angle_deg"] for p in pts]
    assert abs(angles[-1] - 180.0) < 0.01, f"Last angle should be 180 with include_end, got {angles[-1]}"

def test_linear_endpoints():
    pts = linear_placements(3, (0, 0, 0), (10, 0, 0))
    assert pts[0]["x"] == 0.0
    assert pts[-1]["x"] == 10.0

def test_stacked_count():
    pts = stacked_placements(5, 2.0)
    assert len(pts) == 5
    assert pts[0]["y"] == 0.0
    assert pts[-1]["y"] == 8.0

def test_dome_endpoints():
    pts = dome_profile(5.0, n=16)
    assert abs(pts[0]["r"] - 5.0) < 0.01, "Base should be full radius"
    assert abs(pts[-1]["r"]) < 0.01, "Apex should be ~0 radius"

def test_taper_endpoints():
    pts = taper_profile(2.0, 0.5, 6.0)
    assert abs(pts[0]["r"] - 2.0) < 0.01
    assert abs(pts[-1]["r"] - 0.5) < 0.01
    assert abs(pts[-1]["y"] - 6.0) < 0.01

def test_arc_point_count():
    pts = arc_points(3.0, 180, n=24)
    assert len(pts) == 25, f"Expected 25 (n+1), got {len(pts)}"

def test_ogee_endpoints():
    pts = ogee_profile(1.0, 0.3, n=16)
    assert abs(pts[0]["x"]) < 0.01 and abs(pts[0]["y"]) < 0.01
    assert abs(pts[-1]["x"] - 1.0) < 0.01 and abs(pts[-1]["y"] - 0.3) < 0.01

def test_mirror_doubles():
    pts = [{"x": 2.0, "y": 0.0, "z": 0.0}]
    mirrored = mirror_points(pts, axis="x")
    assert len(mirrored) == 2

def test_validate_catches_negative():
    warns = validate_params({"height": -3.0})
    assert any("negative" in w for w in warns), "Should warn about negative height"

def test_validate_catches_zero():
    warns = validate_params({"radius": 0})
    assert any("zero" in w for w in warns), "Should warn about zero radius"

def test_validate_catches_unit_mixing():
    warns = validate_params({"bigThing": 10000.0, "smallThing": 0.5})
    assert any("ratio" in w.lower() or "mixing" in w.lower() for w in warns)

def test_validate_clean():
    warns = validate_params({"width": 10.0, "height": 5.0, "depth": 8.0})
    assert len(warns) == 0, f"Expected no warnings, got {warns}"

def test_flatten_profile():
    pts = [{"r": 5.0, "y": 0.0}, {"r": 0.0, "y": 5.0}]
    flat = flatten_profile(pts)
    assert flat == [[5.0, 0.0], [0.0, 5.0]]


if __name__ == "__main__":
    passed = 0
    failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
                passed += 1
            except Exception as e:
                print(f"  FAIL  {name}: {e}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
