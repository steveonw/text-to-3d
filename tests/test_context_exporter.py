"""
Tests for scripts/authoring/context_exporter.py

Coverage:
  - packet structure and self fields
  - neighbor sorting and direction labels
  - interior piece (surrounded on all sides)
  - edge piece (open half-space on one side)
  - piece near a path
  - piece not near a path
  - outward direction
  - integration: real solver output (shrine scene)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dropgrid.models import Piece, SceneResult
from authoring.context_exporter import export_piece_context, export_all_contexts


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _piece(id, type, gx, gz, *, label=None, family="", rot=0):
    return Piece(
        id=id, type=type, label=label or type,
        gx=gx, gy=0, gz=gz,
        rot=rot, cells=[(0, 0, 0)],
        group=label or type, family=family, meta={},
    )


def _scene(*pieces):
    return SceneResult(pieces=list(pieces), meta={}, trace=[])


# ── Structure ──────────────────────────────────────────────────────────────────

def test_packet_has_all_required_keys():
    p = _piece(1, "tree", 5, 5)
    ctx = export_piece_context(p, _scene(p, _piece(2, "tree", 8, 8)))
    for key in ("self", "neighbors", "near_path", "path_direction",
                "on_cluster_edge", "interior", "in_corner",
                "outward_direction", "scene_center"):
        assert key in ctx, f"Missing key: {key}"


def test_self_fields_correct():
    p = _piece(7, "tree", 5, 5, label="forest", family="flora", rot=2)
    ctx = export_piece_context(p, _scene(p, _piece(2, "tree", 8, 8)))
    s = ctx["self"]
    assert s["id"] == 7
    assert s["type"] == "tree"
    assert s["label"] == "forest"
    assert s["family"] == "flora"
    assert s["position"] == {"x": 5, "z": 5}
    assert s["rot"] == 2
    assert s["facing"] == "S"          # rot=2 → south


def test_scene_center_is_mean_position():
    pieces = [_piece(i, "tree", i * 4, 0) for i in range(3)]   # x = 0, 4, 8 → center 4
    ctx = export_piece_context(pieces[1], _scene(*pieces))
    assert ctx["scene_center"]["x"] == 4.0


# ── Neighbors ─────────────────────────────────────────────────────────────────

def test_neighbors_sorted_by_distance():
    center = _piece(0, "altar", 14, 14)
    near   = _piece(1, "tree",  15, 14)   # dist 1
    far    = _piece(2, "tree",  20, 14)   # dist 6
    ctx = export_piece_context(center, _scene(center, near, far))
    dists = [n["distance"] for n in ctx["neighbors"]]
    assert dists == sorted(dists)


def test_neighbor_count_capped_by_n():
    pieces = [_piece(i, "tree", i * 2, 0) for i in range(10)]
    ctx = export_piece_context(pieces[5], _scene(*pieces), neighbors=3)
    assert len(ctx["neighbors"]) == 3


def test_neighbor_direction_east():
    p = _piece(1, "tree", 5, 5)
    q = _piece(2, "tree", 10, 5)   # directly east (x+)
    ctx = export_piece_context(p, _scene(p, q))
    assert ctx["neighbors"][0]["direction"] == "E"


def test_neighbor_direction_south():
    p = _piece(1, "tree", 5, 5)
    q = _piece(2, "tree", 5, 10)   # directly south (z+)
    ctx = export_piece_context(p, _scene(p, q))
    assert ctx["neighbors"][0]["direction"] == "S"


def test_neighbor_direction_northwest():
    p = _piece(1, "tree", 10, 10)
    q = _piece(2, "tree", 7, 7)    # dx=-3, dz=-3 → NW
    ctx = export_piece_context(p, _scene(p, q))
    assert ctx["neighbors"][0]["direction"] == "NW"


# ── Interior vs edge ──────────────────────────────────────────────────────────

def test_interior_piece_surrounded_on_all_sides():
    altar = _piece(0, "campfire", 14, 14, family="anchor")
    ring = [
        _piece(i + 1, "tree", 14 + dx, 14 + dz, family="flora")
        for i, (dx, dz) in enumerate([
            (3, 0), (-3, 0), (0, 3), (0, -3),
            (2, 2), (-2, 2), (2, -2), (-2, -2),
        ])
    ]
    ctx = export_piece_context(altar, _scene(altar, *ring))
    assert ctx["interior"] is True
    assert ctx["on_cluster_edge"] is False


def test_edge_piece_open_half_space():
    # Dense cluster at z ≥ 12; lone tree at z=5 has nothing to its north
    cluster = [_piece(i, "tree", 12 + (i % 4), 12 + (i // 4)) for i in range(12)]
    lone = _piece(99, "tree", 14, 5)
    ctx = export_piece_context(lone, _scene(*cluster, lone))
    assert ctx["on_cluster_edge"] is True
    assert ctx["interior"] is False


def test_tiny_scene_is_all_edge():
    # 3-piece scene — every piece should be considered edge
    pieces = [_piece(i, "tree", i * 5, 0) for i in range(3)]
    for p in pieces:
        ctx = export_piece_context(p, _scene(*pieces))
        assert ctx["on_cluster_edge"] is True


# ── Path proximity ─────────────────────────────────────────────────────────────

def test_near_path_detects_road_family():
    road    = _piece(1, "road", 14, 10, family="path")
    lantern = _piece(2, "lantern", 15, 10, family="prop")
    ctx = export_piece_context(lantern, _scene(road, lantern))
    assert ctx["near_path"] is True
    assert ctx["path_direction"] is not None


def test_near_path_direction_points_toward_road():
    road    = _piece(1, "road", 14, 10, family="path")
    lantern = _piece(2, "lantern", 12, 10, family="prop")  # road is to the east
    ctx = export_piece_context(lantern, _scene(road, lantern))
    assert ctx["path_direction"] == "E"


def test_not_near_path_when_far():
    road     = _piece(1, "road", 14, 10, family="path")
    far_tree = _piece(2, "tree",  5,  5, family="flora")
    ctx = export_piece_context(far_tree, _scene(road, far_tree))
    assert ctx["near_path"] is False
    assert ctx["path_direction"] is None


def test_path_piece_itself_not_near_path():
    road1 = _piece(1, "road", 14, 10, family="path")
    tree  = _piece(2, "tree",  5,  5, family="flora")
    # road itself — its own type shouldn't self-match
    ctx = export_piece_context(road1, _scene(road1, tree))
    assert ctx["near_path"] is False


# ── Outward direction ──────────────────────────────────────────────────────────

def test_outward_direction_north():
    # Cluster sits south of the lone piece
    south = [_piece(i, "tree", 14, 18 + i) for i in range(4)]
    north_tree = _piece(10, "tree", 14, 5)
    ctx = export_piece_context(north_tree, _scene(*south, north_tree))
    assert ctx["outward_direction"] in ("N", "NE", "NW")


def test_outward_direction_center_when_at_mean():
    # Single piece at the mean position → "center"
    p = _piece(0, "altar", 10, 10)
    ctx = export_piece_context(p, _scene(p))
    assert ctx["outward_direction"] == "center"


# ── Integration: real solver output ───────────────────────────────────────────

def test_export_all_contexts_returns_one_entry_per_piece():
    from dropgrid.api import solve_object_scene

    DSL = """
anchor campfire altar
ma hard radius 4

object road label path count 10 from altar heading south steps 10 wobble 0.1
object lantern label lanterns count 4 target road side any distance 1 spacing 2
object tree label forest count 10 shape circle radius 7 clusters 5 spread 1
"""
    result = solve_object_scene(DSL, seed=42, debug=False)
    contexts = export_all_contexts(result)

    assert len(contexts) == len(result.pieces)
    for pid, ctx in contexts.items():
        assert "self" in ctx
        assert isinstance(ctx["near_path"], bool)
        assert isinstance(ctx["on_cluster_edge"], bool)


def test_campfire_is_interior_in_shrine():
    from dropgrid.api import solve_object_scene

    DSL = """
anchor campfire altar
ma hard radius 4

object road label path count 10 from altar heading south steps 10 wobble 0.1
object tree label forest count 10 shape circle radius 7 clusters 5 spread 1
"""
    result = solve_object_scene(DSL, seed=42, debug=False)
    contexts = export_all_contexts(result)

    campfires = [p for p in result.pieces if p.type == "campfire"]
    assert campfires
    assert contexts[campfires[0].id]["interior"] is True


def test_lanterns_near_path_in_shrine():
    from dropgrid.api import solve_object_scene

    DSL = """
anchor campfire altar
ma hard radius 4

object road label path count 10 from altar heading south steps 10 wobble 0.1
object lantern label lanterns count 4 target road side any distance 1 spacing 2
"""
    result = solve_object_scene(DSL, seed=42, debug=False)
    contexts = export_all_contexts(result)

    lanterns = [p for p in result.pieces if p.type == "lantern"]
    assert lanterns
    near_path_count = sum(1 for p in lanterns if contexts[p.id]["near_path"])
    assert near_path_count > 0


def test_trees_mostly_on_cluster_edge_in_shrine():
    from dropgrid.api import solve_object_scene

    DSL = """
anchor campfire altar
ma hard radius 4

object road label path count 8 from altar heading south steps 8 wobble 0.1
object tree label forest count 12 shape circle radius 7 clusters 6 spread 1
"""
    result = solve_object_scene(DSL, seed=42, debug=False)
    contexts = export_all_contexts(result)

    trees = [p for p in result.pieces if p.type == "tree"]
    assert trees
    edge_count = sum(1 for p in trees if contexts[p.id]["on_cluster_edge"])
    assert edge_count > len(trees) // 2
