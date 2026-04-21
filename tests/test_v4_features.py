"""
Tests for v4 verification modules: spatial_validate, braille_view, path_walk.

template_library tests from the original v4 suite are intentionally omitted —
that module was excluded from this skill by design (see CHECKLIST.md).
"""

import sys
from pathlib import Path

# Add verification modules to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "verification"))

import spatial_validate as sv
import braille_view as bv
import path_walk as pw


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_scene(w, d, h, objects=None):
    return {
        "grid": {"width": w, "depth": d, "height": h},
        "templates": {},
        "objects": objects or [],
        "constraints": {"require_support": True, "no_overlap": True, "within_bounds": True},
    }


def make_obj(name, x, y, z, w, h, d, char="█"):
    return {"name": name, "x": x, "y": y, "z": z, "w": w, "h": h, "d": d, "char": char}


# ── spatial_validate ──────────────────────────────────────────────────────────

def test_overlap_rejection():
    scene = make_scene(30, 20, 10, [make_obj("house_01", 8, 0, 3, 3, 4.75, 3)])
    ok, issues = sv.check_placement(scene, make_obj("house_02", 9, 0, 4, 3, 4.75, 3))
    assert not ok
    assert any(i["type"] == "overlap" for i in issues)


def test_valid_placement_accepted():
    scene = make_scene(30, 20, 10, [make_obj("house_01", 8, 0, 3, 3, 4.75, 3)])
    ok, issues = sv.check_placement(scene, make_obj("house_02", 15, 0, 3, 3, 4.75, 3))
    assert ok, f"Issues: {[i['message'] for i in issues]}"


def test_out_of_bounds_rejection():
    scene = make_scene(30, 20, 10, [make_obj("house_01", 8, 0, 3, 3, 4.75, 3)])
    _, issues = sv.check_placement(scene, make_obj("house_oob", 29, 0, 3, 3, 4.75, 3))
    assert any(i["type"] == "out_of_bounds" for i in issues)


def test_floating_object_warning():
    scene = make_scene(30, 20, 10, [make_obj("house_01", 8, 0, 3, 3, 4.75, 3)])
    _, issues = sv.check_placement(scene, make_obj("lamp_01", 5, 3, 5, 0.5, 0.5, 0.5))
    assert any(i["type"] == "floating" for i in issues)


def test_ground_placement_no_float_warning():
    scene = make_scene(30, 20, 10, [make_obj("house_01", 8, 0, 3, 3, 4.75, 3)])
    _, issues = sv.check_placement(scene, make_obj("barrel_01", 5, 0, 5, 1, 1, 1))
    assert not any(i["type"] == "floating" for i in issues)


def test_distance_query():
    scene = make_scene(30, 20, 10, [make_obj("a", 0, 0, 0, 1, 1, 1), make_obj("b", 3, 0, 4, 1, 1, 1)])
    result = sv.query_distance(scene, "a", "b")
    assert "5.00" in result


def test_overlap_query_positive():
    scene = make_scene(30, 20, 10, [make_obj("x", 5, 0, 5, 3, 3, 3), make_obj("y", 6, 0, 6, 3, 3, 3)])
    assert "YES" in sv.query_overlap(scene, "x", "y")


def test_overlap_query_negative():
    scene = make_scene(30, 20, 10, [make_obj("x", 0, 0, 0, 1, 1, 1), make_obj("y", 20, 0, 20, 1, 1, 1)])
    assert "NO" in sv.query_overlap(scene, "x", "y")


def test_fits_query_positive():
    scene = make_scene(30, 20, 10, [make_obj("wall", 15, 0, 10, 30, 10, 1)])
    assert "YES" in sv.query_fits(scene, 2, 2, 2, 5, 0, 5)


def test_clean_scene_validation():
    scene = make_scene(30, 20, 10, [
        make_obj("h1", 5, 0, 5, 3, 4, 3), make_obj("h2", 20, 0, 5, 3, 4, 3),
        make_obj("h3", 5, 0, 15, 3, 4, 3), make_obj("h4", 20, 0, 15, 3, 4, 3),
    ])
    issues = sv.validate_scene(scene)
    assert any("passed" in i for i in issues)


def test_zone_rejection():
    scene = make_scene(30, 20, 10)
    scene["zones"] = [{"name": "road", "xmin": 13, "zmin": 0, "xmax": 17, "zmax": 20}]
    ok, issues = sv.check_placement(scene, make_obj("person_bad", 15, 0, 5, 1, 1.8, 1))
    assert not ok
    assert any(i["type"] == "zone_violation" for i in issues)


def test_zone_outside_accepted():
    scene = make_scene(30, 20, 10)
    scene["zones"] = [{"name": "road", "xmin": 13, "zmin": 0, "xmax": 17, "zmax": 20}]
    ok, _ = sv.check_placement(scene, make_obj("person_safe", 5, 0, 5, 1, 1.8, 1))
    assert ok


def test_zone_in_full_validation():
    scene = make_scene(30, 20, 10, [make_obj("person_in_road", 15, 0, 10, 1, 1.8, 1)])
    scene["zones"] = [{"name": "road", "xmin": 13, "zmin": 0, "xmax": 17, "zmax": 20}]
    issues = sv.validate_scene(scene)
    assert any("zone" in i.lower() for i in issues)


# ── braille_view ──────────────────────────────────────────────────────────────

def test_braille_canvas_renders():
    canvas = bv.BrailleCanvas(4, 4)
    for i in range(4):
        canvas.set(i, i)
    result = canvas.render()
    assert len(result) > 0 and result != "⠀" * len(result)


def test_braille_full_block():
    canvas = bv.BrailleCanvas(2, 4)
    for y in range(4):
        for x in range(2):
            canvas.set(x, y)
    assert "⣿" in canvas.render()


def test_braille_top_view():
    layout = {"room": {"width": 10, "depth": 10, "height": 8},
               "parts": [{"name": "box", "x": 0, "z": 0, "y": 1, "w": 4, "d": 4, "h": 2}]}
    result = bv.render_top(layout, zoom=1)
    assert "TOP" in result and len(result) > 20


def test_braille_front_view():
    layout = {"room": {"width": 10, "depth": 10, "height": 8},
               "parts": [{"name": "box", "x": 0, "z": 0, "y": 1, "w": 4, "d": 4, "h": 2}]}
    assert "FRONT" in bv.render_front(layout, zoom=1)


def test_braille_side_view():
    layout = {"room": {"width": 10, "depth": 10, "height": 8},
               "parts": [{"name": "box", "x": 0, "z": 0, "y": 1, "w": 4, "d": 4, "h": 2}]}
    assert "SIDE" in bv.render_side(layout, zoom=1)


def test_curve_flat_is_horizontal():
    pts = bv.parse_curve("FLAT(5)")
    assert abs(pts[-1][1]) < 0.001
    assert abs(pts[-1][0] - 5.0) < 0.1


def test_curve_pointed_is_vertical():
    pts = bv.parse_curve("POINTED(3)")
    assert abs(pts[-1][0]) < 0.001
    assert abs(pts[-1][1] - 3.0) < 0.1


def test_curve_gentle_arc():
    pts = bv.parse_curve("GENTLE-ARC(5)")
    assert pts[-1][1] > 0.3
    assert pts[-1][0] > pts[-1][1]


def test_curve_steep_arc_rises_more():
    pts_gentle = bv.parse_curve("GENTLE-ARC(5)")
    pts_steep = bv.parse_curve("STEEP-ARC(5)")
    assert pts_steep[-1][1] > pts_gentle[-1][1]


def test_curve_mirror_symmetric():
    pts = bv.parse_curve("FLAT(3) POINTED(2) mirror")
    assert abs(pts[0][0]) < 0.001 and abs(pts[0][1]) < 0.001
    assert abs(pts[-1][1]) < 0.001


def test_roof_profile_monotonic():
    pts = bv.parse_curve("FLAT(3) GENTLE-ARC(4) STEEP-ARC(3) POINTED(1) mirror")
    peak = max(range(len(pts)), key=lambda i: pts[i][1])
    left = pts[:peak + 1]
    assert all(left[i][1] <= left[i + 1][1] + 0.001 for i in range(len(left) - 1))


def test_shape_vocab_exists():
    assert len(bv.SHAPE_VOCAB) >= 10
    assert "triangle-equilateral" in bv.SHAPE_VOCAB
    assert "arch-pointed" in bv.SHAPE_VOCAB
    assert "dome-round" in bv.SHAPE_VOCAB


def test_verify_produces_scored_output():
    layout = {"room": {"width": 10, "depth": 10, "height": 8},
               "parts": [{"name": "box", "x": 0, "z": 0, "y": 2, "w": 6, "d": 6, "h": 4}]}
    result = bv.verify(layout, layout, "front", 1.0, "test_box", "box_template")
    assert "inspect: test_box" in result
    assert "profile_alignment" in result
    assert "status:" in result


def test_verify_detects_mismatch():
    layout = {"room": {"width": 10, "depth": 10, "height": 8},
               "parts": [{"name": "box", "x": 0, "z": 0, "y": 2, "w": 6, "d": 6, "h": 4}]}
    big = {"room": {"width": 10, "depth": 10, "height": 8},
           "parts": [{"name": "box", "x": 0, "z": 0, "y": 2, "w": 8, "d": 8, "h": 6}]}
    result = bv.verify(layout, big, "front", 1.0, "test_mismatch", "big_box")
    assert ("missing" in result.lower() or "extra" in result.lower() or "needs_patch" in result)


# ── path_walk ─────────────────────────────────────────────────────────────────

WALK_SCENE = {
    "grid": {"width": 20, "depth": 20, "height": 10},
    "objects": [
        {"name": "gate", "template": "gate", "x": 10, "y": 0, "z": 5, "w": 4, "h": 3, "d": 1},
        {"name": "hall", "template": "hall", "x": 10, "y": 0, "z": 15, "w": 6, "h": 5, "d": 4},
    ],
    "zones": [],
}


def test_scan_nearby_finds_objects():
    nearby = pw.scan_nearby(WALK_SCENE["objects"], 10, 4, radius=5)
    assert any(h["name"] == "gate" for h in nearby)


def test_direction_labels():
    assert pw.direction_label(0, 5) == "ahead"
    assert pw.direction_label(-5, 0) == "left"
    assert pw.direction_label(5, 0) == "right"
    assert pw.direction_label(0, -5) == "behind"


def test_walk_axis_produces_steps():
    steps = pw.walk_axis(WALK_SCENE, 10, 0, 20, step=2, radius=5)
    assert len(steps) > 5
    assert all("nearby" in s for s in steps)


def test_detect_gaps():
    steps = pw.walk_axis(WALK_SCENE, 10, 0, 20, step=2, radius=5)
    gaps = pw.detect_gaps(steps)
    assert len(gaps) >= 1


def test_detect_facade_transitions():
    steps = pw.walk_axis(WALK_SCENE, 10, 0, 20, step=2, radius=5)
    transitions = pw.detect_facade_transitions(steps)
    assert len(transitions) >= 1


def test_waypoint_walk():
    steps = pw.walk_waypoints(WALK_SCENE, [(10, 0), (10, 10), (15, 15)], step=2, radius=5)
    assert len(steps) > 3
