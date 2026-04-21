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
