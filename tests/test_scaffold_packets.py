"""
Tests for the packet-based rendering path in scaffold_v4_walkmode.py.

Covers:
  - _hex_to_js_int
  - _geo_js for every supported shape
  - _mat_js with and without emissive
  - build_body_from_packets: piece groups, primitives, placeholder fallback
  - generate_scene_html: full HTML round-trip, camera auto-position
"""

import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "scaffold"))
sys.path.insert(0, str(ROOT / "scripts"))

import scaffold_v4_walkmode as sc
from dropgrid.models import Piece, SceneResult


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _piece(id, type, gx, gz, rot=0):
    return Piece(
        id=id, type=type, label=type,
        gx=gx, gy=0, gz=gz, rot=rot,
        cells=[(0, 0, 0)], group=type, family="", meta={},
    )


def _scene(*pieces):
    return SceneResult(pieces=list(pieces), meta={}, trace=[])


def _prim(shape="box", dims=None, pos=None, rot=None, color="#aabbcc", **mat_extra):
    return {
        "shape": shape,
        "dimensions": dims or {"box": [1, 2, 1], "cylinder": [0.5, 0.5, 2],
                                "cone": [0.5, 1], "sphere": [0.5], "plane": [2, 3]}[shape],
        "position": pos or [0.0, 0.0, 0.0],
        "rotation": rot or [0.0, 0.0, 0.0],
        "material": {"color": color, "roughness": 0.85, "metalness": 0.05, **mat_extra},
    }


def _packet(pid, shapes=("box",)):
    return {
        "piece_id": pid,
        "primitives": [_prim(s) for s in shapes],
    }


# ── _hex_to_js_int ─────────────────────────────────────────────────────────────

def test_hex_to_js_int_lowercase():
    assert sc._hex_to_js_int("#aabbcc") == "0xaabbcc"


def test_hex_to_js_int_uppercase_normalised():
    assert sc._hex_to_js_int("#AABBCC") == "0xaabbcc"


def test_hex_to_js_int_no_hash():
    assert sc._hex_to_js_int("aabbcc") == "0xaabbcc"


# ── _geo_js ────────────────────────────────────────────────────────────────────

def test_geo_js_box():
    assert sc._geo_js("box", [1, 2, 3]) == "new THREE.BoxGeometry(1, 2, 3)"


def test_geo_js_cylinder():
    assert sc._geo_js("cylinder", [0.5, 0.5, 2]) == "new THREE.CylinderGeometry(0.5, 0.5, 2, 16)"


def test_geo_js_cone_top_radius_zero():
    result = sc._geo_js("cone", [0.5, 1.2])
    assert result == "new THREE.CylinderGeometry(0, 0.5, 1.2, 16)"


def test_geo_js_sphere():
    assert sc._geo_js("sphere", [0.5]) == "new THREE.SphereGeometry(0.5, 16, 12)"


def test_geo_js_plane():
    assert sc._geo_js("plane", [2, 3]) == "new THREE.PlaneGeometry(2, 3)"


def test_geo_js_unknown_raises():
    with pytest.raises(ValueError):
        sc._geo_js("torus", [1])


# ── _mat_js ────────────────────────────────────────────────────────────────────

def test_mat_js_contains_color():
    s = sc._mat_js({"color": "#ff0000", "roughness": 0.8, "metalness": 0.1})
    assert "0xff0000" in s


def test_mat_js_contains_roughness_metalness():
    s = sc._mat_js({"color": "#aabbcc", "roughness": 0.7, "metalness": 0.3})
    assert "0.7" in s
    assert "0.3" in s


def test_mat_js_no_emissive_when_absent():
    s = sc._mat_js({"color": "#aabbcc", "roughness": 0.8, "metalness": 0.05})
    assert "emissive" not in s


def test_mat_js_emissive_when_present():
    s = sc._mat_js({
        "color": "#aabbcc", "roughness": 0.3, "metalness": 0.0,
        "emissive": "#ff6600", "emissive_intensity": 0.8,
    })
    assert "0xff6600" in s
    assert "emissiveIntensity" in s
    assert "0.8" in s


# ── build_body_from_packets ────────────────────────────────────────────────────

def test_build_body_contains_function_signature():
    body = sc.build_body_from_packets([], {})
    assert "function buildModel(scene)" in body


def test_build_body_piece_comment():
    pieces = [_piece(7, "tree", 10, 10)]
    body = sc.build_body_from_packets(pieces, {7: _packet(7, ["cone"])})
    assert "piece 7" in body
    assert "tree" in body


def test_build_body_piece_position():
    pieces = [_piece(3, "lantern", 5, 12)]
    body = sc.build_body_from_packets(pieces, {3: _packet(3)})
    assert "pg.position.set(5, 0, 12)" in body


def test_build_body_piece_rotation_zero():
    pieces = [_piece(1, "tree", 0, 0, rot=0)]
    body = sc.build_body_from_packets(pieces, {1: _packet(1)})
    assert "pg.rotation.y = 0.000000" in body


def test_build_body_piece_rotation_90():
    pieces = [_piece(1, "tree", 0, 0, rot=1)]
    body = sc.build_body_from_packets(pieces, {1: _packet(1)})
    assert "1.570796" in body


def test_build_body_box_geometry():
    pieces = [_piece(1, "box", 0, 0)]
    body = sc.build_body_from_packets(pieces, {1: _packet(1, ["box"])})
    assert "BoxGeometry" in body


def test_build_body_cylinder_geometry():
    pieces = [_piece(1, "cyl", 0, 0)]
    body = sc.build_body_from_packets(pieces, {1: _packet(1, ["cylinder"])})
    assert "CylinderGeometry" in body


def test_build_body_cone_geometry():
    pieces = [_piece(1, "cone", 0, 0)]
    body = sc.build_body_from_packets(pieces, {1: _packet(1, ["cone"])})
    assert "CylinderGeometry(0," in body


def test_build_body_sphere_geometry():
    pieces = [_piece(1, "sph", 0, 0)]
    body = sc.build_body_from_packets(pieces, {1: _packet(1, ["sphere"])})
    assert "SphereGeometry" in body


def test_build_body_plane_geometry():
    pieces = [_piece(1, "plane", 0, 0)]
    body = sc.build_body_from_packets(pieces, {1: _packet(1, ["plane"])})
    assert "PlaneGeometry" in body


def test_build_body_multiple_primitives():
    pieces = [_piece(1, "tree", 0, 0)]
    body = sc.build_body_from_packets(pieces, {1: _packet(1, ["cylinder", "cone"])})
    assert "geo0" in body
    assert "geo1" in body
    assert "mat0" in body
    assert "mat1" in body


def test_build_body_placeholder_for_missing_packet():
    pieces = [_piece(5, "unknown", 3, 7)]
    body = sc.build_body_from_packets(pieces, {})
    assert "0x888888" in body  # placeholder grey


def test_build_body_mixed_present_and_missing():
    pieces = [_piece(1, "tree", 0, 0), _piece(2, "rock", 5, 5)]
    body = sc.build_body_from_packets(pieces, {1: _packet(1, ["sphere"])})
    assert "SphereGeometry" in body   # authored
    assert "0x888888" in body         # placeholder for piece 2


def test_build_body_cast_shadow():
    pieces = [_piece(1, "t", 0, 0)]
    body = sc.build_body_from_packets(pieces, {1: _packet(1)})
    assert "castShadow = true" in body
    assert "receiveShadow = true" in body


def test_build_body_emissive_material():
    pieces = [_piece(1, "lantern", 0, 0)]
    prim = _prim("box", emissive="#ff6600", emissive_intensity=0.8)
    pkt = {"piece_id": 1, "primitives": [prim]}
    body = sc.build_body_from_packets(pieces, {1: pkt})
    assert "0xff6600" in body
    assert "emissiveIntensity" in body


def test_build_body_primitive_local_position():
    pieces = [_piece(1, "t", 0, 0)]
    prim = _prim("box", pos=[0.0, 0.5, 0.0])
    pkt = {"piece_id": 1, "primitives": [prim]}
    body = sc.build_body_from_packets(pieces, {1: pkt})
    assert "mesh0.position.set(0.0, 0.5, 0.0)" in body


def test_build_body_primitive_rotation_degrees_to_radians():
    pieces = [_piece(1, "t", 0, 0)]
    prim = _prim("box", rot=[0.0, 90.0, 0.0])
    pkt = {"piece_id": 1, "primitives": [prim]}
    body = sc.build_body_from_packets(pieces, {1: pkt})
    # 90° → ~1.5707... radians
    assert "1.570796" in body


def test_build_body_scene_add_and_return():
    body = sc.build_body_from_packets([], {})
    assert "scene.add(g)" in body
    assert "return g" in body


# ── generate_scene_html ────────────────────────────────────────────────────────

def test_generate_scene_html_is_valid_html():
    scene = _scene(_piece(1, "tree", 5, 5))
    html = sc.generate_scene_html(scene, {1: _packet(1)})
    assert html.startswith("<!DOCTYPE html>")
    assert "</html>" in html


def test_generate_scene_html_custom_title():
    scene = _scene(_piece(1, "tree", 5, 5))
    html = sc.generate_scene_html(scene, {}, title="My Forest")
    assert "My Forest" in html


def test_generate_scene_html_contains_threejs():
    scene = _scene(_piece(1, "tree", 5, 5))
    html = sc.generate_scene_html(scene, {})
    assert "three" in html
    assert "OrbitControls" in html


def test_generate_scene_html_empty_packets_still_renders():
    pieces = [_piece(i, "tree", i * 3, 5) for i in range(5)]
    scene = _scene(*pieces)
    html = sc.generate_scene_html(scene, {})
    assert "0x888888" in html  # all placeholders


def test_generate_scene_html_walk_mode_included():
    scene = _scene(_piece(1, "tree", 5, 5))
    html = sc.generate_scene_html(scene, {})
    assert "walkMode" in html or "_walkMode" in html


def test_generate_scene_html_empty_scene():
    scene = _scene()
    html = sc.generate_scene_html(scene, {})
    assert "<!DOCTYPE html>" in html


def test_generate_scene_html_integration_with_real_solver():
    from dropgrid.api import solve_object_scene
    from authoring.geometry_receiver import receive_all

    DSL = """
anchor campfire altar
ma hard radius 3
object tree label forest count 6 shape circle radius 5 clusters 3 spread 1
"""
    result = solve_object_scene(DSL, seed=42, debug=False)

    raw_packets = []
    for p in result.pieces:
        raw_packets.append({
            "piece_id": p.id,
            "primitives": [
                {
                    "shape": "cylinder" if p.type == "campfire" else "cone",
                    "dimensions": [0.2, 0.2, 0.4] if p.type == "campfire" else [0.4, 1.0],
                    "position": [0.0, 0.2, 0.0],
                    "rotation": [0.0, 0.0, 0.0],
                    "material": {"color": "#ff6600" if p.type == "campfire" else "#2d5a27"},
                }
            ],
        })

    packets = receive_all(raw_packets)
    html = sc.generate_scene_html(result, packets, title="Forest Scene")

    assert len(result.pieces) > 0
    assert "Forest Scene" in html
    # All pieces have authored geometry — no placeholder
    assert "0x888888" not in html
