#!/usr/bin/env python3
"""
test_v4.py — Golden-path tests for v4 additions.

Run: python scripts/test_v4.py
Expected: all tests pass.
"""

import json
import os
import sys
import tempfile

# Add scripts dir to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))


def make_scene(w, d, h, objects=None):
    return {
        "grid": {"width": w, "depth": d, "height": h},
        "templates": {},
        "objects": objects or [],
        "constraints": {
            "require_support": True,
            "no_overlap": True,
            "within_bounds": True
        }
    }


def make_obj(name, x, y, z, w, h, d, char="█"):
    return {"name": name, "x": x, "y": y, "z": z, "w": w, "h": h, "d": d, "char": char}


# ═══════════════════════════════════════════════════════
#  spatial_validate.py tests
# ═══════════════════════════════════════════════════════

print("\n── spatial_validate.py ──")

import spatial_validate as sv

# Test 1: Overlap rejection
scene = make_scene(30, 20, 10, [make_obj("house_01", 8, 0, 3, 3, 4.75, 3)])
new_obj = make_obj("house_02", 9, 0, 4, 3, 4.75, 3)
ok, issues = sv.check_placement(scene, new_obj)
test("Overlap rejection", not ok, f"Expected rejection, got ok={ok}")
test("Overlap issue type", any(i['type'] == 'overlap' for i in issues))

# Test 2: Valid placement accepted
new_obj2 = make_obj("house_02", 15, 0, 3, 3, 4.75, 3)
ok2, issues2 = sv.check_placement(scene, new_obj2)
test("Valid placement accepted", ok2, f"Issues: {[i['message'] for i in issues2]}")

# Test 3: Out of bounds rejection
oob_obj = make_obj("house_oob", 29, 0, 3, 3, 4.75, 3)
ok3, issues3 = sv.check_placement(scene, oob_obj)
test("Out of bounds rejection", any(i['type'] == 'out_of_bounds' for i in issues3))

# Test 4: Floating object warning
floating_obj = make_obj("lamp_01", 5, 3, 5, 0.5, 0.5, 0.5)
ok4, issues4 = sv.check_placement(scene, floating_obj)
test("Floating object warning", any(i['type'] == 'floating' for i in issues4))

# Test 5: Ground-level placement has no floating warning
ground_obj = make_obj("barrel_01", 5, 0, 5, 1, 1, 1)
ok5, issues5 = sv.check_placement(scene, ground_obj)
test("Ground placement no float warning", not any(i['type'] == 'floating' for i in issues5))

# Test 6: Distance query
scene2 = make_scene(30, 20, 10, [
    make_obj("a", 0, 0, 0, 1, 1, 1),
    make_obj("b", 3, 0, 4, 1, 1, 1),
])
result = sv.query_distance(scene2, "a", "b")
test("Distance query", "5.00" in result, f"Expected 5.00 in: {result}")

# Test 7: Overlap query
scene3 = make_scene(30, 20, 10, [
    make_obj("x", 5, 0, 5, 3, 3, 3),
    make_obj("y", 6, 0, 6, 3, 3, 3),
])
result3 = sv.query_overlap(scene3, "x", "y")
test("Overlap query positive", "YES" in result3)

# Test 8: Non-overlap query
scene4 = make_scene(30, 20, 10, [
    make_obj("x", 0, 0, 0, 1, 1, 1),
    make_obj("y", 20, 0, 20, 1, 1, 1),
])
result4 = sv.query_overlap(scene4, "x", "y")
test("Overlap query negative", "NO" in result4)

# Test 9: Fits query
scene5 = make_scene(30, 20, 10, [make_obj("wall", 15, 0, 10, 30, 10, 1)])
result5 = sv.query_fits(scene5, 2, 2, 2, 5, 0, 5)
test("Fits query positive", "YES" in result5)

# Test 10: Full scene validation
scene6 = make_scene(30, 20, 10, [
    make_obj("h1", 5, 0, 5, 3, 4, 3),
    make_obj("h2", 20, 0, 5, 3, 4, 3),
    make_obj("h3", 5, 0, 15, 3, 4, 3),
    make_obj("h4", 20, 0, 15, 3, 4, 3),
])
issues6 = sv.validate_scene(scene6)
test("Clean scene validation", any("passed" in i for i in issues6))

# Test 10b: Keepout zone rejection
scene_z = make_scene(30, 20, 10)
scene_z['zones'] = [{"name": "road", "xmin": 13, "zmin": 0, "xmax": 17, "zmax": 20}]
road_obj = make_obj("person_bad", 15, 0, 5, 1, 1.8, 1)
ok_z, issues_z = sv.check_placement(scene_z, road_obj)
test("Zone rejection (road)", not ok_z, f"Expected rejection, got ok={ok_z}")
test("Zone issue type", any(i['type'] == 'zone_violation' for i in issues_z))

# Test 10c: Outside zone accepted
safe_obj = make_obj("person_safe", 5, 0, 5, 1, 1.8, 1)
ok_safe, issues_safe = sv.check_placement(scene_z, safe_obj)
test("Outside zone accepted", ok_safe)

# Test 10d: Zone in full scene validation
scene_zv = make_scene(30, 20, 10, [make_obj("person_in_road", 15, 0, 10, 1, 1.8, 1)])
scene_zv['zones'] = [{"name": "road", "xmin": 13, "zmin": 0, "xmax": 17, "zmax": 20}]
issues_zv = sv.validate_scene(scene_zv)
test("Zone violation in scene check", any("zone" in i.lower() for i in issues_zv))


# ═══════════════════════════════════════════════════════
#  braille_view.py tests
# ═══════════════════════════════════════════════════════

print("\n── braille_view.py ──")

import braille_view as bv

# Test 11: Braille canvas basic rendering
canvas = bv.BrailleCanvas(4, 4)
canvas.set(0, 0)
canvas.set(1, 1)
canvas.set(2, 2)
canvas.set(3, 3)
result = canvas.render()
test("Braille canvas renders", len(result) > 0 and result != '⠀' * len(result), f"Got: {repr(result)}")

# Test 12: Full block character
canvas2 = bv.BrailleCanvas(2, 4)
for y in range(4):
    for x in range(2):
        canvas2.set(x, y)
result2 = canvas2.render()
test("Full block is ⣿", '⣿' in result2)

# Test 13: Top view renders without error
layout = {
    "room": {"width": 10, "depth": 10, "height": 8},
    "parts": [{"name": "box", "x": 0, "z": 0, "y": 1, "w": 4, "d": 4, "h": 2}]
}
top_result = bv.render_top(layout, zoom=1)
test("Top view renders", "TOP" in top_result and len(top_result) > 20)

# Test 14: Front view renders without error
front_result = bv.render_front(layout, zoom=1)
test("Front view renders", "FRONT" in front_result and len(front_result) > 20)

# Test 15: Side view renders without error
side_result = bv.render_side(layout, zoom=1)
test("Side view renders", "SIDE" in side_result and len(side_result) > 20)

# Test 16: Curve parsing — FLAT is horizontal
pts_flat = bv.parse_curve("FLAT(5)")
test("FLAT is horizontal", abs(pts_flat[-1][1]) < 0.001, f"Y={pts_flat[-1][1]}")
test("FLAT covers length", abs(pts_flat[-1][0] - 5.0) < 0.1, f"X={pts_flat[-1][0]}")

# Test 16b: POINTED is vertical
pts_pointed = bv.parse_curve("POINTED(3)")
test("POINTED is vertical", abs(pts_pointed[-1][0]) < 0.001, f"X={pts_pointed[-1][0]}")
test("POINTED covers length", abs(pts_pointed[-1][1] - 3.0) < 0.1, f"Y={pts_pointed[-1][1]}")

# Test 16c: GENTLE-ARC curves upward
pts_gentle = bv.parse_curve("GENTLE-ARC(5)")
test("GENTLE-ARC rises", pts_gentle[-1][1] > 0.3, f"Y={pts_gentle[-1][1]}")
test("GENTLE-ARC mostly horizontal", pts_gentle[-1][0] > pts_gentle[-1][1], 
     f"X={pts_gentle[-1][0]}, Y={pts_gentle[-1][1]}")

# Test 16d: STEEP-ARC curves more than GENTLE
pts_steep = bv.parse_curve("STEEP-ARC(5)")
test("STEEP rises more than GENTLE", pts_steep[-1][1] > pts_gentle[-1][1])

# Test 16e: Mirror produces symmetric output
pts_mirror = bv.parse_curve("FLAT(3) POINTED(2) mirror")
test("Mirror starts at origin", abs(pts_mirror[0][0]) < 0.001 and abs(pts_mirror[0][1]) < 0.001)
test("Mirror ends at origin Y", abs(pts_mirror[-1][1]) < 0.001, f"Y={pts_mirror[-1][1]}")

# Test 16f: Roof profile is monotonic to peak
pts_roof = bv.parse_curve("FLAT(3) GENTLE-ARC(4) STEEP-ARC(3) POINTED(1) mirror")
peak_idx = max(range(len(pts_roof)), key=lambda i: pts_roof[i][1])
left_half = pts_roof[:peak_idx+1]
monotonic = all(left_half[i][1] <= left_half[i+1][1] + 0.001 for i in range(len(left_half)-1))
test("Roof profile monotonic to peak", monotonic)

# Test 17: Shape vocabulary exists
test("Shape vocab has entries", len(bv.SHAPE_VOCAB) >= 10)
test("Shape vocab has triangle", 'triangle-equilateral' in bv.SHAPE_VOCAB)
test("Shape vocab has arch", 'arch-pointed' in bv.SHAPE_VOCAB)
test("Shape vocab has dome", 'dome-round' in bv.SHAPE_VOCAB)

# Test 18: Verify produces scored output
shape_layout = {
    "room": {"width": 10, "depth": 10, "height": 8},
    "parts": [{"name": "box", "x": 0, "z": 0, "y": 2, "w": 6, "d": 6, "h": 4}]
}
target_layout = {
    "room": {"width": 10, "depth": 10, "height": 8},
    "parts": [{"name": "box", "x": 0, "z": 0, "y": 2, "w": 6, "d": 6, "h": 4}]
}
verify_result = bv.verify(shape_layout, target_layout, 'front', 1.0, 'test_box', 'box_template')
test("Verify produces output", "inspect: test_box" in verify_result)
test("Verify has scores", "profile_alignment" in verify_result)
test("Verify has status", "status:" in verify_result)

# Test 19: Verify detects mismatch
mismatched_target = {
    "room": {"width": 10, "depth": 10, "height": 8},
    "parts": [{"name": "box", "x": 0, "z": 0, "y": 2, "w": 8, "d": 8, "h": 6}]
}
mismatch_result = bv.verify(shape_layout, mismatched_target, 'front', 1.0, 'test_mismatch', 'big_box')
test("Verify detects mismatch", "missing" in mismatch_result.lower() or "extra" in mismatch_result.lower() or "needs_patch" in mismatch_result)


# ═══════════════════════════════════════════════════════
#  template_library.py tests
# ═══════════════════════════════════════════════════════

print("\n── template_library.py ──")

import template_library as tl

# Test 20: Init library
lib = tl.init_library()
test("Init library", 'templates' in lib and len(lib['templates']) == 0)

# Test 21: Add template
lib = tl.add_template(lib, 'test_box', {
    'name': 'Test Box',
    'parts': [{'shape': 'box', 'w': 2, 'h': 2, 'd': 2, 'material': 'stone'}],
    'footprint': [2, 2],
    'bounding_box': [2, 2, 2],
})
test("Add template", 'test_box' in lib['templates'])

# Test 22: List templates
items = tl.list_templates(lib)
test("List templates", len(items) == 1 and 'test_box' in items[0])

# Test 23: Show template
info = tl.show_template(lib, 'test_box')
test("Show template", 'Test Box' in info and 'box' in info)

# Test 24: Show missing template
info_missing = tl.show_template(lib, 'nonexistent')
test("Show missing template", 'not found' in info_missing)

# Test 25: Instantiate template
scene_t = make_scene(20, 20, 10)
scene_t, msg = tl.instantiate_template(lib, scene_t, 'test_box', 5, 0, 5)
test("Instantiate template", len(scene_t['objects']) == 1)
test("Instance has template ref", scene_t['objects'][0].get('template') == 'test_box')
test("Instance has bbox from template", scene_t['objects'][0]['w'] == 2)

# Test 26: Default templates
lib2 = tl.init_library()
for tid, tdata in tl.DEFAULT_TEMPLATES.items():
    lib2 = tl.add_template(lib2, tid, tdata)
test("Default templates loaded", len(lib2['templates']) == 6)
test("Has house_simple", 'house_simple' in lib2['templates'])
test("Has person_simple", 'person_simple' in lib2['templates'])
test("Has cart_simple", 'cart_simple' in lib2['templates'])
test("Has stall_simple", 'stall_simple' in lib2['templates'])

# Test 27: Generate code — buildModel, not buildScene
scene_g = make_scene(20, 20, 10)
scene_g, _ = tl.instantiate_template(lib2, scene_g, 'house_simple', 5, 0, 5, {'name': 'h1'})
scene_g, _ = tl.instantiate_template(lib2, scene_g, 'person_simple', 10, 0, 10, {'name': 'p1'})
code = tl.generate_threejs_objects(lib2, scene_g)
test("Generate code has house builder", 'build_house_simple' in code)
test("Generate code has person builder", 'build_person_simple' in code)
test("Generate code has placement", 'h1' in code and 'p1' in code)
test("Generate uses buildModel not buildScene", 'buildModel' in code and 'buildScene' not in code)
test("Generate notes matByName dependency", 'matByName' in code)

# Test 28: Part rotation in generated code
scene_cart = make_scene(20, 20, 10)
scene_cart, _ = tl.instantiate_template(lib2, scene_cart, 'cart_simple', 10, 0, 10, {'name': 'cart1'})
code_cart = tl.generate_threejs_objects(lib2, scene_cart)
test("Cart wheels have rotation", 'rotation.set' in code_cart, "Expected rotation.set for wheel parts")

# Test 29: >8 instances triggers batch placement pattern
scene_many = make_scene(100, 20, 10)
for i in range(10):
    scene_many, _ = tl.instantiate_template(lib2, scene_many, 'house_simple', i * 8, 0, 5, {'name': f'house_{i}'})
code_many = tl.generate_threejs_objects(lib2, scene_many)
test(">8 instances mentions batch", 'instances' in code_many.lower() or 'positions' in code_many.lower(),
     "Expected batch/positions pattern for 10 houses")


# ═══════════════════════════════════════════════════════
#  v4.0.6 tests — instance rotation + centering
# ═══════════════════════════════════════════════════════

print("\n── v4.0.6: instance rotation + centering ──")

# Test: Instance rotation_y stored in scene
scene_rot = make_scene(30, 30, 10)
scene_rot, msg = tl.instantiate_template(lib2, scene_rot, 'cart_simple', 10, 0, 10,
    {'name': 'cart_rot', 'rotation_y': 90})
rotated_obj = [o for o in scene_rot['objects'] if o['name'] == 'cart_rot'][0]
test("Instance rotation stored", rotated_obj.get('rotation_y') == 90)
test("Instance rotation swaps w/d", rotated_obj['w'] == 2 and rotated_obj['d'] == 4,
     f"Expected w=2 d=4, got w={rotated_obj['w']} d={rotated_obj['d']}")
test("Instance rotation in message", "rot_y=90" in msg)

# Test: No rotation → no rotation_y key
scene_norot = make_scene(20, 20, 10)
scene_norot, _ = tl.instantiate_template(lib2, scene_norot, 'cart_simple', 5, 0, 5, {'name': 'cart_nr'})
nr_obj = [o for o in scene_norot['objects'] if o['name'] == 'cart_nr'][0]
test("No rotation → no key", 'rotation_y' not in nr_obj)

# Test: Code generation with rotation_y
scene_rotcode = make_scene(30, 30, 10)
scene_rotcode, _ = tl.instantiate_template(lib2, scene_rotcode, 'house_simple', 5, 0, 5, {'name': 'h_straight'})
scene_rotcode, _ = tl.instantiate_template(lib2, scene_rotcode, 'house_simple', 15, 0, 5, {'name': 'h_rotated', 'rotation_y': 90})
code_rot = tl.generate_threejs_objects(lib2, scene_rotcode)
test("Rotated instance has rotation.y in code", 'rotation.y' in code_rot)

# Test: Centering
scene_ctr = make_scene(30, 30, 10)
scene_ctr, _ = tl.instantiate_template(lib2, scene_ctr, 'house_simple', 15, 0, 15, {'name': 'ctr_house'})
code_ctr = tl.generate_threejs_objects(lib2, scene_ctr, center=(15, 15))
test("Centered code has offset comment", "Centered" in code_ctr)
test("Centered position is 0,0", "position.set(0.0, 0" in code_ctr or "position.set(0, 0" in code_ctr,
     "Expected centered house at x=0, z=0")

# Test: Centering doesn't affect non-centered
code_noctr = tl.generate_threejs_objects(lib2, scene_ctr)
test("Non-centered keeps original pos", "position.set(15" in code_noctr)




# ═══════════════════════════════════════════════════════
#  v4.0.7 tests — path_walk.py
# ═══════════════════════════════════════════════════════

print("\n── v4.0.7: path_walk.py ──")

import path_walk as pw

# Build a simple test scene
walk_scene = {
    "grid": {"width": 20, "depth": 20, "height": 10},
    "objects": [
        {"name": "gate", "template": "gate", "x": 10, "y": 0, "z": 5, "w": 4, "h": 3, "d": 1},
        {"name": "hall", "template": "hall", "x": 10, "y": 0, "z": 15, "w": 6, "h": 5, "d": 4},
    ],
    "zones": []
}

# Test: scan_nearby finds objects
nearby = pw.scan_nearby(walk_scene["objects"], 10, 4, radius=5)
test("scan_nearby finds gate", any(h["name"] == "gate" for h in nearby))

# Test: direction labels
test("direction ahead", pw.direction_label(0, 5) == "ahead")
test("direction left", pw.direction_label(-5, 0) == "left")
test("direction right", pw.direction_label(5, 0) == "right")
test("direction behind", pw.direction_label(0, -5) == "behind")

# Test: walk_axis produces steps
steps = pw.walk_axis(walk_scene, 10, 0, 20, step=2, radius=5)
test("walk_axis produces steps", len(steps) > 5)
test("steps have nearby", all("nearby" in s for s in steps))

# Test: detect_gaps finds gap between gate and hall
gaps = pw.detect_gaps(steps)
test("detect_gaps finds gap", len(gaps) >= 1, f"Expected gaps between gate(z=5) and hall(z=15)")

# Test: detect_facade_transitions
transitions = pw.detect_facade_transitions(steps)
test("detect_transitions finds some", len(transitions) >= 1)

# Test: waypoint walk
wp_steps = pw.walk_waypoints(walk_scene, [(10,0), (10,10), (15,15)], step=2, radius=5)
test("waypoint walk produces steps", len(wp_steps) > 3)

# ═══════════════════════════════════════════════════════
#  Summary
# ═══════════════════════════════════════════════════════

print(f"\n{'='*40}")
print(f"  {PASS} passed, {FAIL} failed, {PASS+FAIL} total")
if FAIL == 0:
    print("  All tests passed ✓")
else:
    print(f"  {FAIL} FAILURES — fix before shipping")
print(f"{'='*40}")
sys.exit(1 if FAIL > 0 else 0)
