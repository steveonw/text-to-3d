from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.dropgrid.topology_candidate.layout_compiler import compile_layout_dsl_to_legacy_spec
from scripts.dropgrid.topology_candidate.layout_runtime import solve_layout_dsl


SMOKE_SCENE = """
object fence
  label yard_edge
  roles barrier boundary
  mode rect_perimeter
  importance primary

object gate
  label front_gate
  roles gate_opening gate_frame
  target yard_edge
  socket opening
  facing south
  importance primary

object fountain
  label shrine_center
  inside yard_edge
  importance primary

object torch
  label gate_torches
  count 2
  roles marker
  target yard_edge
  socket face
  near front_gate
"""

INTERIOR_FACE_SCENE = """
object fence
  label yard_edge
  roles barrier boundary
  mode rect_perimeter

object fountain
  label shrine_center
  inside yard_edge
  importance primary

object torch
  label inner_torch
  target yard_edge
  socket face
  near shrine_center
"""

CENTER_SCENE = """
object fence
  label yard_edge
  roles barrier boundary
  mode rect_perimeter

object fountain
  label shrine_center
  inside yard_edge
  importance primary

object table
  label center_table
  inside yard_edge
  importance secondary
"""

SCARCITY_SCENE = """
object fence
  label yard_edge
  roles barrier boundary
  mode rect_perimeter

object gate
  label front_gate
  roles gate_opening gate_frame
  target yard_edge
  socket opening
  facing south

object fountain
  label shrine_center
  inside yard_edge
  importance primary

object torch
  label many_torches
  count 30
  target yard_edge
  socket face
  near front_gate
"""


def test_compile_layout_dsl_to_legacy_spec_smoke():
    spec = compile_layout_dsl_to_legacy_spec(SMOKE_SCENE)
    assert spec["anchor"]["type"] == "fountain"
    labels = {o["label"] for o in spec["objects"]}
    assert "yard_edge" not in labels  # topology-managed host
    assert "gate_torches" in labels
    assert "yard_edge" in spec["layout_hosts_to_emit"]
    assert spec["layout_special_ops"][0]["type"] == "gate_opening"


def test_solve_layout_dsl_smoke():
    result = solve_layout_dsl(SMOKE_SCENE, seed=42)
    types = [p.type for p in result.pieces]
    assert "fountain" in types
    assert "gate" in types
    assert types.count("torch") == 2
    assert "yard_edge" in result.meta.get("topology_hosts", [])
    gate = [p for p in result.pieces if p.type == "gate" and p.label == "front_gate"][0]
    assert gate.meta.get("special_op") == "gate_opening_topology"
    torches = [p for p in result.pieces if p.type == "torch"]
    assert all("picked_from_slot_id" in p.meta for p in torches)
    assert all(":face:south:" in p.meta["picked_from_slot_id"] for p in torches)
    ascii_map = result.to_ascii(include_legend=False, show_axes=False, include_warnings=False)
    assert "G" in ascii_map
    assert "T" in ascii_map
    assert "F" in ascii_map


def test_attach_scarcity_hard_fail():
    result = solve_layout_dsl(SCARCITY_SCENE, seed=42)
    assert not [p for p in result.pieces if p.group == "many_torches"]
    errs = result.meta.get("errors", [])
    assert any(e.get("error") == "attach_scarcity" for e in errs)


def test_face_side_interior_context():
    result = solve_layout_dsl(INTERIOR_FACE_SCENE, seed=42)
    torch = [p for p in result.pieces if p.type == "torch"][0]
    assert torch.meta.get("face_side") == "interior"


def test_true_center_nudge_places_secondary_center():
    spec = compile_layout_dsl_to_legacy_spec(CENTER_SCENE)
    assert any(c["label"] == "center_table" for c in spec["layout_fixed_centers"])
    result = solve_layout_dsl(CENTER_SCENE, seed=42)
    table = [p for p in result.pieces if p.label == "center_table"][0]
    fountain = [p for p in result.pieces if p.label == "shrine_center"][0]
    assert (table.gx, table.gz) != (fountain.gx, fountain.gz)
    assert abs(table.gx - fountain.gx) <= 3
    assert abs(table.gz - fountain.gz) <= 3


ROAD_SCENE = """
object fence
  label yard_edge
  roles barrier boundary
  mode rect_perimeter

object gate
  label front_gate
  roles gate_opening gate_frame
  target yard_edge
  socket opening
  facing south

object fountain
  label shrine_center
  inside yard_edge
  importance primary

object road
  label approach
  mode line
  target front_gate
"""

CLUTTER_SCENE = """
object fence
  label yard_edge
  roles barrier boundary
  mode rect_perimeter

object gate
  label front_gate
  roles gate_opening gate_frame
  target yard_edge
  socket opening
  facing south

object fountain
  label shrine_center
  inside yard_edge
  importance primary

object rubble
  label clutter
  count 3
  mode scatter
  inside yard_edge
"""

def test_cross_layer_target_uses_topology_export():
    result = solve_layout_dsl(ROAD_SCENE, seed=42)
    gate_ref = result.meta.get("topology_exports", {}).get("front_gate")
    assert gate_ref is not None
    road = [p for p in result.pieces if p.type == "road"]
    assert road
    end = road[-1]
    assert abs(end.gx - round(gate_ref[0])) <= 1
    assert abs(end.gz - round(gate_ref[1])) <= 1

def test_topology_blocks_solver_overlap():
    result = solve_layout_dsl(CLUTTER_SCENE, seed=42)
    topo = {(p.gx, p.gz) for p in result.pieces if p.meta.get("topology_emitted")}
    clutter = [(p.gx, p.gz) for p in result.pieces if p.group == "clutter"]
    assert all(c not in topo for c in clutter)


# ── Box-drawing borders and height view ───────────────────────────────────────

def test_ascii_borders_uses_box_drawing():
    """MA zone cells should use ┌─┐│└─┘ chars when show_borders=True."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
ma hard radius 4
object tree label ring count 6 shape circle radius 6
"""
    result = solve_object_scene(DSL, seed=1, debug=False)
    ascii_out = result.to_ascii(show_borders=True, include_warnings=False)
    box_chars = set('┌─┐│└─┘┬┴├┤┼')
    assert any(ch in ascii_out for ch in box_chars), "Expected box-drawing chars in MA zone border"


def test_ascii_no_borders_uses_shade():
    """show_borders=False should use only ░ for MA cells."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
ma hard radius 3
"""
    result = solve_object_scene(DSL, seed=1, debug=False)
    ascii_out = result.to_ascii(show_borders=False, include_warnings=False)
    assert '┌' not in ascii_out
    assert '│' not in ascii_out
    # MA cells rendered as shade
    assert '░' in ascii_out


def test_ascii_height_view_appended():
    """show_heights=True should append a height grid with block chars."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
object tree label ring count 3 shape circle radius 4
"""
    result = solve_object_scene(DSL, seed=1, debug=False)
    ascii_out = result.to_ascii(show_heights=True, include_warnings=False)
    assert 'Height:' in ascii_out
    assert '█' in ascii_out  # trees are tall tier


def test_ascii_height_campfire_is_short():
    """Campfire should render as ▒ (short tier) in the height view."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
"""
    result = solve_object_scene(DSL, seed=1, debug=False)
    ascii_out = result.to_ascii(show_heights=True, include_warnings=False)
    assert '▒' in ascii_out


def test_ascii_border_legend_note():
    """Legend with show_borders=True should include box-drawing note."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
ma hard radius 3
"""
    result = solve_object_scene(DSL, seed=1, debug=False)
    ascii_out = result.to_ascii(include_legend=True, show_borders=True, include_warnings=False)
    assert '┌─┐' in ascii_out  # border note in legend


# ── E11: Path terminus pinning ────────────────────────────────────────────────

def test_path_to_stops_adjacent_to_target():
    """Path with `to` should stop when it reaches adjacency to the target piece."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
object market label shop count 1 shape circle radius 8
object road label path steps 20 from campfire heading east wobble 0.1 to shop_0
"""
    result = solve_object_scene(DSL, seed=42, debug=False)
    roads = [p for p in result.pieces if p.type == 'road']
    market = next((p for p in result.pieces if p.type == 'market'), None)
    assert market is not None, "Market piece not placed"
    assert len(roads) > 0, "No road pieces placed"
    last = roads[-1]
    dist = abs(last.gx - market.gx) + abs(last.gz - market.gz)
    assert dist <= 2, f"Path ended {dist} cells from target, expected <=2"


def test_path_steps_alias_for_count():
    """`steps N` should produce N road cells (alias for count)."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
object road label path steps 6 from campfire heading south wobble 0.0
"""
    result = solve_object_scene(DSL, seed=42, debug=False)
    roads = [p for p in result.pieces if p.type == 'road']
    assert len(roads) == 6, f"Expected 6 road cells from steps 6, got {len(roads)}"


def test_path_to_unknown_target_still_places():
    """Path with a `to` that doesn't exist should walk the full count."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
object road label path steps 5 from campfire heading east to nonexistent
"""
    result = solve_object_scene(DSL, seed=42, debug=False)
    roads = [p for p in result.pieces if p.type == 'road']
    assert len(roads) == 5


# ── E12: Anchored cluster scatter ────────────────────────────────────────────

def test_scatter_near_places_within_radius():
    """Pieces scattered `near X radius R` should all be within R cells of X."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
object barrel label fuel count 4 near campfire radius 3
"""
    result = solve_object_scene(DSL, seed=42, debug=False)
    anchor = next(p for p in result.pieces if p.type == 'campfire')
    barrels = [p for p in result.pieces if p.type == 'barrel']
    assert len(barrels) > 0
    for b in barrels:
        d = abs(b.gx - anchor.gx) + abs(b.gz - anchor.gz)
        assert d <= 3, f"Barrel at ({b.gx},{b.gz}) is {d} from anchor, exceeds radius 3"


def test_scatter_radius_places_within_distance():
    """Pieces with `radius R` scatter within R of scene center."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
object rubble label clutter count 4 radius 5
"""
    result = solve_object_scene(DSL, seed=42, debug=False)
    anchor = next(p for p in result.pieces if p.type == 'campfire')
    rubble = [p for p in result.pieces if p.type == 'rubble']
    assert len(rubble) > 0
    for r in rubble:
        d = abs(r.gx - anchor.gx) + abs(r.gz - anchor.gz)
        assert d <= 5, f"Rubble at ({r.gx},{r.gz}) is {d} from center, exceeds radius 5"


def test_scatter_near_invalid_target_falls_back_to_center():
    """near with unknown type should still place pieces (falls back to scene center)."""
    from dropgrid.api import solve_object_scene
    DSL = """
anchor campfire center
object rubble label debris count 3 near nonexistent radius 4
"""
    result = solve_object_scene(DSL, seed=42, debug=False)
    rubble = [p for p in result.pieces if p.type == 'rubble']
    assert len(rubble) > 0
